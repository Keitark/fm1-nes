import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import embed_rom50 as embed
from make_diagnostic_rom import make_rom,make_cnrom_rom

class EmbedTests(unittest.TestCase):
    def test_original_diagnostics_roundtrip(self):
        for data in (make_rom(),make_rom(2),make_cnrom_rom()):
            with tempfile.TemporaryDirectory() as d:
                source=Path(d)/'input.nes';out=Path(d)/'rom.c';source.write_bytes(data)
                embed.select_rom(source,hashlib.sha256(data).hexdigest())
                embed.generate(source,out)
                body=out.read_text().split('cartridge[] = {\n',1)[1].split('};',1)[0]
                self.assertEqual(bytes(int(x.strip(),16) for x in body.split(',') if x.strip()),data)
    def test_changed_asset_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.nes';out=Path(d)/'rom.c';data=make_rom()
            source.write_bytes(data);embed.select_rom(source,hashlib.sha256(data).hexdigest())
            out.write_text('preserve');source.write_bytes(data[:-1]+bytes([data[-1]^1]))
            with self.assertRaises(ValueError):embed.generate(source,out)
            self.assertEqual(out.read_text(),'preserve')
    def test_bad_hash_and_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.nes';source.write_bytes(make_rom())
            for digest in ('','nope','0'*64):
                with self.assertRaises(ValueError):embed.select_rom(source,digest)
        for data in (b'',make_rom()[:-1],make_rom()+b'x'):
            with self.assertRaises(ValueError):embed.validate(data)
        for offset,value in ((4,3),(5,2),(6,4),(6,2),(6,8),(6,0x10),(7,8),(8,1)):
            data=bytearray(make_rom());data[offset]=value
            with self.assertRaises(ValueError):embed.validate(data)

if __name__=='__main__':unittest.main()
