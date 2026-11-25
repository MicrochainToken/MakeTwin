"""Negative test: a scene with one known defect per check. check_model.py must report each.

  scripts/blender.sh -b --python tests/broken_scene.py -- --out broken.blend
  scripts/blender.sh -b broken.blend --python scripts/check_model.py -- --report broken.json
Expected codes: naming, material, zfight, overlap, motion_collision, faceted, inside_out, pivot_far
"""
import os
import sys

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
from c3d import anim, core, joints, materials, shapes  # noqa: E402

OUT = os.path.abspath(core.args().get("out", "broken.blend"))
core.reset_scene(product_size=(0.4, 0.3, 0.3))
m = materials.get("abs_matte")

base = core.part(shapes.box("base", (0.4, 0.3, 0.2), center=(0, 0, 0.1)), "base", material=m)
# zfight: a label plate whose front face lies exactly on the base's front face (y = -0.15)
core.part(shapes.box("label", (0.1, 0.01, 0.05), center=(0, -0.145, 0.1)), "label", material=m)
# overlap: a block sunk halfway into the top
core.part(shapes.box("block", (0.05, 0.05, 0.05), center=(0.1, 0.05, 0.2)), "block", material=m)
# material: a part without one
core.part(shapes.box("bare", (0.03, 0.03, 0.03), center=(-0.15, 0.1, 0.215)), "bare")
# faceted: a 10-sided cylinder, flat shaded
core.part(shapes.cylinder("can", 0.04, 0.06, center=(-0.1, -0.05, 0.231), segments=10), "can", material=m)
# inside_out: a box with flipped normals
inv = shapes.box("inverted", (0.03, 0.03, 0.03), center=(0.16, -0.1, 0.216))
inv.data.flip_normals()
core.part(inv, "inverted", material=m)
# motion_collision + pivot_far: a lid on top hinged about a pivot far below it, so it swings into the base
lid = core.part(shapes.box("lid", (0.2, 0.15, 0.01), center=(0, 0.0, 0.2 + core.gap() + 0.005)), "lid", material=m)
hinge = joints.hinge(lid, pivot=(0, 0, 0.05), axis="X", limits_deg=(0, 60), name="lid_hinge")
anim.open_close(hinge, clip="open_lid")
# naming: an unregistered default-named cube
shapes.box("Cube", (0.01, 0.01, 0.01), center=(0, 0.12, 0.205))  # _to_obj links it
core.finish(OUT)
