"""Inspect actual exported generic fixture GLB, never a mocked animation document."""
import json
import math
import os
from pathlib import Path
import struct
import unittest

@unittest.skipUnless(os.environ.get('C3D_CAMERA_FIXTURE'),'Set C3D_CAMERA_FIXTURE to the built generic fixture')
class CameraExportTests(unittest.TestCase):
    def setUp(self):
        self.folder=Path(os.environ['C3D_CAMERA_FIXTURE'])
        raw=(self.folder/'model.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0]
        self.doc=json.loads(raw[20:20+n]);self.data=raw[28+n:]
        self.manifest=json.loads((self.folder/'model.manifest.json').read_text())

    def values(self,index):
        a=self.doc['accessors'][index];self.assertEqual(a['componentType'],5126)
        width={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']];v=self.doc['bufferViews'][a['bufferView']]
        start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',width*4)
        return [struct.unpack_from('<'+'f'*width,self.data,start+i*stride) for i in range(a['count'])]

    def channel(self,clip,node,path):
        a=next(a for a in self.doc['animations'] if a['name']==clip)
        c=next(c for c in a['channels'] if self.doc['nodes'][c['target']['node']]['name']==node and c['target']['path']==path)
        s=a['samplers'][c['sampler']]
        return [v[0] for v in self.values(s['input'])],self.values(s['output'])

    def test_embedded_camera_metadata_matches_manifest(self):
        embedded=json.loads(self.doc['scenes'][self.doc.get('scene',0)]['extras']['c3d_camera_metadata'])
        self.assertEqual(embedded,{k:self.manifest[k] for k in ('schemaVersion','guides','clipCameras','cameraViews')})
        self.assertEqual({s['camera']['view'] for s in self.manifest['guides'][0]['steps']},{'rear','top','underside'})

    def test_independent_lead_in_holds_without_shortening_motion(self):
        for clip,node,path,duration in [('rear_open','rear_hinge','rotation',1.2),
            ('top_inspect','top_lift_joint','translation',1),('underside_press','underside_press_joint','translation',.6)]:
            with self.subTest(clip=clip):
                r=self.manifest['clipCameras'][clip];lead=r['motionStartSeconds']
                times,poses=self.channel(clip,node,path)
                self.assertAlmostEqual(times[-1]-lead,duration,places=5)
                for t,p in zip(times,poses):
                    if t<=lead+1e-6:
                        for a,b in zip(p,poses[0]):self.assertAlmostEqual(a,b,places=6)
                self.assertTrue(any(math.dist(p,poses[0])>.001 for t,p in zip(times,poses) if t>lead))
                self.assertGreaterEqual(lead+1e-6,r['camera']['transitionSeconds'])

    def test_guide_chapter_leads_hold_every_channel(self):
        g=next(g for g in self.manifest['guides'] if g['clip']=='how_to_use')
        for node,path in [('rear_hinge','rotation'),('top_lift_joint','translation'),('underside_press_joint','translation')]:
            times,poses=self.channel(g['clip'],node,path)
            for s in g['steps']:
                held=[p for t,p in zip(times,poses) if s['startSeconds']-1e-6<=t<=s['motionStartSeconds']+1e-6]
                self.assertTrue(held)
                self.assertTrue(all(math.dist(p,held[0])<1e-6 for p in held))
        self.assertAlmostEqual(g['steps'][0]['actionEndSeconds']-g['steps'][0]['motionStartSeconds'],1.2)

    def test_nonzero_initial_state_isolated_and_unmodified_initial_channel_held(self):
        for name in ['rear_hinge','top_lift_joint','underside_press_joint']:
            node=next(n for n in self.doc['nodes'] if n['name']==name)
            self.assertLess(math.dist(node.get('translation',[0,0,0]),[0,0,0]),1e-6)
            self.assertAlmostEqual(abs(node.get('rotation',[0,0,0,1])[3]),1,places=6)
        _,poses=self.channel('close_from_open','top_lift_joint','translation')
        self.assertTrue(all(abs(math.sqrt(sum(x*x for x in p))-.12)<1e-6 for p in poses))
        _,poses=self.channel('close_from_open','rear_hinge','rotation')
        self.assertAlmostEqual(abs(poses[0][3]),math.cos(math.radians(105)/2),places=5)
        # If exporter writes other joint channels into an independent clip, they stay at rest.
        for name in ['top_inspect','underside_press']:
            a=next(a for a in self.doc['animations'] if a['name']==name)
            for c in a['channels']:
                if self.doc['nodes'][c['target']['node']]['name']=='rear_hinge' and c['target']['path']=='rotation':
                    self.assertTrue(all(abs(abs(p[3])-1)<1e-6 for p in self.values(a['samplers'][c['sampler']]['output'])))

    def test_review_shots_include_directives_and_lead_boundaries(self):
        p=self.folder/'renders/render-manifest.json'
        if not p.exists():self.skipTest('render suite not generated yet')
        renders=json.loads(p.read_text());self.assertTrue(renders['complete'])
        shots=renders['cameraShots']['how_to_use']
        self.assertTrue(any(s['shot']['pitch']<-50 for s in shots))
        self.assertTrue(any(s['shot']['pitch']==15 for s in shots))
        g=next(g for g in self.manifest['guides'] if g['clip']=='how_to_use')
        times=[s['timeSeconds'] for s in shots]
        for step in g['steps']:
            for key in ('startSeconds','motionStartSeconds','actionEndSeconds','endSeconds'):
                self.assertTrue(any(abs(t-step[key])<1e-6 for t in times))
