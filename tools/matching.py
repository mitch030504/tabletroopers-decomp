#!/usr/bin/env python3
"""Private-target ARM64 matching. A diff score never substitutes for linked bytes."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('O2', 'O3', 'Os')
NATIVE_MEMBER = 'lib/arm64-v8a/libil2cpp.so'
METADATA_MEMBER = 'assets/bin/Data/Managed/Metadata/global-metadata.dat'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def save(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=path.parent,delete=False) as f:
        json.dump(data,f,indent=2);tmp=Path(f.name)
    tmp.replace(path)


class Elf:
    def __init__(self, path):
        self.path=Path(path)
        with self.path.open('rb') as f:
            h=f.read(64)
            if h[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',h,18)[0]!=183:
                raise ValueError('Expected little-endian ELF64 AArch64')
            self.phoff,self.shoff=struct.unpack_from('<QQ',h,32)
            self.phsize,self.phnum,self.shsize,self.shnum,self.shstr=struct.unpack_from('<HHHHH',h,54)
            self.segments=[]
            for n in range(self.phnum):
                f.seek(self.phoff+n*self.phsize);self.segments.append(struct.unpack('<IIQQQQQQ',f.read(56)))
            self.sections=[]
            for n in range(self.shnum):
                f.seek(self.shoff+n*self.shsize);self.sections.append(struct.unpack('<IIQQQQIIQQ',f.read(64)))

    def section(self,n):
        s=self.sections[n]
        with self.path.open('rb') as f:f.seek(s[4]);return f.read(s[5])

    def bytes_at(self,address,size,executable=False):
        for kind,flags,off,base,_,length,_,_ in self.segments:
            if kind==1 and base<=address and address+size<=base+length and (not executable or flags&1):
                with self.path.open('rb') as f:f.seek(off+address-base);return f.read(size)
        raise ValueError('Range outside file-backed executable input' if executable else 'Range outside ELF')

    def symbol(self,name):
        for n,s in enumerate(self.sections):
            if s[1]!=2:continue
            strings=self.section(s[6]);data=self.section(n)
            for offset in range(0,len(data),24):
                text,info,_,section,value,size=struct.unpack_from('<IBBHQQ',data,offset)
                end=strings.find(b'\0',text)
                if strings[text:end].decode()==name and section and info&15==2:
                    return value,size
        raise ValueError('Missing compiled function symbol '+name)


def object_file(path, name, code):
    """Derived ET_REL display object; not an original compiler object or acceptance oracle."""
    names=b'\0.text\0.symtab\0.strtab\0.shstrtab\0'
    strings=b'\0'+name.encode()+b'\0'
    symbols=bytes(24)+struct.pack('<IBBHQQ',1,0x12,0,1,0,len(code))
    data=bytearray(64)
    sections=[(0,0,0,0,0,0,0,0,0,0)]
    for label,kind,flags,payload,link,info,align,entsize in (
        ('.text',1,6,code,0,0,4,0),('.symtab',2,0,symbols,3,1,8,24),
        ('.strtab',3,0,strings,0,0,1,0),('.shstrtab',3,0,names,0,0,1,0)):
        while len(data)%align:data.append(0)
        off=len(data);data.extend(payload)
        sections.append((names.index(label.encode()),kind,flags,0,off,len(payload),link,info,align,entsize))
    while len(data)%8:data.append(0)
    shoff=len(data)
    for section in sections:data.extend(struct.pack('<IIQQQQIIQQ',*section))
    header=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+bytes(9),1,183,1,0,0,shoff,0,64,0,0,64,len(sections),4)
    data[:64]=header;Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_bytes(data)


def policy(sources):
    for name,text in sources.items():
        if not re.fullmatch(r'(src/[a-z_]+\.cpp|include/game\.hpp)',name):raise ValueError('Unapproved source path')
        if len(text.encode())>65536:raise ValueError('Source exceeds 64 KiB')
        if re.search(r'\b(?:asm|__asm__|__asm|naked)\b|\.incbin|\.byte|section\s*\(',text):raise ValueError('Inline assembly/embedded instruction sections are forbidden')
        for line in text.splitlines():
            m=re.match(r'\s*#\s*include\s+(.+)',line)
            if m and m[1].strip() not in ('"game.hpp"','<cstdint>','<cmath>'):
                raise ValueError('Unapproved include')


def setup(apk,root=ROOT):
    root=Path(root);cfg=json.loads((root/'config/pilot.json').read_text())
    if sha(apk)!=cfg['apk_sha256']:raise ValueError('Wrong APK version/hash')
    private=root/'orig';private.mkdir(exist_ok=True)
    with zipfile.ZipFile(apk) as z:
        for member,name,key in ((NATIVE_MEMBER,'libil2cpp.so','native_sha256'),(METADATA_MEMBER,'global-metadata.dat','metadata_sha256')):
            with z.open(member) as src,(private/name).open('wb') as dst:shutil.copyfileobj(src,dst)
            if sha(private/name)!=cfg[key]:raise ValueError('Extracted member hash mismatch')
    if Path(apk).resolve()!=(private/'TableTroopers.apk').resolve():
        # Avoid duplicating a 400 MiB APK on the same filesystem.
        dest=private/'TableTroopers.apk'
        if dest.exists() and sha(dest)!=cfg['apk_sha256']:raise ValueError('Existing private APK differs')
        if not dest.exists():
            try:os.link(apk,dest)
            except OSError:shutil.copyfile(apk,dest)
    elf=Elf(private/'libil2cpp.so')
    for function in cfg['functions']:
        code=elf.bytes_at(function['rva'],function['size'],True)
        expected=function.get('code_sha256')
        if expected and hashlib.sha256(code).hexdigest()!=expected:raise ValueError('Function hash mismatch')
        object_file(root/'build/expected'/f"{function['id']}.o",function['symbol'],code)
    return cfg


def toolchain(ndk):
    ndk=Path(ndk)
    props=(ndk/'source.properties').read_text()
    if not re.search(r'Pkg.Revision\s*=\s*27\.2\.12479018\b',props):raise ValueError('NDK r27c required')
    folder=ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
    compiler=folder/'clang++';linker=folder/'ld.lld'
    version=subprocess.check_output([str(compiler),'--version'],text=True)
    if '18.0.3' not in version or '12470979' not in version:raise ValueError('Unexpected Clang build')
    return compiler,linker


def compare(target,candidate):
    return {'exact_match':target==candidate,'target_code_sha256':hashlib.sha256(target).hexdigest(),
            'candidate_code_sha256':hashlib.sha256(candidate).hexdigest(),'target_bytes':len(target),'candidate_bytes':len(candidate),
            'matching_bytes':sum(x==y for x,y in zip(target,candidate)),
            'first_mismatch':next((i for i in range(max(len(target),len(candidate))) if i>=min(len(target),len(candidate)) or target[i]!=candidate[i]),None)}


def build(function_id,profile='O2',root=ROOT,ndk=None,count_attempt=True,job_id='local'):
    root=Path(root);cfg=json.loads((root/'config/pilot.json').read_text())
    function=next((f for f in cfg['functions'] if f['id']==function_id),None)
    if function is None or profile not in PROFILES:raise ValueError('Unknown function/profile')
    sources={f'src/{function_id}.cpp':(root/f'src/{function_id}.cpp').read_text(),'include/game.hpp':(root/'include/game.hpp').read_text()}
    policy(sources)
    source_hash=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    native=root/'orig/libil2cpp.so';metadata=root/'orig/global-metadata.dat'
    if sha(native)!=cfg['native_sha256'] or sha(metadata)!=cfg['metadata_sha256']:raise ValueError('Stale/mutated private input')
    compiler,linker=toolchain(ndk or os.environ.get('ANDROID_NDK_HOME',''))
    folder=root/'build'/function_id/profile;folder.mkdir(parents=True,exist_ok=True)
    target=Elf(native).bytes_at(function['rva'],function['size'],True)
    if function['rva']%4 or function['size']%4 or hashlib.sha256(target).hexdigest()!=function['code_sha256']:raise ValueError('Pinned function boundary/bytes changed')
    row={'id':function_id,'status':'not_run','exact_match':False,'profile':profile,'source_sha256':source_hash,
         'target_sha256':cfg['apk_sha256'],'native_sha256':cfg['native_sha256'],'rva':function['rva'],'semantic_verification':False}
    state_path=root/'build/state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    prior=state.get(function_id,{})
    seen=prior.get('attempt_keys',[]);key=source_hash+profile
    failures=prior.get('non_improving_attempts',0) if prior.get('job_id')==job_id else 0
    if count_attempt and key not in seen and failures>=25:
        raise ValueError('25 non-improving attempts reached; release this slice')
    flags=['--target=aarch64-linux-android25','-std=c++17','-'+profile,'-fPIC','-fomit-frame-pointer','-fno-stack-protector',
           '-fno-exceptions','-fno-rtti','-fno-math-errno','-ffp-contract=off','-ffunction-sections','-fno-unwind-tables','-fno-asynchronous-unwind-tables']
    result=subprocess.run([str(compiler),*flags,'-I',str(root/'include'),'-c',str(root/f'src/{function_id}.cpp'),'-o',str(folder/'compiled.o')],capture_output=True,text=True,timeout=60)
    if result.returncode:row['error']=result.stderr[-4000:]
    else:
        aliases='\n'.join(f'{name} = 0x{address:x};' for name,address in function['references'].items())
        script=f'ENTRY({function["symbol"]})\n{aliases}\nSECTIONS {{ .text 0x{function["rva"]:x} : {{ *(.text.{function["symbol"]}) *(.text*) }} /DISCARD/ : {{ *(.eh_frame*) *(.note*) *(.comment*) }} }}'
        (folder/'link.ld').write_text(script)
        linked=subprocess.run([str(linker),'-m','aarch64elf','--build-id=none','-T',str(folder/'link.ld'),str(folder/'compiled.o'),'-o',str(folder/'candidate.elf')],capture_output=True,text=True,timeout=60)
        if linked.returncode:row['error']=linked.stderr[-4000:]
        else:
            elf=Elf(folder/'candidate.elf');address,size=elf.symbol(function['symbol'])
            if address!=function['rva']:raise ValueError('Wrong candidate link address')
            candidate=elf.bytes_at(address,size,True);row.update(compare(target,candidate))
            row['status']='matched' if row['exact_match'] else 'mismatch'
            object_file(folder/'display.o',function['symbol'],candidate)
            # decomp.wtf builds this per-unit path; comparisons use post-link instructions.
            object_file(root/'build/current'/f'{function_id}.o',function['symbol'],candidate)
    if count_attempt and key not in seen:
        seen.append(key)
        best=prior.get('best_matching_bytes',-1)
        improved=row.get('matching_bytes',-1)>best or row['exact_match']
        failures=0 if improved else failures+1
    else:best=prior.get('best_matching_bytes',-1)
    row.update(attempts=len(seen),attempt_keys=seen,non_improving_attempts=failures,job_id=job_id,
               best_matching_bytes=max(best,row.get('matching_bytes',-1)))
    state[function_id]=row;save(state_path,state);save(folder/'report.json',row)
    return row


def report(root=ROOT):
    root=Path(root);cfg=json.loads((root/'config/pilot.json').read_text())
    state=json.loads((root/'build/state.json').read_text()) if (root/'build/state.json').exists() else {}
    functions=[{k:v for k,v in state.get(f['id'],{'id':f['id'],'status':'not_run','exact_match':False}).items() if k!='attempt_keys'} for f in cfg['functions']]
    for fn,row in zip(cfg['functions'],functions):
        if not row.get('source_sha256'):continue
        files={f"src/{fn['id']}.cpp":(root/f"src/{fn['id']}.cpp").read_text(),'include/game.hpp':(root/'include/game.hpp').read_text()}
        current=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        if row.get('source_sha256') and row['source_sha256']!=current:
            row.update(status='not_run',exact_match=False,error='Candidate/header changed; revalidation required')
    return {'target_sha256':cfg['apk_sha256'],'repository_url':'https://github.com/mitch030504/tabletroopers-decomp','pilot_functions':len(functions),
            'matched_functions':sum(bool(f.get('exact_match')) for f in functions),'matched_bytes':sum(f.get('target_bytes',0) for f in functions if f.get('exact_match')),
            'functions':functions,'scope':'Three-function pilot, not whole-game progress','semantic_verification':False}


def dispatch(function,profile,root,ndk,job_id,revalidate=False):
    url=os.getenv('TT_MATCHING_BUILDER_URL')
    if not url:return build(function,profile,root,ndk,count_attempt=not revalidate,job_id=job_id)
    import urllib.request,base64
    sources={f'src/{function}.cpp':(root/f'src/{function}.cpp').read_text(),'include/game.hpp':(root/'include/game.hpp').read_text()}
    request=urllib.request.Request(url+'/build',data=json.dumps({'function':function,'profile':profile,'job_id':job_id,'sources':sources,'revalidate':revalidate}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=100) as response:output=json.load(response)
    if output.get('error'):raise ValueError(output['error'])
    code=base64.b64decode(output.pop('candidate_b64'))
    cfg=json.loads((root/'config/pilot.json').read_text());fn=next(f for f in cfg['functions'] if f['id']==function)
    object_file(root/'build/current'/f'{function}.o',fn['symbol'],code)
    state=json.loads((root/'build/state.json').read_text()) if (root/'build/state.json').exists() else {}
    state[function]=output;save(root/'build/state.json',state)
    return output


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('build','verify','report','calibrate'));parser.add_argument('--function');parser.add_argument('--profile',choices=PROFILES,default='O2');parser.add_argument('--ndk');parser.add_argument('--job-id',default=os.getenv('TT_MATCHING_JOB','local'));parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();root=args.root
    (root/'build').mkdir(exist_ok=True)
    with (root/'build/.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.action=='report':output=report(root)
        elif args.action=='build':
            if not args.function:parser.error('--function required')
            output=dispatch(args.function,args.profile,root,args.ndk,args.job_id)
        else:
            cfg=json.loads((root/'config/pilot.json').read_text())
            for fn in cfg['functions']:
                if args.action=='calibrate':
                    rows=[build(fn['id'],profile,root,args.ndk,count_attempt=False) for profile in PROFILES]
                    best=max(rows,key=lambda r:(r.get('exact_match',False),r.get('matching_bytes',-1)))
                    build(fn['id'],best['profile'],root,args.ndk,count_attempt=False)
                else:
                    prior=report(root);entry=next(x for x in prior['functions'] if x['id']==fn['id'])
                    dispatch(fn['id'],entry.get('profile',fn.get('profile','O2')),root,args.ndk,args.job_id,revalidate=True)
            output=report(root)
        print(json.dumps(output,indent=2))

if __name__=='__main__':main()
