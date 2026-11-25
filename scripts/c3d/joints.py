"""Joints: the pivot a moving part hangs from.

Each joint is two empties:
  <name>_frame  fixed; sits at the pivot, its local Z points along the motion axis
  <name>        moves; rotates about / slides along its local Z. Parts are parented here.
Rest value 0 is always the closed / off / assembled state.
"""
import math

import bpy
from mathutils import Matrix, Vector

from . import core
from .shapes import _vec


def _make(name, kind, pivot, axis, limits, parts, parent=None):
    axis = _vec(axis)
    frame = core.link(bpy.data.objects.new(name + "_frame", None))
    frame.empty_display_type = "ARROWS"
    frame.empty_display_size = 0.02
    rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    frame.matrix_world = Matrix.Translation(Vector(pivot)) @ rot
    joint = core.link(bpy.data.objects.new(name, None))
    joint.empty_display_type = "SINGLE_ARROW"
    joint.empty_display_size = 0.03
    joint.parent = frame
    joint.matrix_parent_inverse = Matrix.Identity(4)
    joint.matrix_basis = Matrix.Identity(4)
    joint.rotation_mode = "XYZ"
    joint["c3d_joint"] = kind
    joint["c3d_frame"] = frame.name
    joint["c3d_axis"] = list(axis)
    joint["c3d_limits"] = list(limits)
    joint["c3d_parts"] = [p.name for p in parts]
    bpy.context.view_layer.update()
    if parent is None:
        parents = {p.parent for p in parts}
        parent = parents.pop() if len(parents) == 1 else None
    if parent is not None:
        core.set_parent(frame, parent)
    for p in parts:
        core.set_parent(p, joint)
    return joint


def frame(joint):
    """Return the fixed frame: carry this when nesting or attaching a whole joint.

    The returned joint itself is the animated handle, not the assembly root.
    Reparenting that handle disconnects it from its pivot and axis frame.
    """
    root = bpy.context.scene.objects.get(joint.get("c3d_frame", ""))
    if root is None:
        root = bpy.context.scene.objects.get(joint.name + "_frame")
    if root is None or joint.parent != root or root.get("c3d_joint"):
        raise ValueError(f"{joint.name} has no intact fixed joint frame")
    return root


def hinge(parts, pivot, axis, limits_deg=(0, 90), name=None):
    """Rotation about a hinge line through `pivot` along `axis` (right-hand rule).

    Example: a door hinged on its left edge that swings towards the viewer (-Y) uses
    axis "-Z" with the pivot on the left edge line.
    """
    parts = parts if isinstance(parts, (list, tuple)) else [parts]
    return _make(name or parts[0].name + "_hinge", "hinge", pivot, axis, limits_deg, parts)


def knob(parts, axis, center=None, limits_deg=(0, 300), name=None):
    """Rotation about the part's own centre line (dials, knobs, turntables, fans)."""
    parts = parts if isinstance(parts, (list, tuple)) else [parts]
    if center is None:
        lo, hi = core.bbox_world(parts[0])
        center = (lo + hi) / 2
    return _make(name or parts[0].name + "_knob", "knob", center, axis, limits_deg, parts)


def slider(parts, axis, limits=(0, 0.1), origin=None, name=None):
    """Straight motion along `axis` (drawers, trays, telescopic handles, filters)."""
    parts = parts if isinstance(parts, (list, tuple)) else [parts]
    if origin is None:
        lo, hi = core.bbox_world(parts[0])
        origin = (lo + hi) / 2
    return _make(name or parts[0].name + "_slide", "slider", origin, axis, limits, parts)


def button(parts, press_axis, travel=0.002, name=None):
    """Push button; press_axis points INTO the product. Leave clearance around it (a hole)."""
    parts = parts if isinstance(parts, (list, tuple)) else [parts]
    return slider(parts, press_axis, (0, travel), name=name or parts[0].name + "_press")


def set_value(joint, value):
    """Pose a joint: degrees for hinge/knob, metres for slider."""
    if joint["c3d_joint"] in ("hinge", "knob"):
        joint.rotation_euler = (0, 0, math.radians(value))
    else:
        joint.location = (0, 0, value)


def joints():
    return [o for o in bpy.context.scene.objects if o.get("c3d_joint")]
