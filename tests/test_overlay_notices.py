"""Dependency-free checks for generated upstream attribution."""
import ast
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'firmware/usb-diag/vendor_overlay.py'
SPEC = importlib.util.spec_from_file_location('vendor_overlay', SOURCE)
overlay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlay)


class NoticeTests(unittest.TestCase):
    def test_notice_preserves_upstream_content_and_is_idempotent(self):
        upstream = '/* Copyright Example Author; upstream license notice */\nint example;\n'
        result = overlay.modified_notice(upstream, 'Example upstream')
        self.assertTrue(result.endswith(upstream))
        self.assertIn('Modified by the FM-1 custom firmware project', result)
        self.assertIn('Example upstream', result)
        self.assertEqual(result, overlay.modified_notice(result, 'Example upstream'))

    def test_every_public_transform_marks_its_source(self):
        transforms = {'nes_render_skip', 'nes_tiles', 'nes_apu', 'nes_profile', 'nes_microphone',
                      'boot_entry', 'cdc', 'device'}
        functions = {n.name: n for n in ast.parse(SOURCE.read_text()).body
                     if isinstance(n, ast.FunctionDef)}
        for name in transforms:
            with self.subTest(transform=name):
                calls = [n for n in ast.walk(functions[name]) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name) and n.func.id == 'modified_notice']
                self.assertEqual(len(calls), 1)

    def test_boot_adaptation_preserves_header_and_marks_modification(self):
        header = '/* Upstream copyright notice */\n'
        result = overlay.boot_entry(header+'void __attribute__((weak)) nvram_set_boot_state(u32 state) {}')
        self.assertIn(header, result)
        self.assertIn('Modified by the FM-1', result)
        self.assertIn('Jieli-Tech AC79 SDK', result)
        self.assertIn('extern void nvram_set_boot_state(u32 state);', result)

    def test_microphone_overlay_fails_closed_on_missing_or_duplicate_anchor(self):
        upstream = '#include "nes.h"\n    return state;\n}\n\nstatic inline void nes_write_joypad'
        result = overlay.nes_microphone(upstream)
        self.assertIn('if(address==0x4016)', result)
        self.assertIn('fm1_usb_audio_mic_bits() & 4u', result)
        for invalid in (upstream.replace('return state;', 'return other;'), upstream+upstream):
            with self.assertRaises(ValueError):
                overlay.nes_microphone(invalid)


if __name__ == '__main__':
    unittest.main()
