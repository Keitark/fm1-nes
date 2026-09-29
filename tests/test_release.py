import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release', ROOT/'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def fixture(self, root):
        names = ['.gitignore', 'LICENSE', 'README.md', 'public-files.txt', 'source.c']
        for name in names: (root/name).write_text('source\n', encoding='utf-8')
        (root/'public-files.txt').write_text('\n'.join(names)+'\n', encoding='utf-8')
        (root/'.gitignore').write_text(release.gitignore_for(names), encoding='utf-8')

    def test_current_inventory(self):
        self.assertGreater(len(release.inventory(ROOT)), 50)

    def test_excludes_unlisted_rom_generated_c_and_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.fixture(root)
            for name in ('game.nes', 'generated_rom.c', '.env', 'dump.bin', 'session.json'):
                (root/name).write_bytes(b'PRIVATE-CANARY')
            out = root/'release.zip'; release.package(root, out)
            with zipfile.ZipFile(out) as archive:
                for name in archive.namelist():
                    self.assertNotIn(b'PRIVATE-CANARY', archive.read(name))
                self.assertIn('fm1-public/SOURCES.sha256', archive.namelist())
            with self.assertRaises(FileExistsError): release.package(root, out)

    def test_rejects_paths(self):
        for name in ('../source.c', '/source.c', 'build/generated.c', '.deps/vendor.h',
                     'private-backups/data.c', 'D:/source.c', 'game.nes', 'a//b.c'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.validate_name(name)

    def test_rejects_binary_and_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.fixture(root)
            for data in (b'\0ROM', ('ghp_'+'x'*36).encode(),
                         ('-----BEGIN '+'PRIVATE KEY-----').encode()):
                (root/'source.c').write_bytes(data)
                with self.assertRaises(ValueError): release.inventory(root)

    def test_rejects_ignore_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.fixture(root)
            (root/'.gitignore').write_text('*\n', encoding='utf-8')
            with self.assertRaises(ValueError): release.inventory(root)

if __name__ == '__main__': unittest.main()
