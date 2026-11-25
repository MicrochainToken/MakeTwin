"""Deterministic Blender tests for staged motion, contacts and material parameters.

Run with scripts/blender.sh -b --python tests/motion_regression.py.
Checker subprocesses use this same Blender binary; no agent or API calls.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import math
import bpy
from mathutils import Vector

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from c3d import anim, core, joints, materials, shapes


class MotionRegression(unittest.TestCase):
    def setUp(self):
        core.reset_scene(product_size=(.4, .4, .5))

    def part(self, name, center=(0, 0, .1), size=(.04, .08, .08)):
        return core.part(shapes.box(name, size, center=center), name,
                         material=materials.get("abs_matte"))

    def check(self):
        with tempfile.TemporaryDirectory() as folder:
            blend = Path(folder) / "model.blend"
            report = Path(folder) / "checks.json"
            core.finish(blend)
            run = subprocess.run([bpy.app.binary_path, "--factory-startup", "-b", str(blend),
                                  "--python-exit-code", "1", "--python", str(SKILL / "scripts/check_model.py"),
                                  "--", "--report", str(report)], capture_output=True, text=True, timeout=60)
            self.assertTrue(report.exists(), run.stdout + run.stderr)
            doc = json.loads(report.read_text())
            self.assertEqual(run.returncode, int(doc["summary"]["errors"] > 0))
            return doc

    def setup_gate(self):
        gate = self.part("gate", size=(.04, .2, .2))
        mover = self.part("tray", center=(-.12, 0, .1))
        return (joints.slider(gate, "Z", limits=(0, .3)),
                joints.slider(mover, "X", limits=(0, .24)))

    def test_sequence_holds_gate_and_keeps_second_clip_independent(self):
        gate, tray = self.setup_gate()
        anim.sequence("remove_tray", [(gate, [(0, 0), (.5, .3)]),
                                      (tray, [(0, 0), (.5, 0), (1.5, .24)])])
        anim.open_close(gate, clip="open_gate", to=.1)
        for obj in bpy.context.scene.objects:
            if obj.animation_data:
                for track in obj.animation_data.nla_tracks:
                    track.mute = track.name != "remove_tray"
        bpy.context.scene.frame_set(30)
        self.assertAlmostEqual(gate.location.z, .3, places=6)
        self.assertAlmostEqual(tray.location.z, .12, places=6)
        report = self.check()
        self.assertFalse([f for f in report["findings"] if f["code"] == "motion_collision"])

    def test_wrong_order_reports_collision(self):
        gate, tray = self.setup_gate()
        anim.sequence("remove_tray", [(gate, [(0, 0), (1, 0), (2, .3)]),
                                      (tray, [(0, 0), (1, .24)])])
        self.assertTrue(any(f["code"] == "motion_collision" for f in self.check()["findings"]))

    def test_short_phase_in_long_explode_clip_is_checked(self):
        _, tray = self.setup_gate()
        anim.sequence("explode", [(tray, [(0, 0), (.1, 0), (.2, .24), (.3, 0), (10, 0)])])
        report = self.check()
        self.assertTrue(any(f["code"] == "motion_collision" for f in report["findings"]))
        self.assertTrue(report["motionSampling"]["includesExplode"])

    def test_rest_contact_does_not_mask_relative_motion(self):
        a = self.part("housing", size=(.1, .1, .1))
        b = self.part("insert", center=(.08, 0, .1), size=(.1, .06, .06))
        core.allow_contact(a, b, "seated insert at rest")
        anim.open_close(joints.slider(b, "-X", limits=(0, .16)), clip="slide")
        self.assertTrue(any(f["code"] == "motion_collision" for f in self.check()["findings"]))

    def test_rigid_contact_moves_together_without_motion_error(self):
        a = self.part("housing", size=(.1, .1, .1))
        b = self.part("handle", center=(.08, 0, .1), size=(.1, .06, .06))
        core.set_parent(b, a)
        core.allow_contact(a, b, "fixed handle ends")
        anim.open_close(joints.slider(a, "X", limits=(0, .2)), clip="slide")
        self.assertFalse(any(f["code"] == "motion_collision" for f in self.check()["findings"]))

    def test_scoped_sliding_contact_keeps_coplanar_check(self):
        a = self.part("housing", size=(.1, .1, .1))
        b = self.part("insert", center=(.08, 0, .1), size=(.1, .1, .1))
        core.allow_contact(a, b, "simplified shaft/bearing fit", motion_clips=["slide"])
        anim.open_close(joints.slider(b, "-X", limits=(0, .16)), clip="slide")
        report = self.check()
        self.assertFalse(any(f["code"] == "motion_collision" for f in report["findings"]))
        self.assertTrue(any(f["code"] == "zfight" for f in report["findings"]))

    def test_invalid_contact_is_reported(self):
        a = self.part("housing")
        core.allow_contact(a, "absent_part", "typo in part id")
        self.assertTrue(any(f["code"] == "contact" for f in self.check()["findings"]))

    def _value_at(self, joint, frame):
        fc = next(iter(anim.curves(joint.animation_data.nla_tracks[0].strips[0].action)))
        return fc.evaluate(frame)

    def test_scene_fps_and_default_easing(self):
        bpy.context.scene.render.fps = 24
        joint = joints.slider(self.part("tray"), "X", limits=(0, .2))
        anim.open_close(joint, seconds=1)
        strip = joint.animation_data.nla_tracks[0].strips[0]
        self.assertAlmostEqual(strip.frame_end, 24)
        # Default in_out (sine): a quarter of the way in time is ~15% of the travel, not 25%.
        self.assertAlmostEqual(self._value_at(joint, 6), .2 * (1 - math.cos(math.pi * .25)) / 2, places=3)
        self.assertAlmostEqual(self._value_at(joint, 12), .1, places=3)
        self.assertAlmostEqual(self._value_at(joint, 24), .2, places=5)

    def test_linear_ease_is_still_available(self):
        bpy.context.scene.render.fps = 24
        joint = joints.slider(self.part("tray"), "X", limits=(0, .2))
        anim.open_close(joint, seconds=1, ease="linear")
        self.assertAlmostEqual(self._value_at(joint, 6), .05, places=4)

    def test_sequence_per_key_ease_and_holds(self):
        bpy.context.scene.render.fps = 24
        joint = joints.slider(self.part("tray"), "X", limits=(0, .2))
        anim.sequence("move", [(joint, [(0, 0), (1, .2, "settle"), (2, .2), (3, 0, "linear")])])
        self.assertGreater(self._value_at(joint, 18), .2)          # settle overshoots before settling
        self.assertAlmostEqual(self._value_at(joint, 24), .2, places=5)
        self.assertAlmostEqual(self._value_at(joint, 36), .2, places=5)  # hold stays put
        self.assertAlmostEqual(self._value_at(joint, 60), .1, places=4)  # linear return, halfway
        with self.assertRaises(ValueError):
            anim.sequence("bad", [(joints.slider(self.part("t2"), "X", limits=(0, .1)), [(0, 0), (1, .1, "wobble")])])

    def test_guide_step_ease(self):
        bpy.context.scene.render.fps = 24
        joint = joints.slider(self.part("tray"), "X", limits=(0, .2))
        g = anim.guide(clip="g", title="G")
        g.step("a", "Slide out.", {joint: .2}, seconds=1, hold=0, ease="out", evidence=[{"source": "manual.pdf", "locator": "p. 1"}])
        g.step("b", "Slide in.", {joint: 0}, seconds=1, hold=0, ease="linear", evidence=[{"source": "manual.pdf", "locator": "p. 1"}])
        g.finish()
        # cubic ease-out is ahead of linear early in the move; the linear return is exact.
        self.assertGreater(self._value_at(joint, 6), .05 * 1.5)
        self.assertAlmostEqual(self._value_at(joint, 36), .1, places=4)

    def test_nested_joint_frames_preserve_rest_and_independent_axes(self):
        panel = self.part("panel", center=(.2, .1, .3))
        bpy.context.view_layer.update()
        original = panel.matrix_world.translation.copy()
        hinge = joints.hinge(panel, pivot=(.1, .1, .3), axis="Z", name="hinge")
        lift = joints.slider(joints.frame(hinge), "Z", origin=(.1, .1, .3), name="lift")
        park = joints.slider(joints.frame(lift), "X", origin=(.1, .1, .3), name="park")
        housing = self.part("housing", center=(0, 0, .1))
        core.set_parent(joints.frame(park), housing)
        bpy.context.view_layer.update()
        self.assertLess((panel.matrix_world.translation - original).length, 1e-6)

        joints.set_value(hinge, 90)
        joints.set_value(lift, .15)
        joints.set_value(park, .25)
        bpy.context.view_layer.update()
        self.assertLess((panel.matrix_world.translation - Vector((.35, .2, .45))).length, 1e-6)
        for joint in [hinge, lift, park]:
            joints.set_value(joint, 0)
        bpy.context.view_layer.update()
        self.assertLess((panel.matrix_world.translation - original).length, 1e-6)

    def test_detached_joint_frame_is_rejected(self):
        joint = joints.hinge(self.part("panel"), (0, 0, .1), "X")
        core.set_parent(joint, self.part("housing", center=(.2, 0, .1)))
        with self.assertRaises(ValueError):
            joints.frame(joint)
        self.assertTrue(any(f["code"] == "joint_hierarchy" for f in self.check()["findings"]))

    def test_invalid_sequences_fail_before_authoring(self):
        joint = joints.slider(self.part("tray"), "X")
        for keys in [[(0, .1), (1, .2)], [(0, 0), (1, .1), (.5, .2)],
                     [(0, 0), (.001, .1)], [(0, 0), (1, float("nan"))]]:
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                anim.sequence("bad", [(joint, keys)])
        self.assertIsNone(joint.animation_data)

    def test_material_overrides_have_distinct_cached_values(self):
        dark = materials.get("acrylic_smoked", alpha=.85, roughness=.18)
        clear = materials.get("acrylic_smoked", alpha=.2, roughness=.05)
        self.assertNotEqual(dark, clear)
        self.assertEqual(dark, materials.get("acrylic_smoked", alpha=.85, roughness=.18))
        self.assertAlmostEqual(dark.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value, .85)
        materials.get("abs_matte", name="explicit", roughness=.2)
        with self.assertRaises(ValueError):
            materials.get("abs_matte", name="explicit", roughness=.8)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(MotionRegression)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.stdout.flush()
sys.stderr.flush()
if not result.wasSuccessful():
    raise SystemExit(1)
