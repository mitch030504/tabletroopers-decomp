"""Synthetic compiler/linker test; no game data or Android SDK required."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('matching',Path(__file__).parents[1]/'tools/matching.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@unittest.skipUnless(shutil.which('clang') and shutil.which('ld.lld'),'clang and ld.lld required')
class LinkedFixtures(unittest.TestCase):
    def code(self,source,callee):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'source.cpp').write_text(source)
            subprocess.run(['clang','--target=aarch64-none-elf','-O2','-fomit-frame-pointer','-c',str(p/'source.cpp'),'-o',str(p/'source.o')],check=True,capture_output=True)
            (p/'link.ld').write_text('ENTRY(f)\ncallee = '+hex(callee)+'; SECTIONS { .text 0x10000 : { *(.text*) } }')
            subprocess.run(['ld.lld','-T',str(p/'link.ld'),str(p/'source.o'),'-o',str(p/'result')],check=True,capture_output=True)
            e=m.Elf(p/'result');address,size=e.symbol('f');self.assertEqual(address,0x10000)
            return e.bytes_at(address,size,True)
    def test_call_and_constant_mutations_fail_after_linking(self):
        source='extern "C" int callee(int); extern "C" int f(int x){return callee(x)+1;}'
        target=self.code(source,0x12000)
        self.assertTrue(m.compare(target,self.code(source,0x12000))['exact_match'])
        self.assertFalse(m.compare(target,self.code(source,0x12004))['exact_match'])
        self.assertFalse(m.compare(target,self.code(source.replace('+1','+2'),0x12000))['exact_match'])
