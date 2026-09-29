"""Embed an explicit local, hash-checked iNES asset. No ROM downloads."""
import argparse
import hashlib
from pathlib import Path
import re

# Legacy identifiers used by the existing linked-image audit. Neither is a
# bundled commercial game; select_rom supplies the validated input metadata.
ROMS = {'smb1': (0,b'', ''), 'rom50': (0,b'', '')}
_paths = {}

def validate(data):
    if len(data)<16 or data[:4]!=b'NES\x1a':raise ValueError('Expected iNES header')
    mapper=(data[6]>>4)|(data[7]&0xf0)
    if (data[4] not in (1,2) or data[6]&0x0e or data[7]&0x0f or any(data[8:16])
        or mapper not in (0,3) or data[5] not in ((1,) if mapper==0 else (1,2,4))):
        raise ValueError('Only bounded NTSC iNES1 NROM/CNROM without trainer/save RAM is supported')
    if len(data)!=16+data[4]*16384+data[5]*8192:raise ValueError('ROM length differs from header')

def select_rom(source, expected, cartridge='smb1'):
    if cartridge not in ROMS or not re.fullmatch(r'[0-9a-fA-F]{64}',expected or ''):
        raise ValueError('Explicit expected SHA256 and known profile required')
    source=Path(source).resolve();data=source.read_bytes();validate(data)
    digest=hashlib.sha256(data).hexdigest()
    if digest!=expected.lower():raise ValueError('ROM SHA256 mismatch')
    ROMS[cartridge]=(len(data),data[:16],digest);_paths[cartridge]=source
    return ROMS[cartridge]

def rom_path(name):
    if name not in _paths:raise ValueError('No explicit ROM selected')
    return _paths[name]

def generate(source,output,cartridge='smb1'):
    size,header,digest=ROMS[cartridge];data=Path(source).read_bytes()
    if not size or (len(data),data[:16],hashlib.sha256(data).hexdigest())!=(size,header,digest):
        raise ValueError('ROM changed or not selected; refusing integration')
    rows=[','.join(f'0x{x:02x}' for x in data[i:i+16])+',' for i in range(0,len(data),16)]
    code=('/* Generated local ROM asset; do not redistribute without permission. */\n'
          '#include "fm1_rom50.h"\nstatic const uint8_t cartridge[] = {\n'+'\n'.join(rows)+'\n};\n'
          'const uint8_t *fm1_rom50_data(size_t *size) {\n'
          '    if(size) *size=sizeof(cartridge);\n    return cartridge;\n}\n'
          'int fm1_rom50_start(void) {\n'
          '    return fm1_nes_target_start(cartridge,sizeof(cartridge));\n}\n')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(code,encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--sha256',required=True)
    a=p.parse_args();select_rom(a.source,a.sha256);generate(a.source,a.output)
