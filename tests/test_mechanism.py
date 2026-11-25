import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from c3d.mechanism import radial_state, slider_point


class LinkageTests(unittest.TestCase):
    def test_full_cycle_preserves_rods_axes_and_rigid_pin_ring(self):
        for k in range(361):
            s=radial_state(math.radians(k), .011, .045, .037, hub_radius=.008)
            c=s['crank_pin']
            for i,p in enumerate(s['cylinders']):
                a,b=p['big_end'],p['piston']
                self.assertAlmostEqual(math.dist(a,b),p['rod_length'],places=12)
                self.assertAlmostEqual(b[0]*math.sin(p['axis'])-b[1]*math.cos(p['axis']),0,places=12)
                if i:
                    self.assertAlmostEqual(math.dist(a,c),.008,places=12)
                    beta=2*math.pi*i/7
                    self.assertAlmostEqual((a[0]-c[0])*math.cos(s['master_angle'])+(a[1]-c[1])*math.sin(s['master_angle']),.008*math.cos(beta),places=12)
    def test_cycle_closes_and_master_stroke_matches_crank(self):
        start=radial_state(0,.011,.045,.037,hub_radius=.008)
        end=radial_state(2*math.pi,.011,.045,.037,hub_radius=.008)
        for a,b in zip(start['cylinders'],end['cylinders']):self.assertLess(math.dist(a['piston'],b['piston']),1e-12)
        opposite=radial_state(math.pi,.011,.045,.037,hub_radius=.008)
        self.assertAlmostEqual(math.dist(start['cylinders'][0]['piston'],opposite['cylinders'][0]['piston']),.022,places=12)
    def test_invalid_and_unreachable_inputs_fail(self):
        for pin,axis,length in [((0,2),0,1),((0,0),0,0),((math.nan,0),0,1)]:
            with self.assertRaises(ValueError):slider_point(pin,axis,length)
        for n in [0,2.5,True]:
            with self.assertRaises(ValueError):radial_state(0,.01,.04,.04,cylinders=n)
