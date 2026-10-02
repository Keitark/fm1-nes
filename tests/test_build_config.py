"""Synthetic private-ROM defaults only; no commercial assets or hardware."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fm1_build',ROOT/'scripts/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class BuildConfigTests(unittest.TestCase):
    def test_absent_private_config_keeps_source_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(build.resolve_rom(config=Path(folder)/'rom.json'),(None,None))
    def test_private_relative_path_and_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'test.nes').write_bytes(b'SYNTHETIC')
            path=root/'rom.json';path.write_text(json.dumps({'rom':'test.nes','sha256':'A'*64}))
            self.assertEqual(build.resolve_rom(config=path),((root/'test.nes').resolve(),'a'*64))
    def test_explicit_cli_and_diagnostic_override_private_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rom.json';path.write_text('INVALID')
            self.assertEqual(build.resolve_rom('custom.nes','b'*64,config=path),(Path('custom.nes').resolve(),'b'*64))
            self.assertEqual(build.resolve_rom(diagnostic=True,config=path),(None,None))
            with self.assertRaises(ValueError):build.resolve_rom('custom.nes','b'*64,True,path)
    def test_bad_config_or_missing_rom_never_silently_falls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rom.json'
            for info in ({'rom':'missing.nes','sha256':'a'*64},{'rom':1,'sha256':'a'*64},{'rom':'x','sha256':'short'},{'rom':'x','sha256':'a'*64,'command':'not-allowed'},[]):
                path.write_text(json.dumps(info))
                with self.assertRaises(ValueError):build.resolve_rom(config=path)
    def test_cli_requires_both_path_and_hash(self):
        with self.assertRaises(ValueError):build.resolve_rom('test.nes')
        with self.assertRaises(ValueError):build.resolve_rom(digest='a'*64)
