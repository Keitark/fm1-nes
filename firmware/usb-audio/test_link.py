# SPDX-License-Identifier: GPL-3.0-only
# Adapted from fm1-mdx4141057; see licenses/fm1-mdx-GPL-3.0.txt.
"""Offline regression checks against the linked composite ELF; no device I/O."""
from pathlib import Path
import struct
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'firmware/nes'))
from audit_boot import audit, PARTS
from embed_rom50 import select_rom
import hashlib


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(os.environ.get('FM1_LINK_TEST_DIR', ROOT / 'build/firmware-audio'))
        rom=ROOT / "build/diagnostic.nes"
        select_rom(rom,hashlib.sha256(rom.read_bytes()).hexdigest())
        cls.elf = (cls.folder / 'fm1-usb-diag.elf').read_bytes()
        offset = struct.unpack_from('<I', cls.elf, 32)[0]
        count, strings = struct.unpack_from('<HH', cls.elf, 48)
        raw = [struct.unpack_from('<10I', cls.elf, offset + i * 40) for i in range(count)]
        s = raw[strings]
        names = cls.elf[s[4]:s[4] + s[5]]
        cls.sections = {names[s[0]:names.index(b'\0', s[0])].decode(): s for s in raw}
        cls.symbols = {}
        for line in (cls.folder / 'symbols.txt').read_text().splitlines():
            fields = line.split()
            if len(fields) == 4:
                cls.symbols[fields[3]] = int(fields[0], 16)

    def check_elf(self, elf):
        app = b''.join(elf[self.sections[n][4]:self.sections[n][4] + self.sections[n][5]] for n in PARTS)
        return audit(elf, app, usb_only=True, usb_peripheral_tests=True,
                     usb_nes=True, rom="smb1", usb_audio=True, require_boot_trace=True,
                     require_board_power=True)

    def corrupt(self, symbol, delta):
        address = self.symbols[symbol] + delta
        section = next(s for s in self.sections.values()
                       if s[1] != 8 and s[3] <= address < s[3] + s[5])
        elf = bytearray(self.elf)
        elf[section[4] + address - section[3]] ^= 4
        return elf

    def test_original_passes(self):
        self.assertEqual(self.check_elf(self.elf)['static_audit'], 'passed')

    def test_boot_trace_store_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Boot trace wrapper instructions changed'):
            self.check_elf(self.corrupt('__wrap_memory_init', 14))

    def test_usb_task_affinity_corruption_is_rejected(self):
        # A corrupted task-name pointer must not bypass the CPU0 requirement.
        with self.assertRaisesRegex(ValueError, 'task registration changed: #C0usb_diag'):
            self.check_elf(self.corrupt('task_info_table', 4 * 20))

    def test_peripheral_task_affinity_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'task registration changed: #C0peripheral'):
            self.check_elf(self.corrupt('task_info_table', 5 * 20))

    def test_descriptor_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UAC1 interface/terminal'):
            self.check_elf(self.corrupt('fm1_uac_descriptor', 90))
    def test_sample_scale_corruption_is_rejected(self):
        # ROM-backed symbol size and call-order checks are separate from host
        # PCM tests; changing this call must not remove the raw capture tap.
        start=self.symbols['audio_output'];body=self.elf
        section=next(s for s in self.sections.values() if s[1]!=8 and s[3]<=start<s[3]+s[5])
        from audit_power import call_target
        raw=body[section[4]+start-section[3]:section[4]+start-section[3]+512]
        for off in range(0,len(raw)-5,2):
            n=6 if raw[off:off+2]==b'\x80\xff' else 4 if raw[off]&0xc0==0x80 and raw[off+1]==0xea else 0
            if n and call_target(raw[off:off+n],start+off)==self.symbols['fm1_audio_queue_raw24']:
                with self.assertRaisesRegex(ValueError,'NES USB pre-volume'):
                    self.check_elf(self.corrupt('audio_output',off+2))
                return
        self.fail('raw capture call not found')

    def test_packet_dma_count_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'USB packet commit instructions changed'):
            self.check_elf(self.corrupt('fm1_usb_packet_write', 0x76))

    def test_packet_doorbell_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'USB packet short call changed'):
            self.check_elf(self.corrupt('fm1_usb_packet_write', 0x8c))

    def test_packet_irq_restore_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'USB packet commit instructions changed'):
            self.check_elf(self.corrupt('fm1_usb_packet_write', 0x96))

    def test_power_destination_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Power merged-global target changed: sys_low_power'):
            self.check_elf(self.corrupt('power_init', 0x3c2))

    def test_lrc_destination_corruption_is_rejected(self):
        # LTO uses a small preincrement store below256, otherwise a six-byte
        # add-immediate/store. Corrupt the destination operand in either form.
        delta = self.symbols['lrc.0'] - self.symbols['ota_status']
        operand = 0x0d8 if delta < 256 else 0x0d6
        with self.assertRaisesRegex(ValueError, 'Power merged-global target changed: lrc.0'):
            self.check_elf(self.corrupt('power_init', operand))

    def test_power_gateway_corruption_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Board power gateway instructions changed'):
            self.check_elf(self.corrupt('fm1_board_power_init', 24))


if __name__ == '__main__':
    unittest.main()
