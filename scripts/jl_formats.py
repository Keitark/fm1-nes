"""Bounded JLFS metadata and sparse application-sector preparation.

ENC/SFC and stored encoding-metadata decoding adapted from kagaimiq/jl-misctools
0a5b12db0ef38f3042acffbe2452730a37fd2405 (Copyright 2023 Andrey Grigoryev).
Those routines are MIT licensed; see licenses/kagaimiq-MIT.txt. Modification:
bounded FM-1 parsing and sparse planning; no CLI extraction, key query or logging.
Remaining project-authored code follows the repository license.
"""
import binascii
import struct

from app_package import ENTRY, LAYOUT, json_bytes, require, sha

SIZE = 1048576
AREA = 0x4000
APP = 0x4120
SECTOR = 4096
BOOT_SHA = 'fcaf033c5e10526353ecb11279a7556ac8645026d370c0267912cb4bfa7c7e4d'


def crc(data):
    return binascii.crc_hqx(data, 0)


def enc(data, offset, length, key=0xffff):
    for i in range(offset, offset + length):
        data[i] ^= key & 255
        key = ((key << 1) ^ (0x1021 if key & 0x8000 else 0)) & 0xffff


def sfc(data, offset, length, key):
    for i in range(offset, offset + length, 32):
        enc(data, i, min(32, offset + length - i), key ^ (i >> 2))


def metadata_value(data):
    require(len(data) == 32, 'Invalid encoding metadata')
    limit = sum(data[:16]) & 255
    limit = 0xaa if limit >= 0xe0 else 0x55 if limit <= 0x10 else limit
    return sum(1 << i for i in range(16) if data[16+i] ^ data[15-i] < limit)


def entry(data, offset):
    require(0 <= offset <= len(data)-32, 'Directory record outside input')
    fields = struct.unpack_from('<HHIIBBH16s', data, offset)
    require(crc(data[offset+2:offset+32]) == fields[0], 'Directory header CRC mismatch')
    return fields


def layout(raw):
    require(len(raw) == SIZE, 'Expected owner-provided 1 MiB backup')
    top = bytearray(raw[:0xa0])
    enc(top, 0, 32)
    require(crc(top[2:32]) == int.from_bytes(top[:2], 'little'), 'Flash header CRC mismatch')
    records = []
    for offset in range(32, 0xa0, 32):
        enc(top, offset, 32)
        item = entry(top, offset)
        records.append(item)
        if item[6]:
            break
    require(len(records) == 4 and records[-1][6] != 0
            and [r[7].split(b'\0')[0] for r in records] ==
            [b'uboot.boot', b'isd_config.ini', b'app_dir_head', b'key_mac'], 'Unsupported top directory')
    boot, config, directory, reserved = records
    require(boot[2:5] == (0xa0, 14384, 0)
            and directory[2] == AREA and directory[4] == 0x81,
            'Unsupported boot/application layout')
    require(config[4] == 2 and config[3] >= 34
            and boot[2]+boot[3] <= config[2] and config[2]+config[3] <= AREA,
            'Unsupported encoding metadata location')
    require(reserved[2:5] == (0xff000, 4096, 0x12), 'Unsupported top reserved record')
    bank = bytearray(raw[0xa0:0xa0+14384])
    enc(bank, 0, 16)
    count, length, load, start, dcrc, hcrc = struct.unpack_from('<HHIIHH', bank)
    require((count, length, load, start) == (1, 14368, 0x01c02000, 16)
            and crc(bank[:14]) == hcrc, 'Unsupported boot bank')
    enc(bank, start, length)
    require(crc(bank[start:]) == dcrc and sha(bank[start:]) == BOOT_SHA,
            'Unreviewed bootloader; no write plan')
    value = raw[config[2]:config[2]+34]
    require(crc(value[:32]) == int.from_bytes(value[32:], 'little'), 'Encoding metadata CRC mismatch')
    key = metadata_value(value[:32])  # Memory only; never return/serialize it.
    header = bytearray(raw[AREA:AREA+32])
    sfc(header, 0, 32, key)
    area = entry(header, 0)
    require(area[2] == ENTRY and area[4:7] == (0x83, 255, 0)
            and area[7].split(b'\0')[0] == b'app_area_head'
            and 0x120 < area[3] <= SIZE-AREA, 'Unsupported application area')
    # A single application area only; never decode VM or other reserved payloads.
    data = bytearray(raw[AREA:AREA+area[3]])
    sfc(data, 0, len(data), key)
    require(crc(data[32:]) == area[1], 'Application area CRC mismatch')
    entries = [entry(data, i) for i in range(32, 0xe0, 32)]
    require([e[7].split(b'\0')[0] for e in entries] ==
            [b'app.bin', b'cfg_tool.bin', b'VM', b'PRCT', b'BTIF', b'USR'],
            'Unsupported application directory')
    app, cfg, vm, prct, btif, usr = entries
    capacity = cfg[2] - 0x120
    require(capacity in (583228, 584956) and app[2] == 0x120
            and 0 < app[3] <= capacity and app[4] == 0x82 and app[6] == 0
            and cfg[3:5] == (383, 0x82) and cfg[6] == 0
            and area[3] == cfg[2]+cfg[3]
            and vm[2:5] == (0x94000, 348160, 0x12)
            and prct[2:5] == (0, 606208, 0x92)
            and btif[2:5] == (0xe9000, 4096, 0x92)
            and usr[2:5] == (0xea000, 73728, 0x92)
            and all(e[6] == 0 for e in entries[:-1]) and usr[6] != 0,
            'Unsupported file allocation or reserved records')
    require(crc(data[app[2]:app[2]+app[3]]) == app[1]
            and crc(data[cfg[2]:cfg[2]+cfg[3]]) == cfg[1], 'Application/configuration CRC mismatch')
    return data, key, capacity


