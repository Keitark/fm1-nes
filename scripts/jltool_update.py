"""App-only sparse planner and wrapper for the existing guarded jluboottool.py.

plan is OFFLINE. Other subcommands contact hardware only when explicitly invoked.
No automatic flashing, retry, elevation, environment setup or reset.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

from app_package import json_bytes, load, require, sha
from jl_formats import AREA, SECTOR, SIZE, plan_digest, prepare

TOOL_PIN = 'adb3f18889e88ac512ce0a3c4d8cc3d3cb30696a'
TOOL_HASHES = {
    'jluboottool.py': '1ba91d8cd1a8faa7c33b5335a96deea717c993078da80befd1bc3702a14833d3',
    'jltech/uboot.py': 'c1301181d2dc2869bc7c8498d7cc11f8aaf95129adb5e583207b475a6a9ef553',
    'scsiio/win32port.py': '17c540f23c457318f7f971fd6aa8bf17f09d42fb69347749dd3000af31daf4e9',
}
HELPER_HASH = 'd41da6126760c9d66660bcc0cac8d27d221806c5e369a8036921efe68dca5376'


def check_tool(root):
    root = root.resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    require(git('rev-parse', 'HEAD') == TOOL_PIN, 'Wrong external jltool revision')
    changed = set(git('diff', 'HEAD', '--name-only').splitlines())
    require(changed == set(TOOL_HASHES), 'External tool has missing guards or unrelated modifications')
    require(not git('ls-files', '--others', '--exclude-standard'), 'Unreviewed untracked external tool files')
    for name, expected in TOOL_HASHES.items():
        require(sha((root/name).read_bytes().replace(b'\r\n', b'\n')) == expected,
                'External jltool guard source mismatch: '+name)
    require(sha((root/'data/loaderblobs/usb/wl82loader.bin').read_bytes()) == HELPER_HASH,
            'WL82 RAM helper mismatch')
    return root


class JLTool:
    """Protocol remains entirely inside the existing, reviewed external tool."""
    def __init__(self, root, device):
        require(re.fullmatch(r'\\\\\.\\PHYSICALDRIVE[0-9]+', device) is not None,
                'Explicit Windows PHYSICALDRIVE device required')
        self.root = check_tool(root)
        self.device = device

    def call(self, commands, log, mode='io'):
        require(mode in ('io', 'load', 'reset'), 'Unknown jltool operation')
        if mode == 'load':
            require(commands == ['help'], 'Loader mode accepts help only')
            flags = ['--fm1-load']
        elif mode == 'reset':
            require(commands == ['reset 1'], 'Reset mode accepts reset 1 only')
            flags = ['--reuse-loader', '--fm1-reset']
        else:
            require(commands and all(c.split()[0] in ('read', 'write') for c in commands),
                    'Only read/write commands permitted')
            flags = ['--reuse-loader', '--fm1-bench', '--fm1-nes-cdc']
        argv = [sys.executable, '-u', str(self.root/'jluboottool.py'),
                '--device', self.device, '--chip', 'wl82', '--io-size', '256', *flags, *commands]
        with log.open('x', encoding='utf-8') as stream:
            subprocess.run(argv, cwd=self.root, stdout=stream, stderr=subprocess.STDOUT,
                           check=True, timeout=60)
        # Guarded CLI also checks the flash ID and rejects incomplete transfers.
        text = log.read_text(encoding='utf-8')
        require('Target confirmed: WL82 UBOOT1.00 1.00' in text,
                'Missing strict device confirmation')
        if mode == 'load':
            require('The Loader has been successfully installed.' in text, 'Helper upload not confirmed')


def inputs(package, baseline, expected):
    app, info = load(package)
    raw = baseline.read_bytes()
    require(sha(raw) == expected, 'Owner backup hash mismatch')
    sectors, plan = prepare(raw, app, info)
    return raw, sectors, plan


def fresh(path):
    require(not any(c in str(path) for c in ('\n', '\r', '\0')), 'Invalid output path')
    path.mkdir(parents=True, exist_ok=False)


def save_plan(directory, raw, sectors, plan):
    (directory/'plan.json').write_bytes(json_bytes(plan))
    for row in plan['sectors']:
        address = row['offset']
        (directory/f'sector-{address:06x}.bin').write_bytes(sectors[address])
        (directory/f'restore-{address:06x}.bin').write_bytes(raw[address:address+SECTOR])


def read(tool, directory, address, length, label):
    path = directory/(label+'.bin')
    tool.call([f'read {address} {length} {path}'], directory/(label+'.log'))
    data = path.read_bytes()
    require(len(data) == length, 'Incomplete read: '+label)
    return data


def deploy(tool, directory, raw, sectors, plan, approved):
    require(approved == plan_digest(plan), 'Approval must match the recomputed private plan')
    require(plan['baseline_sha256'] == sha(raw) and plan['sector_bytes'] == SECTOR,
            'Plan baseline/geometry mismatch')
    order = [row['offset'] for row in plan['sectors']]
    require(plan['allocation_bytes'] in (583228, 584956)
            and 0 < plan['application_bytes'] <= plan['allocation_bytes'], 'Invalid application allocation')
    app_end = 0x4120 + plan['application_bytes']
    require(len(order) == len(set(order)) and set(order) == set(sectors)
            and all(AREA <= i < app_end and i % SECTOR == 0 for i in order), 'Invalid sparse sector scope')
    require(not order or order[-1] == AREA, 'Application directory must be written last')
    for row in plan['sectors']:
        i = row['offset']
        require(len(sectors[i]) == SECTOR and sha(sectors[i]) == row['after_sha256']
                and sha(raw[i:i+SECTOR]) == row['before_sha256'], 'Plan sector hash mismatch')
        require(all(a == b or AREA <= i+j < AREA+64 or 0x4120 <= i+j < app_end
                    for j, (a, b) in enumerate(zip(raw[i:i+SECTOR], sectors[i]))),
                'Sector changes protected bytes')
    receipt = {'status': 'preflight', 'plan_sha256': approved,
               'write_attempted': False, 'verified_sectors': [],
               'hardware_boot_verified': False, 'automatic_reset': False}
    def save():
        (directory/'receipt.json').write_bytes(json_bytes(receipt))
    save()
    try:
        require(read(tool, directory, 0, SIZE, 'preflight') == raw,
                'Device no longer matches owner backup; no writes permitted')
        save_plan(directory, raw, sectors, plan)
        for address in order:
            require(read(tool, directory, address, SECTOR, f'before-{address:06x}')
                    == raw[address:address+SECTOR], 'Sector changed after preflight')
            receipt.update(status='write_outcome_pending', current_sector=address, write_attempted=True)
            save()
            source = directory/f'sector-{address:06x}.bin'
            # Existing CLI erases this sector, programs 256-byte chunks and
            # checks its own readback. The wrapper performs independent readback.
            tool.call([f'write {address} {source}'], directory/f'write-{address:06x}.log')
            require(read(tool, directory, address, SECTOR, f'after-{address:06x}') == sectors[address],
                    'Independent program readback mismatch')
            receipt['verified_sectors'].append(address)
            receipt['status'] = 'sector_verified'
            save()
        final = read(tool, directory, 0, SIZE, 'final')
        # One full readback, compared sparsely. No full candidate is constructed.
        require(all(final[i:i+SECTOR] == sectors.get(i, raw[i:i+SECTOR])
                    for i in range(0, SIZE, SECTOR)), 'Final readback mismatch')
        receipt.update(status='written_and_readback_verified', full_readback_count=1)
    except Exception:
        receipt['status'] = 'failed_do_not_boot_or_automatically_retry'
        raise
    finally:
        save()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='op', required=True)
    for op in ('plan', 'flash', 'load-loader', 'backup', 'reset'):
        p = sub.add_parser(op)
        p.add_argument('--out', type=Path, required=True, help='Fresh private run directory')
        if op in ('plan', 'flash'):
            p.add_argument('--package', type=Path, required=True)
            p.add_argument('--baseline', type=Path, required=True)
            p.add_argument('--baseline-sha256', required=True)
        if op != 'plan':
            p.add_argument('--jltool', type=Path, required=True, help='Existing patched external checkout')
            p.add_argument('--device', required=True, help=r'Explicit \\.\PHYSICALDRIVE number')
        if op == 'flash':
            p.add_argument('--approve-plan', required=True, help='SHA-256 printed by offline plan')
            p.add_argument('--write', action='store_true', required=True)
    args = parser.parse_args()
    directory = args.out.resolve()
    if args.op in ('plan', 'flash'):
        raw, sectors, plan = inputs(args.package, args.baseline, args.baseline_sha256)
        if args.op == 'flash':
            require(args.approve_plan == plan_digest(plan), 'Plan approval mismatch; no device I/O')
        else:
            fresh(directory)
            save_plan(directory, raw, sectors, plan)
            print('PRIVATE plan SHA256 '+plan_digest(plan))
            print('Changed 4 KiB sectors: '+str(len(sectors))+'; directory last; no device I/O')
            return
    tool = JLTool(args.jltool, args.device)
    fresh(directory)
    if args.op == 'flash':
        print(json_bytes(deploy(tool, directory, raw, sectors, plan, args.approve_plan)).decode())
    elif args.op == 'backup':
        raw = read(tool, directory, 0, SIZE, 'backup')
        print('PRIVATE backup SHA256 '+sha(raw))
    else:
        mode = 'load' if args.op == 'load-loader' else 'reset'
        tool.call(['help'] if mode == 'load' else ['reset 1'], directory/(mode+'.log'), mode=mode)
        print('Explicit '+mode+' command completed; hardware boot not verified')


if __name__ == '__main__':
    main()
