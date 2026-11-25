"""Boolean helper: fast MANIFOLD solver for closed solids, EXACT fallback otherwise, same result.

  blender.sh -b --python tests/boolean_solver.py
"""
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from c3d import core, shapes  # noqa: E402

used = []
_orig = shapes._apply_boolean


def _record(target, cutter, operation, solver):
    used.append(solver)
    return _orig(target, cutter, operation, solver)


shapes._apply_boolean = _record


def volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    v = bm.calc_volume(signed=False)
    bm.free()
    return v


def join(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


fail = []
core.reset_scene(product_size=(0.1, 0.1, 0.1))

# 1. closed solid minus closed solid: MANIFOLD only, removes the hole's volume
used.clear()
a = shapes.box("a", (0.04, 0.04, 0.02), (0, 0, 0.01))
shapes.boolean(a, shapes.cylinder("hole", 0.005, 0.03, (0, 0, 0.01), segments=32))
if used != ["MANIFOLD"]:
    fail.append(f"closed solids should use MANIFOLD only, used {used}")
expect = 0.04 * 0.04 * 0.02 - 3.14159 * 0.005 ** 2 * 0.02
if abs(volume(a) - expect) > expect * 0.01:
    fail.append(f"manifold cut volume {volume(a):.3e} != {expect:.3e}")

# 2. joined overlapping solids are not watertight: EXACT fallback, cut still happens
used.clear()
b = join([shapes.box("b1", (0.04, 0.04, 0.02), (0, 0, 0.01)), shapes.box("b2", (0.02, 0.06, 0.02), (0, 0, 0.01))])
nb = len(b.data.polygons)
shapes.boolean(b, shapes.cylinder("hole2", 0.004, 0.03, (0.012, 0, 0.01), segments=32))
if "EXACT" not in used:
    fail.append(f"non-watertight target should fall back to EXACT, used {used}")
if len(b.data.polygons) <= nb:
    fail.append("fallback cut did not change the mesh")

# 3. cutter that misses the target: MANIFOLD no-op is accepted, no retry
used.clear()
c = shapes.box("c", (0.02, 0.02, 0.02), (0, 0, 0.01))
shapes.boolean(c, shapes.box("far", (0.01, 0.01, 0.01), (0.2, 0.2, 0.2)))
if used != ["MANIFOLD"]:
    fail.append(f"non-overlapping cutter should not retry, used {used}")

# 4. no orphan meshes left behind by the retry path
orphans = [m.name for m in bpy.data.meshes if m.users == 0 and m.name != "b2"]  # b2: left by the test's own join
if orphans:
    fail.append(f"orphan meshes after booleans: {orphans}")


def mirrored(name):
    """Box at +X with an unapplied Mirror modifier: evaluates to two boxes (+X and -X)."""
    o = shapes.box(name, (0.02, 0.02, 0.02), (0.02, 0, 0.01))
    m = o.modifiers.new("mirror", "MIRROR")
    m.use_axis = (True, False, False)
    return o


# 5. unapplied modifier on the target: must not use MANIFOLD; result equals an EXACT-only cut
used.clear()
m1 = mirrored("m1")
shapes.boolean(m1, shapes.box("slot1", (0.06, 0.004, 0.03), (0, 0, 0.01)))
if "MANIFOLD" in used:
    fail.append(f"target with unapplied modifiers must use EXACT, used {used}")
ref = mirrored("m_ref")
_orig(ref, shapes.box("slot_ref", (0.06, 0.004, 0.03), (0, 0, 0.01)), "DIFFERENCE", "EXACT")
if abs(volume(m1) - volume(ref)) > volume(ref) * 0.01:
    fail.append(f"modifier case volume {volume(m1):.3e} != EXACT {volume(ref):.3e}")

# 6. unapplied modifier on the cutter (kept): EXACT, and the caller's cutter keeps its modifier
used.clear()
d = shapes.box("d", (0.08, 0.02, 0.02), (0, 0, 0.01))
mc = mirrored("mc")
shapes.boolean(d, mc, keep_cutter=True)
if "MANIFOLD" in used or len(mc.modifiers) != 1:
    fail.append(f"cutter with modifiers: used {used}, cutter modifiers {len(mc.modifiers)}")

# 7. Blender without the MANIFOLD solver (4.2-4.4): EXACT only, never assigns MANIFOLD
used.clear()
saved = shapes._manifold_solver_available
shapes._manifold_solver_available = lambda: False
e = shapes.box("e", (0.04, 0.04, 0.02), (0, 0, 0.01))
shapes.boolean(e, shapes.cylinder("hole_e", 0.005, 0.03, (0, 0, 0.01), segments=32))
shapes._manifold_solver_available = saved
if used != ["EXACT"]:
    fail.append(f"without MANIFOLD support only EXACT may run, used {used}")

for f in fail:
    print("[c3d] FAIL", f)
print("[c3d] boolean_solver", "FAILED" if fail else "ok")
sys.exit(1 if fail else 0)
