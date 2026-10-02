"""Check or package source only. Technical checks are not legal clearance."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {'build', 'dist', '.deps', '.git', 'local', 'tmp',
                   'private-backups', '__pycache__', 'generated'}
ALLOWED_EXTENSIONS = {'.c', '.h', '.S', '.py', '.md', '.txt'}
SPECIAL_FILES = {'.gitignore', 'LICENSE', '.github/workflows/source-release.yml'}
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
    if p.suffix not in ALLOWED_EXTENSIONS and name not in SPECIAL_FILES:
        raise ValueError('Non-source release path: ' + name)

def check_content(data, name):
    if len(data) > 1024 * 1024 or b'\0' in data:
        raise ValueError('Binary/oversized source: ' + name)
    text = data.decode('utf-8-sig')
    for category, pattern in PATTERNS:
        if pattern.search(text):
            # Never echo the matched credential or file contents.
            raise ValueError('Review required (' + category + '): ' + name)


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
    check_content(data, name)
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

def git(root, *args, input=None):
    return subprocess.run(['git', '-C', str(root), *args], input=input,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout


def check_git(root, names):
    """Inspect local reachable history, not remote issues/assets or reflogs."""
    if git(root, 'rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('Full history required; fetch with depth 0 before checking')
    tracked = {s.decode('utf-8') for s in git(root, 'ls-files', '-z').split(b'\0') if s}
    if tracked != set(names):
        raise ValueError('Tracked files differ from public-files.txt: ' +
                         ', '.join(sorted(tracked ^ set(names))))
    # Check every historical path/mode, including deleted files and alternate
    # names of the same blob, rather than only rev-list's representative names.
    commits = git(root, 'rev-list', '--all', 'HEAD').decode('ascii').splitlines()
    objects = set(commits)
    for commit in commits:
        for entry in git(root, 'ls-tree', '-r', '-z', commit).split(b'\0'):
            if not entry:
                continue
            metadata, name_bytes = entry.split(b'\t', 1)
            mode, kind, oid = metadata.split()
            name = name_bytes.decode('utf-8')
            validate_name(name)
            if mode not in (b'100644', b'100755') or kind != b'blob':
                raise ValueError('Non-regular historical entry: ' + name)
            objects.add(oid.decode('ascii'))
    # Include tag messages as well as commits and reachable blob contents.
    objects.update(line.split()[0] for line in
                   git(root, 'rev-list', '--objects', '--all', 'HEAD').decode('utf-8').splitlines())
    query = ('\n'.join(sorted(objects))+'\n').encode('ascii')
    selected = []
    for entry in git(root, 'cat-file', '--batch-check', input=query).splitlines():
        oid, kind, size = entry.split()
        if kind in (b'blob', b'commit', b'tag'):
            if int(size) > 1024 * 1024:
                raise ValueError('Oversized historical object: ' + oid.decode('ascii'))
            selected.append(oid)
    payload = git(root, 'cat-file', '--batch', input=b'\n'.join(selected)+b'\n')
    offset = 0
    for expected in selected:
        end = payload.index(b'\n', offset)
        oid, kind, size = payload[offset:end].split()
        if oid != expected:
            raise ValueError('Unexpected Git batch response')
        offset = end+1
        length = int(size)
        check_content(payload[offset:offset+length], 'Git object '+oid.decode('ascii'))
        offset += length+1
    return {'commits': len(commits), 'objects_scanned': len(selected),
            'tracked_files': len(tracked)}


def package(root, destination):
    files = inventory(root)
    destination = destination.resolve()
    # Do not overwrite a previous release: choose a fresh destination/archive.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(zip_entry(name), data)
        hashes = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                         for name, data in sorted(files.items()))
        archive.writestr(zip_entry('SOURCES.sha256'), hashes)
    return len(files)

def zip_entry(name):
    info = zipfile.ZipInfo('fm1-public/' + name, (1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check without making an archive')
    parser.add_argument('--git', action='store_true', help='Scan tracked inventory and full local reachable history')
    parser.add_argument('--output', type=Path, help='Fresh ZIP path; existing files are never overwritten')
    args = parser.parse_args()
    if args.check and args.output:
        parser.error('--check cannot be combined with --output')
    files = inventory(ROOT)
    if args.git:
        print('Git checks:', check_git(ROOT, files))
    print(f'Source checks passed: {len(files)} files (limited pattern scan; not rights clearance)')
    if args.check:
        return
    out = args.output or ROOT / 'dist/fm1-public-source.zip'
    count = package(ROOT, out)
    print(f'Packaged {count} reviewed source files: {out}')
    print('SHA256 ' + hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
