"""Scene setup, part registration and shared conventions.

Conventions: metres, Z up, product front faces -Y, product rests on Z = 0.
"""
import json
import math
import sys

import bpy
from mathutils import Vector

# Minimum separation between surfaces that must not share a plane. Use gap() for the
# product-scaled value; this is the floor for small products.
EPS_GAP = 0.0003

_PRODUCT_SIZE = [0.5, 0.5, 0.5]


def args():
    """Arguments after `--` on the Blender command line, as a dict of --key value pairs."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out, key = {}, None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
            out[key] = True
        elif key:
            out[key] = a
            key = None
    return out


def reset_scene(product_size=None, fps=30):
    """Empty the scene and set metric units. product_size=(W, D, H) in metres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = fps
    scene.frame_start = 0
    scene.frame_end = 1
    if product_size:
        set_product_size(*product_size)
    scene["c3d_allowed_contacts"] = "[]"
    return scene


def set_product_size(w, d, h):
    _PRODUCT_SIZE[:] = [w, d, h]
    bpy.context.scene["c3d_product_size"] = [w, d, h]


def gap():
    """Separation that stays visible and flicker-free at this product's scale."""
    size = bpy.context.scene.get("c3d_product_size", _PRODUCT_SIZE)
    return max(EPS_GAP, 0.0008 * max(size))


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def part(obj, pid, material=None, parent=None, label=None):
    """Register obj as product part `pid` (also its object and mesh name)."""
    obj.name = pid
    if obj.data is not None:
        obj.data.name = pid
    obj["c3d_part"] = pid
    obj["c3d_label"] = label or pid.replace("_", " ")
    if obj.type == "MESH":
        origin_to_center(obj)
    if material is not None:
        obj.data.materials.clear()
        obj.data.materials.append(material)
    if parent is not None:
        set_parent(obj, parent)
    return obj


def set_parent(child, parent):
    """Parent while keeping the child's world placement."""
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = world


def origin_to_center(obj):
    """Put the object's origin at its bounding-box centre without moving the geometry.

    Gives every glTF node a meaningful position (labels, explode, scaling all rely on it).
    """
    from mathutils import Matrix
    c = sum((Vector(v) for v in obj.bound_box), Vector()) / 8
    if c.length < 1e-12:
        return obj
    obj.data.transform(Matrix.Translation(-c))
    obj.matrix_world = obj.matrix_world @ Matrix.Translation(c)
    return obj


def allow_contact(a, b, reason, motion_clips=()):
    """Declare a fitted contact at rest; sliding contacts need explicit motion clip names.

    A rigid attachment keeps its exemption while moving as one assembly. This never
    suppresses the coplanar-face check.
    """
    if not isinstance(reason, str) or not reason.strip() or _name(a) == _name(b):
        raise ValueError("Contact needs two different parts and a nonempty reason")
    if isinstance(motion_clips, str) or any(not isinstance(c, str) or not c for c in motion_clips):
        raise ValueError("motion_clips must be a sequence of nonempty clip names")
    scene = bpy.context.scene
    items = json.loads(scene.get("c3d_allowed_contacts", "[]"))
    items.append({"a": _name(a), "b": _name(b), "reason": reason,
                  "motion_clips": list(motion_clips)})
    scene["c3d_allowed_contacts"] = json.dumps(items)


def allowed_contacts():
    items = json.loads(bpy.context.scene.get("c3d_allowed_contacts", "[]"))
    return {frozenset((i["a"], i["b"])) for i in items}


def _name(o):
    return o if isinstance(o, str) else o.name


def parts():
    return [o for o in bpy.context.scene.objects if o.get("c3d_part")]


def smooth(obj, angle_deg=35.0):
    """Smooth shading with sharp edges kept above angle_deg (auto-smooth)."""
    with bpy.context.temp_override(object=obj, active_object=obj,
                                   selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg), keep_sharp_edges=True)
    return obj


def flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def apply_modifiers(obj):
    """Bake all modifiers into the mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    mats = list(old.materials)
    obj.modifiers.clear()
    obj.data = new
    new.materials.clear()
    for m in mats:
        new.materials.append(m)
    new.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def bbox_world(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def product_bbox(objs=None):
    objs = objs or [o for o in parts() if o.type == "MESH" and not o.get("c3d_glow")]
    los, his = zip(*(bbox_world(o) for o in objs))
    lo = Vector([min(v[i] for v in los) for i in range(3)])
    hi = Vector([max(v[i] for v in his) for i in range(3)])
    return lo, hi


def finish(path):
    """Reset all joints to rest, set the frame range to the longest clip and save."""
    scene = bpy.context.scene
    end = 1
    for o in scene.objects:
        ad = o.animation_data
        if ad:
            for t in ad.nla_tracks:
                for s in t.strips:
                    end = max(end, int(s.frame_end))
    scene.frame_end = end
    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print(f"[c3d] saved {path} ({len(parts())} parts, frames 0-{end})")
