import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'scripts'))
from guide_schema import validate_camera, validate_guides, validate_clip_cameras, CAMERA_ANGLES
from camera_math import shot_at, position_for, fit_distance

class CameraMetadataTests(unittest.TestCase):
    def guide(self):
        return dict(id='use',title='Use',initialState='rest',clip='use',steps=[dict(id='rear',
            instruction='Open rear',startSeconds=0,motionStartSeconds=.8,actionEndSeconds=2,endSeconds=3,
            evidence=[dict(source='fixture',locator='rear')],camera=dict(view='rear',parts=['hatch'],transitionSeconds=.8))])

    def test_valid_and_zero_lead_and_legacy(self):
        g=self.guide();self.assertEqual(validate_guides([g],{'use':3},{'hatch'}),[])
        s=g['steps'][0];s['motionStartSeconds']=0;s['camera']['transitionSeconds']=0
        self.assertEqual(validate_guides([g],{'use':3},{'hatch'}),[])
        del s['camera'];del s['motionStartSeconds']
        self.assertEqual(validate_guides([g],{'use':3},{'hatch'}),[])

    def test_missing_part_bad_view_and_unsupported_fields(self):
        for shot in [{'view':'upside'},{'parts':['unknown']},{'parts':'hatch'},{'padding':float('nan')},
                     {'padding':True},{'padding':.9},{'transitionSeconds':float('inf')},
                     {'transitionSeconds':-1},{'azimuth':181},{'elevation':90},{'minContext':0},{'zoom':2}]:
            with self.subTest(shot=shot),self.assertRaises(ValueError):validate_camera(shot,{'hatch'})

    def test_impossible_transition_and_nonfinite_timing(self):
        for value in [float('nan'),float('inf'),-.1,2,True,'1']:
            g=self.guide();g['steps'][0]['motionStartSeconds']=value
            self.assertTrue(validate_guides([g],{'use':3},{'hatch'}))
        g=self.guide();g['steps'][0]['camera']['transitionSeconds']=1
        self.assertTrue(validate_guides([g],{'use':3},{'hatch'}))

    def test_clip_camera_validates_duration_and_parts(self):
        record={'camera':{'view':'top','parts':['lid'],'transitionSeconds':.5},
                'motionStartSeconds':.5,'actionEndSeconds':2,'endSeconds':2}
        self.assertEqual(validate_clip_cameras({'lift':record},{'lift':2},{'lid'}),[])
        for key,value in [('motionStartSeconds',.2),('endSeconds',3),('actionEndSeconds',float('nan'))]:
            bad=copy.deepcopy(record);bad[key]=value
            self.assertTrue(validate_clip_cameras({'lift':bad},{'lift':2},{'lid'}))
        self.assertTrue(validate_clip_cameras({'lift':record},{'lift':2},{'body'}))
        self.assertTrue(validate_clip_cameras({'missing':record},{'lift':2},{'lid'}))

    def test_render_math_matches_shared_viewer_math(self):
        # Same moving bounds and timeline, compare complete shots plus camera positions.
        script="""
const m=require(process.argv[1]),views=require(process.argv[2]);
const overview={min:[-1,-1,-1],max:[1,1,1]};
const steps=JSON.parse(process.argv[3]);
const boundsAt=t=>({min:[t*.1-.2,-.1,-.1],max:[t*.1+.2,.1,.1]});
const out=JSON.parse(process.argv[4]).map(time=>{const shot=m.shotAt({steps,time,boundsAt,overview,views});return {shot,pose:m.positionFor(shot,35,.5,overview)};});
console.log(JSON.stringify(out));
"""
        steps=self.guide()['steps'];times=[0,.2,.4,.799,.8,1,1.5,2,2.9,3]
        result=subprocess.run(['node','-e',script,str(SKILL/'templates/viewer/camera-director.js'),
            str(SKILL/'templates/viewer/camera-views.json'),json.dumps(steps),json.dumps(times)],capture_output=True,text=True,check=True)
        overview={'min':[-1,-1,-1],'max':[1,1,1]}
        def bounds(t,parts=None):return {'min':[t*.1-.2,-.1,-.1],'max':[t*.1+.2,.1,.1]}
        for t,actual in zip(times,json.loads(result.stdout)):
            shot=shot_at(steps,t,bounds,overview);pose=position_for(shot,35,.5,overview)
            for key in ['radius','padding','yaw','pitch']:self.assertAlmostEqual(actual['shot'][key],shot[key],places=10)
            for key in ['target','position']:
                for a,b in zip(actual['pose'][key],pose[key]):self.assertAlmostEqual(a,b,places=10)

    def test_named_views_and_fit(self):
        self.assertEqual(CAMERA_ANGLES['rear'],[180,12]);self.assertLess(CAMERA_ANGLES['underside'][1],0)
        self.assertGreater(fit_distance(1,35,.5),fit_distance(1,35,2))
        for radius in [0,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):fit_distance(radius,35,1)
