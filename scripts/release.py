"""Package exact reviewed source paths only; never include build/dependency trees."""
import hashlib
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'build', 'dist', '.deps', '.git', 'local', 'tmp',
                   'private-backups', '__pycache__', 'generated'}
ALLOWED_EXTENSIONS = {'.c', '.h', '.S', '.py', '.md', '.txt'}
# Patterns are intentionally split so the scanner source does not match itself.
PATTERNS = (
    ('private key', re.compile(r'-----BEGIN ' + r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('GitHub token', re.compile(r'gh[pousr]_' + r'[A-Za-z0-9]{30,}')),
    ('fine-grained token', re.compile(r'github_pat_' + r'[A-Za-z0-9_]{40,}')),
    ('AWS access key', re.compile(r'AKIA' + r'[A-Z0-9]{16}')),
    ('Windows user path', re.compile(r'[A-Za-z]:[\\/]Users[\\/]' + r'[^\s/\\]+', re.I)),
    ('owner SID', re.compile(r'S-1-5-21-' + r'\d+-\d+-\d+-\d+')),
)

def validate_name(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '\\' in name or ':' in name
            or p.as_posix() != name or any(x in ('.', '..') for x in p.parts)
            or any(x.lower() in FORBIDDEN_PARTS for x in p.parts)):
        raise ValueError('Unsafe release path: ' + name)
    if p.suffix not in ALLOWED_EXTENSIONS and name not in ('.gitignore', 'LICENSE'):
        raise ValueError('Non-source release path: ' + name)

def read_source(root, name):
    validate_name(name)
    path = root / name
    # Reject links/junctions, including ancestor junctions, even inside the root.
    for part in (path, *path.parents):
        if part == root: break
        if part.is_symlink() or getattr(part.stat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Release path is a link/reparse point: ' + name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Release path escaped root: ' + name)
    data = path.read_bytes()
    if len(data) > 1024 * 1024 or b'\0' in data:
        raise ValueError('Binary/oversized source: ' + name)
    text = data.decode('utf-8-sig')
    for category, pattern in PATTERNS:
        if pattern.search(text):
            raise ValueError('Review required (' + category + '): ' + name)
    return data

def gitignore_for(names):
    return ('# Only explicitly reviewed source paths are eligible for Git.\n*\n!*/\n'
            + ''.join('!/' + n + '\n' for n in sorted(names))
            + '/.deps/\n/build/\n/dist/\n/local/\n**/__pycache__/\n')

def inventory(root):
    root = root.resolve()
    names = (root / 'public-files.txt').read_text(encoding='utf-8').splitlines()
    if not names or len(set(names)) != len(names):
        raise ValueError('Empty or duplicate public source inventory')
    if not {'public-files.txt', '.gitignore', 'LICENSE', 'README.md'} <= set(names):
        raise ValueError('Required release metadata missing')
    result = {n: read_source(root, n) for n in names}
    if result['.gitignore'].decode('utf-8').replace('\r\n', '\n') != gitignore_for(names):
        raise ValueError('.gitignore does not match public-files.txt')
    return result

def package(root, destination):
    files = inventory(root)
    destination = destination.resolve()
    # Do not overwrite a previous release: choose a fresh destination/archive.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr('fm1-public/' + name, data)
        hashes = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                         for name, data in sorted(files.items()))
        archive.writestr('fm1-public/SOURCES.sha256', hashes)
    return len(files)

if __name__ == '__main__':
    out = ROOT / 'dist/fm1-public-source.zip'
    count = package(ROOT, out)
    print(f'Packaged {count} reviewed source files: {out}')
    print('SHA256 ' + hashlib.sha256(out.read_bytes()).hexdigest())
