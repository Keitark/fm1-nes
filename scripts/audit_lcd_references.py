"""Compare existing LCD records with pinned SDK examples; never changes firmware.

This is a literal-value comparison, not a C preprocessor, hardware qualification
or licensing determination. S/V preprocessor alternatives are reported as
source candidates, not as one combined executable initialization sequence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SDK_PIN = 'e30b1ee375d1f2993fc23bf92c8b99006a6e5f9d'
SDK_BASE = 'apps/common/ui/lcd_driver/'
NUMBER = r'(?:0[xX][0-9a-fA-F]+|[0-9]+)'


def numbers(text):
    tokens = [s.strip() for s in text.split(',') if s.strip()]
    if any(not re.fullmatch(NUMBER, s) for s in tokens):
        raise ValueError('Non-literal table input')
    return tuple(int(s, 16) if s.lower().startswith('0x') else int(s) for s in tokens)


def without_comments(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*', lambda m: '\n'*m.group().count('\n'),
                  text, flags=re.S)


def fm1_rows(text):
    body = re.search(r'panel_init\[21\]\[18\]\s*=\s*\{(.*?)\n\};', text, re.S)
    if not body:
        raise ValueError('Expected 21 x 18-byte FM-1 table')
    rows = [numbers(s) for s in re.findall(r'\{([^{}]+)\}', body.group(1))]
    if len(rows) != 21 or rows[1] != (0x45, 120):
        raise ValueError('Table shape or index-1 delay convention changed')
    for index, row in enumerate(rows):
        if not 2 <= len(row) <= 18 or any(v > 255 for v in row):
            raise ValueError('Unexpected record bytes')
        if index != 1 and (row[1] > 16 or len(row)-2 < row[1]):
            raise ValueError('Implicit payload bytes require manual review')
    return rows


def table_digest(rows):
    return hashlib.sha256(b''.join(bytes(r)+(b'\0'*(18-len(r))) for r in rows)).hexdigest()


def array_candidates(text):
    text = without_comments(text)
    body = re.search(r'static\s+const\s+InitCode\s+code1\[\]\s*=\s*\{(.*?)\n\s*\};', text, re.S)
    if not body:
        raise ValueError('SDK code1 table changed')
    row_pattern = (r'\{\s*('+NUMBER+r'|REGFLAG_DELAY)\s*,\s*('+NUMBER+
                   r')\s*(?:,\s*\{([^{}]*)\})?\s*\}')
    result = []
    for m in re.finditer(row_pattern, body.group(1)):
        cmd, count, values = m.groups()
        count = numbers(count)[0]
        data = numbers(values or '')
        line = text.count('\n', 0, body.start(1)+m.start())+1
        if cmd == 'REGFLAG_DELAY':
            result.append(('delay', (count,), line))
        else:
            if len(data) != count:
                raise ValueError('SDK initializer needs manual payload review')
            result.append((numbers(cmd)[0], data, line))
    if not result:
        raise ValueError('No SDK rows recognized')
    return result


def t3_candidates(text):
    text = without_comments(text)
    body = re.search(r'^void LCD_Init\(void\)\s*\{(.*?)^\}', text, re.S | re.M)
    if not body:
        raise ValueError('SDK T3 LCD_Init changed')
    result = []; cmd = None; data = []; line = None
    def flush():
        if cmd is not None:
            result.append((cmd, tuple(data), line))
    for m in re.finditer(r'\b(WriteComm|WriteData|Delay)\(\s*('+NUMBER+r')\s*\)', body.group(1)):
        kind, value = m.groups(); value = numbers(value)[0]
        pos = text.count('\n', 0, body.start(1)+m.start())+1
        if kind == 'WriteData':
            if cmd is None:
                raise ValueError('SDK data without command')
            data.append(value)
        else:
            flush(); cmd = None; data = []
            if kind == 'Delay':
                result.append(('delay', (value,), pos))
            else:
                cmd = value; line = pos
    flush()
    return result


def compare(rows, examples):
    result = []
    for index, row in enumerate(rows):
        cmd = 'delay' if index == 1 else row[0]
        data = (120,) if index == 1 else row[2:2+row[1]]
        exact = [f'{name}:{line}' for name, records in examples.items()
                 for candidate, payload, line in records if (candidate, payload) == (cmd, data)]
        result.append({'row': index, 'command': 'delay' if cmd == 'delay' else f'{cmd:02X}',
                       'payload': ' '.join(f'{v:02X}' for v in data),
                       'unused_explicit_bytes': list(row[2+row[1]:]) if index != 1 else [],
                       'sdk_exact_candidates': exact})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk', type=Path, required=True, help='Existing SDK Git checkout; no fetch performed')
    a = p.parse_args()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(a.sdk), *args])
    if git('rev-parse', 'HEAD').decode().strip() != SDK_PIN:
        raise ValueError('SDK checkout must be at the reviewed pin')
    paths = ['firmware/nes/boot/display_test.c', 'firmware/nes/src/fm1_board.c']
    tables = [fm1_rows((ROOT/name).read_text(encoding='utf-8')) for name in paths]
    if tables[0] != tables[1]:
        raise ValueError('Local panel tables differ')
    examples = {}; hashes = {}
    for variant in ('s', 'v', 't3'):
        name = f'lcd_st7789{variant}.c'
        raw = git('show', SDK_PIN+':'+SDK_BASE+name)
        hashes[name] = hashlib.sha256(raw).hexdigest()
        examples[name] = (t3_candidates if variant == 't3' else array_candidates)(raw.decode('utf-8'))
    rows = compare(tables[0], examples)
    print(json.dumps({'sdk_commit': SDK_PIN, 'sdk_file_sha256': hashes,
                      'table_sha256': table_digest(tables[0]),
                      'exact_candidate_rows': sum(bool(r['sdk_exact_candidates']) for r in rows),
                      'rows': rows}, indent=2))


if __name__ == '__main__':
    main()