def prepare(raw, app, package_info):
    """Return changed sector bytes and a sanitized plan, never a full candidate."""
    data, key, capacity = layout(raw)
    require(0 < len(app) <= capacity, 'Application exceeds this device allocation')
    require(package_info['layout'] == LAYOUT and package_info['application_sha256'] == sha(app),
            'Package identity mismatch')
    data[0x120:0x120+len(app)] = app
    struct.pack_into('<H', data, 34, crc(app))
    struct.pack_into('<I', data, 40, len(app))
    struct.pack_into('<H', data, 32, crc(data[34:64]))
    struct.pack_into('<H', data, 2, crc(data[32:]))
    struct.pack_into('<H', data, 0, crc(data[2:32]))
    end = (0x120+len(app)+31) & ~31
    # This stays before cfg_tool; use existing raw tail when crossing a cipher block.
    require(end <= len(data), 'Encoded application exceeds area')
    replacements = []
    for first, last in ((0, 64), (0x120, end)):
        plain = bytes(data[first:last])
        sfc(data, first, last-first, key)
        encoded = bytes(data[first:last])
        # Round trip independently before using any prepared sector bytes.
        sfc(data, first, last-first, key)
        require(bytes(data[first:last]) == plain, 'Encoding round-trip mismatch')
        replacements.append((AREA+first, encoded))
    addresses = sorted({address // SECTOR * SECTOR
                        for first, blob in replacements
                        for address in range(first, first+len(blob))})
    sectors = {}
    for address in addresses:
        original = raw[address:address+SECTOR]
        target = bytearray(original)
        for first, blob in replacements:
            left, right = max(first, address), min(first+len(blob), address+SECTOR)
            if left < right:
                target[left-address:right-address] = blob[left-first:right-first]
        target = bytes(target)
        # Even cipher-block and erase-sector boundary bytes must be unchanged.
        for i, (old, new) in enumerate(zip(original, target)):
            absolute = address+i
            require(old == new or AREA <= absolute < AREA+64
                    or APP <= absolute < APP+len(app), 'Change outside application/CRC records')
        if target != original:
            sectors[address] = target
    order = [i for i in sorted(sectors) if i != AREA] + ([AREA] if AREA in sectors else [])
    plan = {'format': 'fm1-private-sector-plan-v1', 'layout': LAYOUT,
            'baseline_sha256': sha(raw), 'application_sha256': sha(app),
            'application_bytes': len(app), 'allocation_bytes': capacity,
            'sector_bytes': SECTOR, 'directory_last': True,
            'hardware_qualified': False, 'private_unit_data': True,
            'sectors': [{'offset': i, 'before_sha256': sha(raw[i:i+SECTOR]),
                         'after_sha256': sha(sectors[i])} for i in order]}
    return sectors, plan


def plan_digest(plan):
    return sha(json_bytes(plan))
