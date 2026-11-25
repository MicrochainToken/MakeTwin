#!/usr/bin/env python3
"""Vendor the existing pinned Three.js viewer modules; no AI calls or npm install."""
import hashlib,json,re,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='https://cdn.jsdelivr.net/npm/three@0.169.0/'
ENTRY=['build/three.module.js','examples/jsm/loaders/GLTFLoader.js','examples/jsm/controls/OrbitControls.js','examples/jsm/environments/RoomEnvironment.js']
IMPORT=re.compile(r'''((?:from\s*|import\s*)["'])(\.[^"']+)(["'])''')
def main():
 folder=ROOT/'templates/viewer';queue=list(ENTRY);raw={}
 while queue:
  path=queue.pop(0)
  if path in raw:continue
  with urllib.request.urlopen(BASE+path,timeout=45) as r:text=r.read().decode('utf-8')
  raw[path]=text
  for match in IMPORT.finditer(text):
   target=urllib.parse.urljoin(BASE+path,match.group(2))
   if not target.startswith(BASE):raise ValueError('Unexpected module origin')
   dep=target[len(BASE):]
   if not dep.endswith('.js'):raise ValueError('Unexpected module extension')
   if dep not in raw:queue.append(dep)
  if len(raw)>30:raise ValueError('Unexpected dependency expansion')
 names={p:'vendor-'+p.replace('/','-') for p in raw}
 hashes={}
 for path,text in raw.items():
  def replace(m):
   dep=urllib.parse.urljoin(BASE+path,m.group(2))[len(BASE):]
   return m.group(1)+'./'+names[dep]+m.group(3)
  data=IMPORT.sub(replace,text).encode();(folder/names[path]).write_bytes(data);hashes[names[path]]=hashlib.sha256(data).hexdigest()
 with urllib.request.urlopen(BASE+'LICENSE',timeout=45) as r:license=r.read()
 (folder/'THREE-LICENSE.txt').write_bytes(license)
 imports={'three':'./'+names['build/three.module.js']}
 for path in ENTRY[1:]:imports['three/addons/'+path[len('examples/jsm/'):]]='./'+names[path]
 p=folder/'index.html';s=p.read_text();s=re.sub(r'<script type="importmap">.*?</script>','<script type="importmap">'+json.dumps({'imports':imports})+'</script>',s,count=1,flags=re.S);p.write_text(s)
 (folder/'vendor-sources.json').write_text(json.dumps({'package':'three@0.169.0','base':BASE,'rewrittenLocalModuleHashes':hashes,'license':'THREE-LICENSE.txt'},indent=2)+'\n')
 print(json.dumps({'vendoredModules':len(raw),'networkRequiredByViewer':False}))
if __name__=='__main__':main()
