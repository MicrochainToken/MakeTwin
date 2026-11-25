"""Inspect a real baked-transform GLB, not just its Blender action keys."""
import json,os,struct,unittest
from pathlib import Path


class MechanismExportTests(unittest.TestCase):
    def test_baked_attachment_translation_and_quaternion_survive_export(self):
        folder=os.environ.get('C3D_EXPORT_FIXTURE')
        if not folder:self.skipTest('Run tests/run_tests.sh for the real Blender export fixture')
        raw=(Path(folder)/'mechanism-baked.glb').read_bytes()
        size,kind=struct.unpack_from('<II',raw,12);self.assertEqual(kind,0x4e4f534a)
        doc=json.loads(raw[20:20+size]);offset=20+size
        binary_size,binary_kind=struct.unpack_from('<II',raw,offset);self.assertEqual(binary_kind,0x004e4942)
        binary=raw[offset+8:offset+8+binary_size]
        def values(index):
            a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
            self.assertEqual(a['componentType'],5126)
            width={'VEC3':3,'VEC4':4}[a['type']];start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',4*width)
            return [struct.unpack_from('<'+'f'*width,binary,start+i*stride) for i in range(a['count'])]
        animation=next(a for a in doc['animations'] if a['name']=='run_cycle')
        paths={}
        for channel in animation['channels']:
            if doc['nodes'][channel['target']['node']].get('name')=='mechanism_attachment':
                paths[channel['target']['path']]=values(animation['samplers'][channel['sampler']]['output'])
        self.assertIn('translation',paths);self.assertIn('rotation',paths)
        xs=[v[0] for v in paths['translation']];self.assertGreater(max(xs)-min(xs),.07)
        first,last=paths['rotation'][0],paths['rotation'][-1]
        self.assertLess(abs(sum(a*b for a,b in zip(first,last))),.3)
