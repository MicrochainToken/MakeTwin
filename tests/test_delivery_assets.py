import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from delivery_files import copy_asset
class DeliveryAssetTests(unittest.TestCase):
 def test_repeated_copy_from_frozen_template_stays_writable(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);source=p/'source.js';source.write_text('one');source.chmod(0o444);dest=p/'output.js'
   copy_asset(source,dest);dest.chmod(0o444);source.chmod(0o644);source.write_text('two');source.chmod(0o444)
   copy_asset(source,dest);self.assertEqual(dest.read_text(),'two');self.assertTrue(dest.stat().st_mode&0o200)
 def test_asset_copy_refuses_symlink(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'source').write_text('safe');(p/'other').write_text('keep');(p/'target').symlink_to(p/'other')
   with self.assertRaises(ValueError):copy_asset(p/'source',p/'target')
   self.assertEqual((p/'other').read_text(),'keep')
