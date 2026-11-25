"""Run inside Blender; exercise helpers used by photo-based product builds."""
import math
import sys
import unittest
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from c3d import core, shapes


class GeometryRegression(unittest.TestCase):
    def setUp(self):
        core.reset_scene(product_size=(1, 1, 1))

    def test_slab_dimensions_for_each_signed_axis(self):
        for axis in ['X', '-X', 'Y', '-Y', 'Z', '-Z']:
            with self.subTest(axis=axis):
                o = shapes.rounded_slab('panel', .24, .08, .006, .01,
                                        center=(.13, -.22, .35), axis=axis)
                bpy.context.view_layer.update()
                lo, hi = core.bbox_world(o)
                expected = {'X': (.006, .24, .08),
                            'Y': (.24, .006, .08),
                            'Z': (.24, .08, .006)}[axis[-1]]
                for actual, target in zip(hi - lo, expected):
                    self.assertAlmostEqual(actual, target, places=5)
                self.assertLess(((lo + hi) / 2 - Vector((.13, -.22, .35))).length, 1e-6)

    def test_slab_oblique_axis_has_requested_thickness(self):
        axis = Vector((1, 2, .3)).normalized()
        o = shapes.rounded_slab('panel', .24, .08, .006, .01, axis=axis)
        depths = [v.co.dot(axis) for v in o.data.vertices]
        self.assertAlmostEqual(max(depths) - min(depths), .006, places=5)

    def test_overlapping_cutters_leave_closed_expected_solid(self):
        body = shapes.box('body', (1, 1, 1))
        cutters = [shapes.box('cutter_a', (.4, .6, 1.4), center=(-.1, 0, 0)),
                   shapes.box('cutter_b', (.4, .6, 1.4), center=(.1, 0, 0))]
        shapes.cut_many(body, cutters)
        bm = bmesh.new()
        try:
            bm.from_mesh(body.data)
            self.assertTrue(all(e.is_manifold for e in bm.edges))
            self.assertAlmostEqual(abs(bm.calc_volume(signed=True)), .64, places=4)
        finally:
            bm.free()
        self.assertFalse(any(o.name.startswith('cutter') for o in bpy.context.scene.objects))

    def test_gap_uses_dimensions_saved_in_scene(self):
        # A fresh Blender invocation imports core with its default cache before opening a file.
        bpy.context.scene['c3d_product_size'] = [2, 1, 1]
        core._PRODUCT_SIZE[:] = [.5, .5, .5]
        self.assertAlmostEqual(core.gap(), .0016)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeometryRegression)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.stdout.flush()
sys.stderr.flush()
if not result.wasSuccessful():
    raise SystemExit(1)
