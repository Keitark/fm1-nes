"""Bounded literal-parser checks; no external SDK or hardware required."""
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('lcd_audit', ROOT/'scripts/audit_lcd_references.py')
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
TABLE_HASH = '280cb746088bea4a2fce2819c1415da0597a286120e3a8229449fbafdc1280c7'


class LcdReferenceTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT/'firmware/nes/src/fm1_board.c').read_text(encoding='utf-8')
        self.rows = audit.fm1_rows(self.text)

    def test_existing_tables_identical_and_hash_frozen(self):
        other = (ROOT/'firmware/nes/boot/display_test.c').read_text(encoding='utf-8')
        self.assertEqual(self.rows, audit.fm1_rows(other))
        self.assertEqual(len(self.rows), 21)
        self.assertEqual(audit.table_digest(self.rows), TABLE_HASH)

    def test_wire_payload_excludes_unused_byte_and_delay_marker(self):
        result = audit.compare(self.rows, {})
        self.assertEqual(result[1]['command'], 'delay')
        self.assertEqual(result[1]['payload'], '78')
        self.assertEqual(result[4]['payload'], '0C 0C 0C 00 33')
        self.assertEqual(result[4]['unused_explicit_bytes'], [0x33])

    def test_report_covers_every_row_and_hash(self):
        report = (ROOT/'LCD_PROVENANCE.md').read_text(encoding='utf-8')
        self.assertEqual([int(n) for n in re.findall(r'^\| (\d+) \|', report, re.M)], list(range(21)))
        self.assertIn(TABLE_HASH, report)

    def test_array_comments_and_conditional_candidates(self):
        source = '''static const InitCode code1[] = {
// {0x99,1,{0x99}},
#if EXAMPLE
{0xc2,1,{1}},
#else
{0xc2,2,{1,0xff}},
#endif
/* {0x98,0,{}} */
{REGFLAG_DELAY,120},
};'''
        result = audit.array_candidates(source)
        self.assertEqual(result, [(0xc2, (1,), 4), (0xc2, (1, 255), 6), ('delay', (120,), 9)])
        matches = audit.compare(self.rows, {'fixture': result})
        self.assertEqual(matches[9]['sdk_exact_candidates'], ['fixture:4'])
        self.assertEqual(matches[1]['sdk_exact_candidates'], ['fixture:9'])

    def test_t3_literal_calls_and_flush(self):
        source = '''void LCD_Init(void) {
WriteComm(0x11);
Delay(120);
// WriteComm(0x99);
WriteComm(0xc2);
WriteData(0x01);
WriteComm(0x29);
}'''
        self.assertEqual(audit.t3_candidates(source),
                         [(0x11, (), 2), ('delay', (120,), 3), (0xc2, (1,), 5), (0x29, (), 7)])

    def test_fail_closed_on_unexpected_literals_and_shapes(self):
        with self.assertRaises(ValueError):
            audit.numbers('1, SOME_MACRO')
        with self.assertRaises(ValueError):
            audit.fm1_rows(self.text.replace('panel_init[21][18]', 'panel_init[22][18]'))
        with self.assertRaises(ValueError):
            audit.array_candidates('static const InitCode code1[] = {\n{0xc2,2,{1}},\n};')
        with self.assertRaises(ValueError):
            audit.t3_candidates('void LCD_Init(void) {\nWriteData(1);\n}')


if __name__ == '__main__':
    unittest.main()
