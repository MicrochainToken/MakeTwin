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
