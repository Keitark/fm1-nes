import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/fablenes'
spec = importlib.util.spec_from_file_location('homebrew_build', EXAMPLE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class HomebrewTests(unittest.TestCase):
    def cartridge(self):
        data = bytearray(b'NES\x1a' + bytes((2, 1, 1, 0)) + bytes(8) + bytes(40960))
        struct.pack_into('<HHH', data, 16 + 32768 - 6, 0x8000, 0x8001, 0xfff9)
        return data

    def test_nrom_shape_vectors_and_hash(self):
        self.assertEqual(len(build.validate_rom(self.cartridge())), 64)
        for offset, value in ((4, 1), (5, 0), (6, 0x41), (16 + 32768 - 6, 0)):
            data = self.cartridge()
            if offset == 16 + 32768 - 6:
                struct.pack_into('<H', data, offset, 0x7000)
            else:
                data[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                build.validate_rom(data)

    def test_missing_external_compiler_fails_before_generators(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                build.tool(Path(folder), 'ca65')

    def test_generators_need_no_downloaded_or_binary_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(EXAMPLE / 'gfx', root / 'gfx', ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('gen_nrom.py', 'gen_all.py'):
                subprocess.run([sys.executable, root / 'gfx' / name], cwd=root,
                               check=True, capture_output=True)
            self.assertEqual((root / 'build/nrom_chrrom.bin').stat().st_size, 8192)
            for name in ('metasprites.inc', 'music.inc', 'nrom_data.inc'):
                self.assertTrue((root / 'build' / name).is_file())

    def test_source_inventory_retains_license_and_no_game_binaries(self):
        names = (ROOT / 'public-files.txt').read_text().splitlines()
        example = [name for name in names if name.startswith('examples/fablenes/')]
        self.assertEqual(len(example), 9)
        for name in example:
            if not name.endswith('README.md'):
                self.assertIn('SPDX-License-Identifier: Apache-2.0', (ROOT / name).read_text(encoding='utf-8'))
        self.assertFalse(any(name.endswith(('.nes', '.bin', '.exe')) for name in names))


if __name__ == '__main__':
    unittest.main()
