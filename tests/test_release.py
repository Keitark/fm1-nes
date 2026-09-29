import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch
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
                     'private-backups/data.c', 'D:/source.c', 'game.nes', 'a//b.c',
                     '.github/workflows/unreviewed.yml'):
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

    def init_git(self, root):
        self.fixture(root)
        release.git(root, 'init', '-q')
        release.git(root, 'config', 'user.name', 'Release Tests')
        release.git(root, 'config', 'user.email', 'tests@example.invalid')
        release.git(root, 'config', 'commit.gpgsign', 'false')
        release.git(root, 'config', 'core.autocrlf', 'false')
        release.git(root, 'config', 'core.hooksPath', str(root/'unused-hooks'))
        release.git(root, 'add', '.')
        release.git(root, 'commit', '-qm', 'Fixture')

    def test_git_inventory_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.init_git(root)
            result = release.check_git(root, release.inventory(root))
            self.assertEqual(result['tracked_files'], 5)
            self.assertEqual(result['commits'], 1)

    def test_git_rejects_force_added_unlisted_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.init_git(root)
            (root/'extra.c').write_text('not reviewed\n')
            release.git(root, 'add', '-f', 'extra.c')
            with self.assertRaisesRegex(ValueError, 'Tracked files differ'):
                release.check_git(root, release.inventory(root))

    def test_git_detects_secret_removed_from_current_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.init_git(root)
            secret = 'ghp_'+'x'*36
            (root/'source.c').write_text(secret)
            release.git(root, 'commit', '-am', 'Fixture change')
            (root/'source.c').write_text('safe again\n')
            release.git(root, 'commit', '-am', 'Fixture repair')
            with self.assertRaisesRegex(ValueError, 'GitHub token') as caught:
                release.check_git(root, release.inventory(root))
            self.assertNotIn(secret, str(caught.exception))

    def test_git_detects_deleted_disallowed_path_with_shared_blob(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.init_git(root)
            # Identical blob under a second name defeats representative-name scans.
            (root/'game.nes').write_bytes((root/'source.c').read_bytes())
            release.git(root, 'add', '-f', 'game.nes')
            release.git(root, 'commit', '-qm', 'Fixture extra path')
            release.git(root, 'rm', 'game.nes')
            release.git(root, 'commit', '-qm', 'Fixture remove path')
            with self.assertRaisesRegex(ValueError, 'Non-source release path'):
                release.check_git(root, release.inventory(root))

    def test_git_detects_annotated_tag_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.init_git(root)
            release.git(root, '-c', 'tag.gpgsign=false', 'tag', '-a', 'fixture',
                        '-m', 'ghp_'+'x'*36)
            with self.assertRaisesRegex(ValueError, 'GitHub token'):
                release.check_git(root, release.inventory(root))

    def test_git_rejects_shallow_checkout(self):
        with patch.object(release, 'git', return_value=b'true\n'):
            with self.assertRaisesRegex(ValueError, 'Full history required'):
                release.check_git(ROOT, [])

    def test_archives_repeat_identically_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); self.fixture(root)
            release.package(root, root/'first.zip')
            release.package(root, root/'second.zip')
            self.assertEqual((root/'first.zip').read_bytes(), (root/'second.zip').read_bytes())

    def test_cli_check_and_output_are_exclusive(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/release.py'),
                                 '--check', '--output', 'unused.zip'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'cannot be combined', result.stderr)

if __name__ == '__main__': unittest.main()
