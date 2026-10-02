"""Synthetic fixtures only: no stock bytes, device access or real encoding keys."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import app_package as package
import jl_formats as fmt
import jltool_update as update

FAKE_CODE = bytes([0x69])*14368  # Generated test data, not executable firmware.


def record(offset, size, flags, name, dcrc=0, index=0, reserved=255):
    value = bytearray(struct.pack('<HHIIBBH16s', 0, dcrc, offset, size, flags,
                                  reserved, index, name.encode()))
    struct.pack_into('<H', value, 0, fmt.crc(value[2:]))
    return value


def fixture(capacity=584956):
    raw = bytearray([0x5a])*fmt.SIZE
    header = bytearray(32)
    struct.pack_into('<I', header, 8, fmt.SIZE)
    struct.pack_into('<H', header, 0, fmt.crc(header[2:]))
    fmt.enc(header, 0, 32)
    raw[:32] = header
    for i, value in enumerate((record(0xa0, 14384, 0, 'uboot.boot'),
            record(0x38d0, 699, 2, 'isd_config.ini', reserved=128),
            record(fmt.AREA, 0xffffffff, 0x81, 'app_dir_head'),
            record(0xff000, 4096, 0x12, 'key_mac', index=65535, reserved=1))):
        fmt.enc(value, 0, 32)
        raw[32+i*32:64+i*32] = value
    bank = bytearray(struct.pack('<HHIIHH', 1, len(FAKE_CODE), 0x01c02000, 16,
                                  fmt.crc(FAKE_CODE), 0) + FAKE_CODE)
    struct.pack_into('<H', bank, 14, fmt.crc(bank[:14]))
    fmt.enc(bank, 0, 16)
    fmt.enc(bank, 16, len(FAKE_CODE))
    raw[0xa0:0xa0+len(bank)] = bank
    # Synthetic metadata encoding zero; never copied from a real unit.
    metadata = bytes(16) + bytes([255])*16
    raw[0x38d0:0x38d0+34] = metadata + fmt.crc(metadata).to_bytes(2, 'little')
    old_app = bytes([0xa5])*capacity
    config = bytes([0x37])*383
    cfg_offset = 0x120+capacity
    area_size = cfg_offset+len(config)
    data = bytearray([0x44])*area_size
    rows = (record(0x120, capacity, 0x82, 'app.bin', fmt.crc(old_app)),
            record(cfg_offset, len(config), 0x82, 'cfg_tool.bin', fmt.crc(config)),
            record(0x94000, 348160, 0x12, 'VM', reserved=128),
            record(0, 606208, 0x92, 'PRCT', reserved=130),
            record(0xe9000, 4096, 0x92, 'BTIF', reserved=128),
            record(0xea000, 73728, 0x92, 'USR', index=1, reserved=129))
    for i, value in enumerate(rows):
        data[32+i*32:64+i*32] = value
    data[0x120:cfg_offset] = old_app
    data[cfg_offset:] = config
    data[:32] = record(package.ENTRY, area_size, 0x83, 'app_area_head', fmt.crc(data[32:]))
    fmt.sfc(data, 0, len(data), 0)
    raw[fmt.AREA:fmt.AREA+len(data)] = data
    return bytes(raw)


class FakeTool:
    def __init__(self, raw, corrupt_after_write=False):
        self.state = bytearray(raw)
        self.events = []
        self.corrupt_after_write = corrupt_after_write

    def call(self, commands, log, mode='io'):
        for command in commands:
            op, address, rest = command.split(maxsplit=2)
            address = int(address)
            self.events.append((op, address))
            if op == 'read':
                length, path = rest.split(maxsplit=1)
                Path(path).write_bytes(self.state[address:address+int(length)])
            elif op == 'write':
                blob = Path(rest).read_bytes()
                assert len(blob) == fmt.SECTOR and address >= fmt.AREA
                self.state[address:address+len(blob)] = blob
                if self.corrupt_after_write:
                    self.state[address] ^= 1
            else:
                raise AssertionError('Forbidden command')


class PackageTests(unittest.TestCase):
    def inputs(self, folder):
        app = folder/'input.bin'
        app.write_bytes(b'PROJECT-ONLY'*37)
        audit = folder/'audit.json'
        info = package.manifest(app.read_bytes())
        info['entry'] = hex(package.ENTRY)
        audit.write_bytes(package.json_bytes(info))
        return app, audit

    def test_package_only_app_and_sanitized_manifest_and_reproducible(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            app, audit = self.inputs(root)
            extra = json.loads(audit.read_text())
            extra['private_path'] = 'MUST-NOT-LEAK'
            audit.write_text(json.dumps(extra))
            for name in ('a.fm1app', 'b.fm1app'):
                package.create(app, audit, root/name)
            self.assertEqual((root/'a.fm1app').read_bytes(), (root/'b.fm1app').read_bytes())
            with zipfile.ZipFile(root/'a.fm1app') as archive:
                self.assertEqual(set(archive.namelist()), {'app.bin', 'manifest.json'})
                self.assertNotIn(b'MUST-NOT-LEAK', archive.read('manifest.json'))
            self.assertEqual(package.load(root/'a.fm1app')[0], app.read_bytes())
            with self.assertRaises(FileExistsError):
                package.create(app, audit, root/'a.fm1app')

    def test_reject_failed_or_unbound_audit(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            app, audit = self.inputs(root)
            for field, value in (('static_audit', 'failed'), ('application_sha256', '0'*64),
                                 ('application_bytes', 1), ('entry', '0x0')):
                info = package.manifest(app.read_bytes())
                info['entry'] = hex(package.ENTRY)
                info[field] = value
                audit.write_text(json.dumps(info))
                with self.assertRaises(ValueError):
                    package.create(app, audit, root/'out.fm1app')
                self.assertFalse((root/'out.fm1app').exists())

    def test_archive_rejects_extra_duplicate_corrupt_and_wrong_manifest(self):
        app = b'original'
        for kind in ('extra', 'duplicate', 'hash', 'entry', 'size', 'type', 'format', 'json-duplicate'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                path = Path(name)/'bad.fm1app'
                info = package.manifest(app)
                if kind in ('entry', 'size', 'type', 'format'):
                    key = {'entry': 'entry', 'size': 'application_bytes', 'type': 'hardware_qualified',
                           'format': 'format'}[kind]
                    info[key] = 0 if kind != 'format' else 'other'
                manifest = package.json_bytes(info)
                if kind == 'json-duplicate':
                    manifest = b'{"format":"x","format":"y"}'
                with zipfile.ZipFile(path, 'w') as archive:
                    archive.writestr('app.bin', b'changed!' if kind == 'hash' else app)
                    archive.writestr('manifest.json', manifest)
                    if kind == 'extra':
                        archive.writestr('../stock.bin', b'NOT-A-ROM')
                    if kind == 'duplicate':
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', UserWarning)
                            archive.writestr('app.bin', app)
                with self.assertRaises(ValueError):
                    package.load(path)

    def test_empty_oversize_and_duplicate_json(self):
        for data in (b'', bytes(package.MAX_APP+1)):
            with self.assertRaises(ValueError):
                package.manifest(data)
        with self.assertRaises(ValueError):
            package.strict_json(b'{"a":1,"a":2}')


class SparseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = fixture()
        cls.raw010 = fixture(583228)

    def setUp(self):
        self.boot_pin = patch.object(fmt, 'BOOT_SHA', package.sha(FAKE_CODE))
        self.boot_pin.start()
        self.addCleanup(self.boot_pin.stop)

    def prepare(self, raw=None, size=4097):
        app = bytes((i*7+3) % 256 for i in range(size))
        sectors, plan = fmt.prepare(raw or self.raw, app, package.manifest(app))
        return app, sectors, plan

    def patched(self, raw, sectors):
        model = bytearray(raw)
        for i, data in sectors.items():
            model[i:i+fmt.SECTOR] = data
        return bytes(model)

    def test_both_layouts_crc_and_all_preservation_boundaries(self):
        for raw in (self.raw, self.raw010):
            with self.subTest(layout=package.sha(raw)):
                app, sectors, plan = self.prepare(raw)
                target = self.patched(raw, sectors)  # Test NOR model, not production packager.
                decoded, _, capacity = fmt.layout(target)
                self.assertEqual(decoded[0x120:0x120+len(app)], app)
                self.assertEqual(target[:fmt.AREA], raw[:fmt.AREA])
                self.assertEqual(target[fmt.AREA+64:fmt.APP], raw[fmt.AREA+64:fmt.APP])
                self.assertEqual(target[fmt.APP+len(app):], raw[fmt.APP+len(app):])
                self.assertEqual(plan['sectors'][-1]['offset'], fmt.AREA)
                self.assertEqual({r['offset'] for r in plan['sectors']}, set(sectors))
                self.assertTrue(all(len(b) == fmt.SECTOR for b in sectors.values()))
                self.assertNotIn('key', json.dumps(plan).lower())

    def test_allocation_survives_smaller_application_then_grows(self):
        _, sectors, _ = self.prepare(size=33)
        small = self.patched(self.raw, sectors)
        app, second, _ = self.prepare(small, size=8193)
        self.assertEqual(fmt.layout(self.patched(small, second))[0][0x120:0x120+len(app)], app)

    def test_cipher_and_sector_boundaries_and_full_slot(self):
        for size in (1, 31, 32, 33, fmt.SECTOR-0x120, fmt.SECTOR-0x120+1, 584956):
            with self.subTest(size=size):
                app, sectors, _ = self.prepare(size=size)
                target = self.patched(self.raw, sectors)
                self.assertEqual(target[fmt.APP+size:], self.raw[fmt.APP+size:])
                self.assertEqual(fmt.layout(target)[0][0x120:0x120+size], app)

    def test_corrupt_header_boot_metadata_area_app_config_rejected(self):
        for position in (0, 32, 0xa0+16, 0x38d0, fmt.AREA, fmt.APP, fmt.APP+584956):
            raw = bytearray(self.raw)
            raw[position] ^= 1
            with self.subTest(position=position), self.assertRaises(ValueError):
                self.prepare(bytes(raw))

    def test_unreviewed_boot_rejected(self):
        with patch.object(fmt, 'BOOT_SHA', '0'*64), self.assertRaisesRegex(ValueError, 'Unreviewed bootloader'):
            self.prepare()

    def test_010_size_limit_and_wrong_length_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            self.prepare(self.raw010, size=583229)
        with self.assertRaises(ValueError):
            self.prepare(self.raw[:-1])

    def test_unsupported_geometry_with_valid_crcs_rejected(self):
        decoded, _, _ = fmt.layout(self.raw)
        for position, value in ((36, 0x140), (68, 0x120+584955), (104, 348159)):
            altered = bytearray(decoded)
            struct.pack_into('<I', altered, position, value)
            header = position // 32 * 32
            struct.pack_into('<H', altered, header, fmt.crc(altered[header+2:header+32]))
            struct.pack_into('<H', altered, 2, fmt.crc(altered[32:]))
            struct.pack_into('<H', altered, 0, fmt.crc(altered[2:32]))
            fmt.sfc(altered, 0, len(altered), 0)
            raw = bytearray(self.raw)
            raw[fmt.AREA:fmt.AREA+len(altered)] = altered
            with self.subTest(position=position), self.assertRaises(ValueError):
                self.prepare(bytes(raw))

    def test_identical_app_is_a_noop(self):
        decoded, _, capacity = fmt.layout(self.raw)
        app = bytes(decoded[0x120:0x120+capacity])
        sectors, plan = fmt.prepare(self.raw, app, package.manifest(app))
        self.assertEqual(sectors, {})
        self.assertEqual(plan['sectors'], [])

    def test_successful_existing_cli_sequence_and_one_final_read(self):
        _, sectors, plan = self.prepare()
        tool = FakeTool(self.raw)
        with tempfile.TemporaryDirectory() as name:
            receipt = update.deploy(tool, Path(name), self.raw, sectors, plan, fmt.plan_digest(plan))
            self.assertEqual(receipt['status'], 'written_and_readback_verified')
            self.assertEqual(receipt['full_readback_count'], 1)
            writes = [address for op, address in tool.events if op == 'write']
            self.assertEqual(writes, [row['offset'] for row in plan['sectors']])
            self.assertEqual(writes[-1], fmt.AREA)
            self.assertEqual(bytes(tool.state), self.patched(self.raw, sectors))

    def test_wrong_approval_and_plan_tampering_do_no_io(self):
        _, sectors, plan = self.prepare()
        for kind in ('approval', 'hash', 'outside', 'protected'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as name:
                bad = copy.deepcopy(plan)
                data = dict(sectors)
                approval = fmt.plan_digest(bad)
                if kind == 'approval':
                    approval = '0'*64
                elif kind == 'hash':
                    data[fmt.AREA] = bytes(fmt.SECTOR)
                elif kind == 'outside':
                    bad['sectors'][0]['offset'] = 0
                else:
                    value = bytearray(data[fmt.AREA]); value[64] ^= 1
                    data[fmt.AREA] = bytes(value)
                    bad['sectors'][-1]['after_sha256'] = package.sha(value)
                if kind != 'approval':
                    approval = fmt.plan_digest(bad)
                tool = FakeTool(self.raw)
                with self.assertRaises(ValueError):
                    update.deploy(tool, Path(name), self.raw, data, bad, approval)
                self.assertEqual(tool.events, [])

    def test_stale_device_and_readback_fail_without_retry_or_reset(self):
        _, sectors, plan = self.prepare()
        for stale in (True, False):
            with tempfile.TemporaryDirectory() as name:
                state = bytearray(self.raw)
                if stale:
                    state[-1] ^= 1
                tool = FakeTool(state, corrupt_after_write=not stale)
                with self.assertRaises(ValueError):
                    update.deploy(tool, Path(name), self.raw, sectors, plan, fmt.plan_digest(plan))
                receipt = json.loads((Path(name)/'receipt.json').read_text())
                self.assertIn('failed', receipt['status'])
                self.assertEqual(len([x for x in tool.events if x[0] == 'write']), 0 if stale else 1)
                self.assertFalse(receipt['automatic_reset'])

    def test_cli_wrapper_commands_do_not_create_new_transport_or_environment(self):
        tool = object.__new__(update.JLTool)
        tool.root = ROOT
        tool.device = r'\\.\PHYSICALDRIVE3'
        with tempfile.TemporaryDirectory() as name:
            def run(argv, **kwargs):
                kwargs['stdout'].write('Target confirmed: WL82 UBOOT1.00 1.00\n')
                self.assertIn('--reuse-loader', argv)
                self.assertIn('--fm1-bench', argv)
                self.assertEqual(argv[0], sys.executable)
                self.assertNotIn('erasechip', ' '.join(argv))
            with patch.object(update.subprocess, 'run', side_effect=run) as call:
                tool.call(['read 0 256 output.bin'], Path(name)/'log.txt')
                self.assertEqual(call.call_count, 1)
            with self.assertRaises(ValueError):
                tool.call(['erasechip'], Path(name)/'bad.log')

    def test_bad_device_path_refused_before_tool_or_io(self):
        for device in ('3', 'C:', r'\\.\PHYSICALDRIVE3 extra', '/dev/sda'):
            with patch.object(update, 'check_tool') as check, self.assertRaises(ValueError):
                update.JLTool(ROOT, device)
            check.assert_not_called()

    def test_incomplete_read_refused(self):
        class ShortRead:
            def call(self, commands, log):
                Path(commands[0].split(maxsplit=3)[3]).write_bytes(b'short')
        with tempfile.TemporaryDirectory() as name, self.assertRaises(ValueError):
            update.read(ShortRead(), Path(name), 0, 256, 'short')


if __name__ == '__main__':
    unittest.main()
