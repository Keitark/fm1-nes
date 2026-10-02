"""Offline application-only archive. No stock bytes, USB access or full ROM."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

FORMAT = 'fm1-app-v1'
LAYOUT = 'fm1-wl82-1m-v1'
ENTRY = 0x02000120
MAX_APP = 584956


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON member')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)


def manifest(app):
    require(0 < len(app) <= MAX_APP, 'Application empty or exceeds reviewed slot')
    return {'format': FORMAT, 'layout': LAYOUT, 'entry': ENTRY,
            'application_bytes': len(app), 'application_sha256': sha(app),
            'static_audit': 'passed', 'hardware_qualified': False}


def create(app_path, audit_path, output):
    app = app_path.read_bytes()
    info = manifest(app)
    audit = strict_json(audit_path.read_bytes())
    require(audit.get('static_audit') == 'passed'
            and audit.get('entry') == hex(ENTRY)
            and audit.get('application_bytes') == len(app)
            and audit.get('application_sha256') == sha(app),
            'Passed static audit does not match this application')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x') as archive:
        for name, data in (('manifest.json', json_bytes(info)), ('app.bin', app)):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return info


def load(path):
    require(path.stat().st_size <= MAX_APP + 65536, 'Oversized package')
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) == 2 and {i.filename for i in entries} == {'app.bin', 'manifest.json'},
                'Package must contain exactly app.bin and manifest.json')
        require(all(not i.flag_bits & 1 and i.file_size <=
                    (MAX_APP if i.filename == 'app.bin' else 4096) for i in entries),
                'Encrypted or oversized package member')
        info = strict_json(archive.read('manifest.json'))
        app = archive.read('app.bin')
    expected = manifest(app)
    # Exact types matter: JSON true must not pass for an integer field.
    require(isinstance(info, dict) and set(info) == set(expected)
            and all(type(info[k]) is type(v) and info[k] == v for k, v in expected.items()),
            'Unsupported manifest or application hash mismatch')
    return app, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json_bytes(create(args.app, args.audit, args.output)).decode(), end='')


if __name__ == '__main__':
    main()
