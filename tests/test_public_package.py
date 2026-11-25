"""The public ZIP must retain viewer/media assets and exclude private run folders."""
import importlib.util,tempfile,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_showcase',SKILL/'scripts/package_showcase.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PublicPackageTests(unittest.TestCase):
 def test_viewer_images_and_future_demo_gif_are_retained(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name in ['SKILL.md','templates/viewer/index.html','templates/viewer/logo.png','docs/demo.gif','templates/viewer/THREE-LICENSE.txt']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'package asset fixture')
   names={p.relative_to(root).as_posix() for p in module.skill_files(root)}
   self.assertIn('templates/viewer/logo.png',names);self.assertIn('docs/demo.gif',names)
   self.assertIn('templates/viewer/THREE-LICENSE.txt',names)
 def test_private_run_inputs_and_operator_files_are_excluded(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   for name in ['SKILL.md','inputs/photos/private.png','ops/login.py','agent-home/config.json','.env','output/model.glb']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'private fixture')
   names={p.relative_to(root).as_posix() for p in module.skill_files(root)}
   self.assertEqual(names,{'SKILL.md'})

 def test_archive_has_version_preview_licenses_and_stable_root(self):
  import json, zipfile
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/'arbitrary-checkout-name'
   for name in ['SKILL.md','VERSION','templates/viewer/model.glb','templates/viewer/model.manifest.json','templates/viewer/explorer.json','templates/viewer/EARCUT-LICENSE.txt','templates/viewer/vendor-sources.json','secret-case/photo.png','examples/generic/model.glb']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('1.0.1' if name=='VERSION' else 'fixture')
   out=Path(folder)/'release.zip'
   with patch.object(module,'ROOT',root):module.package(out)
   with zipfile.ZipFile(out) as z:
    prefix='mechanical-explorer-test/'
    self.assertEqual(z.read(prefix+'VERSION'),b'1.0.1')
    for name in ['model.glb','model.manifest.json','explorer.json','EARCUT-LICENSE.txt','vendor-sources.json']:
     self.assertIn(prefix+'templates/viewer/'+name,z.namelist())
    self.assertFalse(any('secret-case' in n or n.endswith('examples/generic/model.glb') for n in z.namelist()))
    manifest=json.loads(z.read(prefix+'PACKAGE-MANIFEST.json'))
    self.assertEqual(manifest['version'],'1.0.1')
    for name in manifest['files']:self.assertIn(prefix+name,z.namelist())
