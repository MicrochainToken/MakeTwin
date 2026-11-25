"""Inspect sampled animation values in a real Blender-exported GLB."""
import json
import math
import os
import struct
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("C3D_EXPORT_FIXTURE"), "Set C3D_EXPORT_FIXTURE from run_tests.sh")
class MotionExportTests(unittest.TestCase):
    def setUp(self):
        raw = (Path(os.environ["C3D_EXPORT_FIXTURE"]) / "mini-oven.glb").read_bytes()
        size, kind = struct.unpack_from("<II", raw, 12)
        self.doc = json.loads(raw[20:20 + size])
        bin_size, bin_kind = struct.unpack_from("<II", raw, 20 + size)
        self.assertEqual(bin_kind, 0x004e4942)
        self.data = raw[28 + size:28 + size + bin_size]

    def values(self, index):
        accessor = self.doc["accessors"][index]
        self.assertEqual(accessor["componentType"], 5126)
        width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[accessor["type"]]
        view = self.doc["bufferViews"][accessor["bufferView"]]
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", width * 4)
        return [struct.unpack_from("<" + "f" * width, self.data, start + i * stride)
                for i in range(accessor["count"])]

    def channel(self, clip, node, path):
        animation = next(a for a in self.doc["animations"] if a["name"] == clip)
        channel = next(c for c in animation["channels"]
                       if self.doc["nodes"][c["target"]["node"]]["name"] == node
                       and c["target"]["path"] == path)
        sampler = animation["samplers"][channel["sampler"]]
        return [v[0] for v in self.values(sampler["input"])], self.values(sampler["output"])

    def test_exploded_door_holds_open_while_turntable_exits(self):
        times, poses = self.channel("explode", "door_hinge", "rotation")
        self.assertGreaterEqual(times[-1], 2.99)
        held = [pose for t, pose in zip(times, poses) if t >= 1.21]
        self.assertTrue(held)
        self.assertTrue(all(abs(sum(a * b for a, b in zip(p, poses[-1]))) > .99999 for p in held))
        # glTF quaternions are xyzw. A 105 degree hinge must not collapse to rest.
        self.assertAlmostEqual(abs(poses[-1][3]), math.cos(math.radians(105) / 2), places=4)

    def test_turntable_waits_then_translates_in_export(self):
        times, poses = self.channel("explode", "turntable_extract", "translation")
        self.assertLess(max(abs(v) for v in poses[0]), 1e-6)
        self.assertTrue(all(max(abs(v) for v in pose) < 1e-6
                            for t, pose in zip(times, poses) if t <= 1.19))
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in poses[-1])), .45, places=5)
        # The independent spinning clip must not inherit extraction from explode.
        anim = next(a for a in self.doc["animations"] if a["name"] == "turntable_spin")
        for channel in anim["channels"]:
            if (self.doc["nodes"][channel["target"]["node"]]["name"] == "turntable_extract"
                    and channel["target"]["path"] == "translation"):
                sampler = anim["samplers"][channel["sampler"]]
                self.assertTrue(all(max(abs(v) for v in pose) < 1e-6
                                    for pose in self.values(sampler["output"])))

    def test_guide_holds_door_then_closes_and_keeps_light_on(self):
        times, poses = self.channel("how_to_use", "door_hinge", "rotation")
        held = [p for t,p in zip(times,poses) if 1.6 <= t <= 2.9]
        self.assertTrue(held)
        self.assertTrue(all(abs(p[3]-poses[0][3]) > .2 for p in held))
        self.assertAlmostEqual(abs(poses[-1][3]), 1, places=5)
        times, scales = self.channel("how_to_use", "power_led_glow", "scale")
        self.assertGreater(max(scales[-1]), .5)
        manifest = json.loads((Path(os.environ["C3D_EXPORT_FIXTURE"]) / "mini-oven.manifest.json").read_text())
        guide = manifest["guides"][0]
        self.assertEqual(len(guide["steps"]), 5)
        self.assertTrue(guide["steps"][1]["pauseAfter"])

    def test_nonzero_guide_initial_does_not_contaminate_default_pose(self):
        node=next(n for n in self.doc["nodes"] if n["name"]=="door_hinge")
        self.assertAlmostEqual(abs(node.get("rotation", [0,0,0,1])[3]), 1, places=5)
        times,poses=self.channel("inspect_from_open","door_hinge","rotation")
        self.assertAlmostEqual(abs(poses[0][3]), math.cos(math.radians(105)/2), places=4)
        self.assertAlmostEqual(abs(poses[-1][3]), 1, places=5)


if __name__ == "__main__":
    unittest.main()
