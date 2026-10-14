#!/usr/bin/env python3
"""Bring your own APK; generate private targets and a decomp.wtf-compatible build."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'tools'))
from matching import ROOT,setup,save,toolchain

parser=argparse.ArgumentParser()
parser.add_argument('--apk',type=Path,default=ROOT/'orig/TableTroopers.apk')
parser.add_argument('--ndk',type=Path,default=os.environ.get('ANDROID_NDK_HOME'))
args=parser.parse_args()
cfg=setup(args.apk)
if not os.getenv('TT_MATCHING_BUILDER_URL'):
    if args.ndk is None:parser.error('Set ANDROID_NDK_HOME to Android NDK r27c or pass --ndk')
    toolchain(args.ndk)
    save(ROOT/'build/toolchain.json',{'ndk':str(args.ndk.resolve())})
ndk_args='' if os.getenv('TT_MATCHING_BUILDER_URL') else ' --ndk '+str(args.ndk.resolve())
lines=['rule match','  command = '+sys.executable+' tools/matching.py build --function $function --profile $profile'+ndk_args,'  description = ARM64 compile and byte comparison: $function']
units=[]
for fn in cfg['functions']:
    name=fn['id'];base=f'build/current/{name}.o'
    lines.extend([f'build {base}: match src/{name}.cpp include/game.hpp config/pilot.json tools/matching.py',f'  function = {name}',f'  profile = {fn.get("profile","O2")}'])
    units.append({'name':name,'target_path':f'build/expected/{name}.o','base_path':base,'metadata':{'source_path':f'src/{name}.cpp','complete':False}})
lines.append('default '+' '.join(x['base_path'] for x in units))
(ROOT/'build.ninja').write_text('\n'.join(lines)+'\n')
save(ROOT/'objdiff.json',{'custom_make':'ninja','build_target':False,'build_base':True,'units':units,'options':{'combineTextSections':True,'combineDataSections':False}})
print('Prepared three ARM64 units. No whole-game reconstruction or runtime claim.')
