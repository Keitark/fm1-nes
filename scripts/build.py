"""Offline host tests or WL82 application build. Never accesses the device."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware/nes'))
from build_env import SDK,CORE,SDK_PIN,CORE_PIN,TC
from dependencies import check

def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)

def resolve_rom(rom=None,digest=None,diagnostic=False,config=None):
    """Private defaults are optional; explicit CLI wins, invalid defaults fail."""
    if bool(rom)!=bool(digest):raise ValueError('Supply both --rom and --rom-sha256')
    if diagnostic:
        if rom:raise ValueError('--diagnostic cannot be combined with --rom')
        return None,None
    if rom:return Path(rom).resolve(),digest
    config=Path(config or ROOT/'local/rom.json')
    if not config.exists():return None,None
    info=json.loads(config.read_text(encoding='utf-8'))
    if not isinstance(info,dict) or set(info)!={'rom','sha256'}:
        raise ValueError('Private ROM config must contain only rom and sha256')
    if not isinstance(info['rom'],str) or not info['rom'] or not isinstance(info['sha256'],str) or not re.fullmatch('[0-9a-fA-F]{64}',info['sha256']):
        raise ValueError('Invalid private ROM path/hash')
    source=Path(info['rom'])
    source=(source if source.is_absolute() else config.parent/source).resolve()
    if not source.is_file():raise ValueError('Configured ROM missing; refusing diagnostic fallback')
    return source,info['sha256'].lower()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=('host','firmware'))
    p.add_argument('--rom',type=Path);p.add_argument('--rom-sha256')
    p.add_argument('--diagnostic',action='store_true',help='Explicit original diagnostic cartridge, ignoring private local/rom.json')
    p.add_argument('--out',type=Path,help='Firmware output directory (default build/firmware)')
    p.add_argument('--usb-audio',action='store_true',help='Optional MDX-derived UAC1 stereo duplex plus CDC profile')
    p.add_argument('--package',type=Path,help='Create a fresh app-only .fm1app after a passed static audit; no device I/O')
    a=p.parse_args();check(CORE,CORE_PIN);check(SDK,SDK_PIN)
    if a.target=='host':
        if a.rom or a.rom_sha256 or a.diagnostic or a.out or a.usb_audio or a.package:p.error('ROM/output/audio/package arguments apply only to firmware; host tests cover both profiles')
        for source,folder in (('firmware/nes','build/host-nes'),('firmware/usb-diag','build/host-usb')):
            run(['cmake','-S',source,'-B',folder,f'-DPython3_EXECUTABLE={sys.executable}'])
            run(['cmake','--build',folder,'--config','Release','--parallel','4'])
            run(['ctest','--test-dir',folder,'-C','Release','--output-on-failure'])
        return
    for exe in ('clang.exe','pi32v2-lto-wrapper.exe','llvm-objcopy.exe','llvm-nm.exe','llvm-objdump.exe'):
        if not (TC/exe).is_file():raise SystemExit('Missing existing Jieli compiler tool: '+str(TC/exe))
    try:rom,digest=resolve_rom(a.rom,a.rom_sha256,a.diagnostic)
    except (ValueError,OSError) as error:p.error(str(error))
    if rom:
        print('Using explicit/private ROM:',rom,'expected SHA256:',digest)
    else:
        sys.path.insert(0,str(ROOT/'firmware/nes/tests'))
        from make_diagnostic_rom import make_rom
        data=make_rom();rom=ROOT/'build/diagnostic.nes';rom.parent.mkdir(parents=True,exist_ok=True)
        rom.write_bytes(data);digest=hashlib.sha256(data).hexdigest()
    flags=['--controller','0','--peripheral-tests','--lcd-stock-fill','--lcd-stock-dma',
           '--lcd-stock-sequence','--nes-player','--keyscan-dma2','--nes-input-recovery',
           '--keyscan-irq','--keyscan-paced','--nes-audio-priority','--nes-live-fx','--nes-channel-fx',
           '--nes-render-skip','--lcd-async','--lcd-spi30','--lcd-rgb444','--lcd-direct','--nes-tiles','--nes-volume']
    if a.usb_audio:flags+=['--usb-audio']
    output=(a.out or ROOT/('build/firmware-audio' if a.usb_audio else 'build/firmware')).resolve()
    if a.package and a.package.exists():p.error('Package already exists; choose a fresh output')
    run([sys.executable,ROOT/'firmware/usb-diag/build.py',*flags,'--rom',rom,'--rom-sha256',digest,'--out',output])
    if a.package:
        from app_package import create
        info=create(output/'fm1-usb-diag.app.bin',output/'static-audit.json',a.package.resolve())
        print('Created application-only package:',a.package.resolve(),info['application_sha256'])

if __name__=='__main__':main()
