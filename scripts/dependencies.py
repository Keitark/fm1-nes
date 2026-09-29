"""Fetch pinned sources only on explicit --fetch; otherwise verify locations."""
import argparse
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'firmware/nes'))
from build_env import SDK,CORE,SDK_PIN,CORE_PIN

def check(path,pin):
    got=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    if got!=pin:raise ValueError('Wrong dependency commit: '+str(path))
    if subprocess.check_output(['git','-C',str(path),'status','--porcelain'],text=True).strip():
        raise ValueError('Dependency has local modifications: '+str(path))
    print('Verified '+str(path)+' @ '+pin)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args()
    for path,pin,url in ((CORE,CORE_PIN,'https://github.com/PeakRacing/nes.git'),
                         (SDK,SDK_PIN,'https://gitee.com/Jieli-Tech/fw-AC79_AIoT_SDK.git')):
        if not path.exists():
            if not a.fetch:raise SystemExit('Missing dependency. Set its environment path or run --fetch: '+str(path))
            path.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['git','clone','--filter=blob:none','--no-checkout',url,str(path)],check=True)
            subprocess.run(['git','-C',str(path),'checkout','--detach',pin],check=True)
        check(path,pin)

if __name__=='__main__':main()
