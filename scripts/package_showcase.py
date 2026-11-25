#!/usr/bin/env python3
"""Package this Skill, optionally with an isolated original-input case. Never calls a model."""
import argparse,hashlib,io,json,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def skill_files(root=ROOT):
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if not p.is_file() or p.is_symlink() or any(x.startswith('.') or x in ('__pycache__','renders','output','node_modules','inputs','ops','agent-home') for x in rel.parts):continue
  if p.suffix not in ('.md','.py','.sh','.js','.cjs','.html','.css','.json','.txt','.yaml','.yml','.png','.jpg','.jpeg','.gif','.webp','.svg','.woff','.woff2'):continue
  yield p

def package(out,case=None):
 out=Path(out).resolve()
 if out.exists():raise ValueError('Choose a new output file; packages are immutable')
 files={'Skill/'+p.relative_to(ROOT).as_posix():p for p in skill_files()}
 if case:
  case=Path(case).resolve()
  for p in sorted(case.rglob('*')):
   if p.is_file() and not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(case).parts):
    rel=p.relative_to(case).as_posix()
    if rel!='CASE.md' and not rel.startswith('inputs/'):raise ValueError('Case contains a non-input artifact: '+rel)
    files[rel]=p
  if 'inputs/manual.pdf' not in files or 'CASE.md' not in files:raise ValueError('Case needs CASE.md and inputs/manual.pdf')
 manifest={'skill':ROOT.name,'version':(ROOT/'VERSION').read_text().strip() if (ROOT/'VERSION').exists() else '1.0.0','files':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}}
 out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_name(out.name+'.tmp')
 try:
  if case:
   if not str(out).endswith('.tgz'):raise ValueError('Case packages use .tgz')
   with tarfile.open(tmp,'w:gz') as t:
    for name,p in files.items():t.add(p,arcname=name,recursive=False)
    data=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('MANIFEST.json');info.size=len(data);info.mode=0o644;t.addfile(info,io.BytesIO(data))
  else:
   if out.suffix!='.zip':raise ValueError('Skill-only packages use .zip')
   with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
    for name,p in files.items():z.write(p,ROOT.name+'/'+name[len('Skill/'):])
    z.writestr(ROOT.name+'/PACKAGE-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
  tmp.replace(out)
 finally:tmp.unlink(missing_ok=True)
 return {'file':str(out),'files':len(files),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'modelCalls':0}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--case',type=Path);a=p.parse_args();print(json.dumps(package(a.out,a.case),indent=2))
if __name__=='__main__':main()
