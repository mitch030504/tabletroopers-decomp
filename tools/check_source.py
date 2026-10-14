from matching import ROOT,policy
sources={str(p.relative_to(ROOT)):p.read_text() for folder in ('src','include') for p in (ROOT/folder).glob('*') if p.suffix in ('.cpp','.hpp')}
policy(sources)
print('Candidate source policy passed')
