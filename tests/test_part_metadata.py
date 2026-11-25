import copy,importlib.util,os,unittest
from pathlib import Path
SKILL=Path(os.environ.get('C3D_SKILL_DIR',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('part_validator',SKILL/'scripts/validate_parts.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PartMetadataTests(unittest.TestCase):
 def setUp(self):
  self.manifest={'parts':[{'id':'tank'},{'id':'lid'}]}
  self.data={'schemaVersion':1,'units':'metres','coordinateSystem':'glTF-Y-up','assemblies':[{'id':'body','label':'Body','purpose':'Holds water'}],'parts':[dict(id=i,label=i,function='Contains water' if i=='tank' else 'Covers the tank',evidence='observed',evidenceNote='Reference diagram',assembly='body',parent=None if i=='tank' else 'tank',interfaces=[],motion={'kind':'unknown'}) for i in ['tank','lid']]}
 def test_complete_metadata_and_declared_unknown_motion(self):self.assertTrue(module.validate(self.manifest,self.data)['passed'])
 def test_unknown_or_missing_part_is_rejected(self):
  self.data['parts'][1]['id']='unexported';self.assertFalse(module.validate(self.manifest,self.data)['passed'])
 def test_parent_cycles_are_rejected(self):
  self.data['parts'][0]['parent']='lid';self.assertFalse(module.validate(self.manifest,self.data)['passed'])
 def test_supported_motion_requires_normalized_axis_and_units(self):
  m={'kind':'rotation','space':'parent','axis':[0,0,2],'pivot':[0,0,0],'range':[0,1],'unit':'radians','note':'Reference hinge'}
  self.data['parts'][1]['motion']=m;self.assertFalse(module.validate(self.manifest,self.data)['passed'])
  m['axis']=[0,0,1];self.assertTrue(module.validate(self.manifest,self.data)['passed'])
  m['unit']='metres';self.assertFalse(module.validate(self.manifest,self.data)['passed'])
 def test_invalid_interface_is_rejected(self):
  self.data['parts'][1]['interfaces']=[{'target':'missing','type':'fastens','evidence':'inferred'}];self.assertFalse(module.validate(self.manifest,self.data)['passed'])
