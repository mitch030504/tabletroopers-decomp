import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('matching',Path(__file__).parents[1]/'tools/matching.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MatchingTests(unittest.TestCase):
    def test_instruction_constant_and_call_changes_never_match(self):
        original=bytes.fromhex('20008052c0035fd6') # Synthetic mov w0,#1; ret
        self.assertTrue(m.compare(original,original)['exact_match'])
        for changed in (bytes.fromhex('40008052c0035fd6'),original[:-4],original+b'\0\0\0\0',bytes.fromhex('01000094c0035fd6')):
            self.assertFalse(m.compare(original,changed)['exact_match'])
        self.assertFalse(m.compare(bytes.fromhex('01000094'),bytes.fromhex('02000094'))['exact_match'])

    def test_display_object_has_real_function_and_exact_payload(self):
        code=bytes.fromhex('20008052c0035fd6')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'fixture.o';m.object_file(p,'fixture',code);elf=m.Elf(p)
            self.assertEqual(elf.symbol('fixture'),(0,8));self.assertEqual(elf.section(1),code)
            self.assertEqual(struct.unpack_from('<H',p.read_bytes(),16)[0],1)

    def test_assembly_and_escape_paths_rejected(self):
        for sources in ({'../auth.json':'secret'},{'src/a.cpp':'asm("ret");'},{'src/a.cpp':'#include "/auth/auth.json"'},{'src/a.cpp':'__attribute__((section(".text"))) char data[4];'}):
            with self.assertRaises(ValueError):m.policy(sources)
        m.policy({'src/a.cpp':'#include "game.hpp"\nfloat f(){return 1.0f;}','include/game.hpp':'#include <cstdint>'})

    def test_wrong_apk_rejected_before_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'wrong.apk';p.write_bytes(b'not the game')
            with self.assertRaisesRegex(ValueError,'Wrong APK'):m.setup(p)
            self.assertFalse((Path(folder)/'orig').exists())

if __name__=='__main__':unittest.main()
