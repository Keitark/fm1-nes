"""Build the optional original NROM cartridge. No downloads or device I/O.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 Keitark.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def validate_rom(data):
    # Match the FM-1 embedder, then require this game's exact NROM shape/vectors.
    sys.path.insert(0, str(ROOT.parents[1] / 'firmware/nes'))
    from embed_rom50 import validate
    validate(data)
    if data[4:8] != bytes((2, 1, 1, 0)):
        raise ValueError('Expected mapper 0, 32 KiB PRG, 8 KiB CHR, vertical mirroring')
    vectors = struct.unpack('<HHH', data[16 + 32768 - 6:16 + 32768])
    if not all(0x8000 <= address <= 0xfff9 for address in vectors):
        raise ValueError('NROM interrupt/reset vector outside executable PRG')
    return hashlib.sha256(data).hexdigest()


def tool(directory, name):
    directory = directory.resolve()
    candidates = [directory / (name + '.exe'), directory / name]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError('Supply an existing cc65 bin directory containing ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc65-bin', required=True, type=Path,
                        help='Existing external ca65/ld65 directory; never installed here')
    parser.add_argument('--out', type=Path, default=ROOT / 'build/game_nrom.nes',
                        help='Fresh output ROM (default ignored example build directory)')
    args = parser.parse_args()
    try:
        assembler, linker = tool(args.cc65_bin, 'ca65'), tool(args.cc65_bin, 'ld65')
        output = args.out.resolve()
        if output.exists():
            raise ValueError('ROM output exists; choose a fresh --out path')
        # Validate tools/output before running generators or creating directories.
        output.parent.mkdir(parents=True, exist_ok=True)
        assets = ROOT / 'build'
        def run(argv):
            subprocess.run(list(map(str, argv)), cwd=ROOT, check=True)
        run([sys.executable, ROOT / 'gfx/gen_nrom.py'])
        run([sys.executable, ROOT / 'gfx/gen_all.py'])
        obj = output.with_suffix('.o')
        run([assembler, ROOT / 'src/main_nrom.s', '-g', '-I', assets,
             '--bin-include-dir', assets, '-o', obj])
        run([linker, '-C', ROOT / 'nes_nrom.cfg', obj, '-o', output,
             '-m', output.with_suffix('.map'), '--dbgfile', output.with_suffix('.dbg')])
        digest = validate_rom(output.read_bytes())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')
    print('NROM mapper 0, PRG 32 KiB, CHR 8 KiB:', output)
    print('SHA256 ' + digest)


if __name__ == '__main__':
    main()
