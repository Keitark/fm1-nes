"""Offline host tests or WL82 application build. Never accesses the device."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware/nes'))
from build_env import SDK,CORE,SDK_PIN,CORE_PIN,TC
from dependencies import check

def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('target',choices=('host','firmware'))
    p.add_argument('--rom',type=Path);p.add_argument('--rom-sha256')
    p.add_argument('--out',type=Path,help='Firmware output directory (default build/firmware)')
    a=p.parse_args();check(CORE,CORE_PIN);check(SDK,SDK_PIN)
    if a.target=='host':
        if a.rom or a.rom_sha256 or a.out:p.error('ROM/output arguments apply only to firmware')
        for source,folder in (('firmware/nes','build/host-nes'),('firmware/usb-diag','build/host-usb')):
            run(['cmake','-S',source,'-B',folder,f'-DPython3_EXECUTABLE={sys.executable}'])
            run(['cmake','--build',folder,'--config','Release','--parallel','4'])
            run(['ctest','--test-dir',folder,'-C','Release','--output-on-failure'])
        return
    for exe in ('clang.exe','pi32v2-lto-wrapper.exe','llvm-objcopy.exe','llvm-nm.exe','llvm-objdump.exe'):
        if not (TC/exe).is_file():raise SystemExit('Missing existing Jieli compiler tool: '+str(TC/exe))
    if bool(a.rom)!=bool(a.rom_sha256):p.error('Supply both --rom and --rom-sha256')
    if a.rom:
        rom=a.rom.resolve();digest=a.rom_sha256
    else:
        sys.path.insert(0,str(ROOT/'firmware/nes/tests'))
        from make_diagnostic_rom import make_rom
        data=make_rom();rom=ROOT/'build/diagnostic.nes';rom.parent.mkdir(parents=True,exist_ok=True)
        rom.write_bytes(data);digest=hashlib.sha256(data).hexdigest()
    flags=['--controller','0','--peripheral-tests','--lcd-stock-fill','--lcd-stock-dma',
           '--lcd-stock-sequence','--nes-player','--keyscan-dma2','--nes-input-recovery',
           '--keyscan-irq','--keyscan-paced','--nes-audio-priority','--nes-live-fx','--nes-channel-fx',
           '--nes-render-skip','--lcd-async','--lcd-spi30','--lcd-rgb444','--lcd-direct','--nes-tiles','--nes-volume']
    run([sys.executable,ROOT/'firmware/usb-diag/build.py',*flags,'--rom',rom,'--rom-sha256',digest,
         '--out',(a.out or ROOT/'build/firmware').resolve()])

if __name__=='__main__':main()
