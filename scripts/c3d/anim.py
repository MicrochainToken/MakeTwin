"""Animation presets. Each call adds one named clip (an NLA track) that the exporter turns
into a glTF animation with the same name. Several calls with the same clip name combine
into one clip (e.g. press the power button AND light the LED in "power_on").

All clips start at frame 0 from the rest pose (closed / off / assembled).
"""
import math

import bpy
from mathutils import Vector

from . import core
from .joints import set_value

# Named easing curves for motion between two keys. Real products accelerate and slow down;
# linear motion looks robotic. "settle" overshoots slightly (about 10%) and comes back, which
# suits lids, doors and snapping clips that have room to swing past their stop.
EASES = {
    "linear": ("LINEAR", None),
    "in_out": ("SINE", "EASE_IN_OUT"),   # default: gentle start and stop
    "smooth": ("CUBIC", "EASE_IN_OUT"),  # stronger acceleration, long soft landing
    "out": ("CUBIC", "EASE_OUT"),        # quick start, soft stop (drop into place, release)
    "in": ("CUBIC", "EASE_IN"),          # soft start, firm stop (push until it latches)
    "settle": ("BACK", "EASE_OUT"),      # small overshoot then settle (lids, clips, doors)
}
DEFAULT_EASE = "in_out"


def _apply_ease(key, ease):
    if ease not in EASES:
        raise ValueError(f"Unknown ease {ease!r}; use one of {sorted(EASES)}")
    interpolation, easing = EASES[ease]
    key.interpolation = interpolation
    if easing:
        key.easing = easing
    if interpolation == "BACK":
        key.back = 1.2


def fps():
    return bpy.context.scene.render.fps / bpy.context.scene.render.fps_base


def curves(action):
    """F-curves for both legacy actions and Blender's slotted actions."""
    if hasattr(action, "fcurves"):
        yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    yield from bag.fcurves


def sample_frames(clip, start, end, intervals=12, neighbors=True):
    """Uniform samples plus authored phase boundaries and interval midpoints.

    This is a sampling aid, not continuous collision detection. Supports scaled NLA
    strips; manually repeated/reversed strips still require additional review.
    """
    if intervals < 1:
        raise ValueError("intervals must be positive")
    boundaries = {float(start), float(end)}
    for obj in bpy.context.scene.objects:
        if not obj.animation_data:
            continue
        for track in obj.animation_data.nla_tracks:
            if track.name != clip:
                continue
            for strip in track.strips:
                if not strip.action:
                    continue
                for fc in curves(strip.action):
                    for key in fc.keyframe_points:
                        f = strip.frame_start + (key.co.x - strip.action_frame_start) * strip.scale
                        if start <= f <= end:
                            boundaries.add(float(f))
    import json
    rate = fps()
    for guide in json.loads(bpy.context.scene.get("c3d_guides", "[]")):
        if guide["clip"] == clip:
            for step in guide["steps"]:
                for k in ("startSeconds", "motionStartSeconds", "actionEndSeconds", "endSeconds"):
                    f = step.get(k, step["startSeconds"]) * rate
                    boundaries.update(x for x in ((f-.25, f, f+.25) if neighbors else (f,)) if start <= x <= end)
    ordered = sorted(boundaries)
    frames = boundaries | {(a + b) / 2 for a, b in zip(ordered, ordered[1:])}
    frames.update(start + (end - start) * k / intervals for k in range(intervals + 1))
    return sorted(frames)


def _clip(obj, clip, keys, path, index=None, eases=None):
    """keys: [(frame, value)]; path: 'rotation_euler' | 'location' | 'scale'.

    eases: one easing name per key, applied to the motion ARRIVING at that key (the first
    entry is ignored). A single name applies to every segment. Default: linear (holds,
    glows and spins); joint helpers pass DEFAULT_EASE.
    """
    if not clip or len(keys) < 2 or keys[0][0] != 0:
        raise ValueError("Clips need a name and at least two keys starting at frame 0")
    if any(not math.isfinite(f) or f < 0 for f, _ in keys) or any(
            b[0] <= a[0] for a, b in zip(keys, keys[1:])):
        raise ValueError("Clip frames must be finite and strictly increasing")
    ad = obj.animation_data or obj.animation_data_create()
    if any(t.name == clip for t in ad.nla_tracks):
        raise ValueError(f"{obj.name} already has clip {clip!r}; combine its keys in one sequence")
    action = bpy.data.actions.new(f"{clip}__{obj.name}")
    ad.action = action
    for frame, value in keys:
        if index is None:
            setattr(obj, path, value)
            obj.keyframe_insert(data_path=path, frame=frame)
        else:
            vec = list(getattr(obj, path))
            vec[index] = value
            setattr(obj, path, vec)
            obj.keyframe_insert(data_path=path, index=index, frame=frame)
    ad.action = None
    if eases is None or isinstance(eases, str):
        eases = [eases or "linear"] * len(keys)
    if len(eases) != len(keys):
        raise ValueError("eases needs one entry per key")
    for fc in curves(action):
        points = sorted(fc.keyframe_points, key=lambda k: k.co.x)
        for i, key in enumerate(points):
            # Blender stores interpolation on the key that STARTS a segment.
            _apply_ease(key, eases[i + 1] if i + 1 < len(eases) else "linear")
    track = next((t for t in ad.nla_tracks if t.name == clip), None) or ad.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, int(keys[0][0]), action)
    strip.extrapolation = "HOLD_FORWARD"
    return action


def _joint_keys(joint, clip, values_by_frame, eases=DEFAULT_EASE):
    if joint["c3d_joint"] in ("hinge", "knob"):
        keys = [(f, math.radians(v)) for f, v in values_by_frame]
        _clip(joint, clip, keys, "rotation_euler", index=2, eases=eases)
    else:
        _clip(joint, clip, values_by_frame, "location", index=2, eases=eases)
    set_value(joint, 0)


def open_close(joint, clip=None, seconds=1.2, to=None, ease=DEFAULT_EASE):
    """Move a hinge/slider from rest to its open limit (play reversed to close)."""
    clip = clip or f"open_{joint.name}"
    to = joint["c3d_limits"][1] if to is None else to
    _joint_keys(joint, clip, [(0, 0), (round(seconds * fps()), to)], ease)
    return clip


def press(joint, clip=None, seconds=0.35):
    """Button goes in firmly and springs back softly."""
    clip = clip or f"press_{joint.name}"
    travel = joint["c3d_limits"][1]
    n = max(3, round(seconds * fps()))
    _joint_keys(joint, clip, [(0, 0), (n // 3, travel), (n, 0)], ["linear", "in", "out"])
    return clip


def turn(joint, clip=None, seconds=1.0, degrees=None, loops=1, ease=None):
    """Rotate a knob/turntable/fan. loops > 1 repeats full turns (for spinning parts).

    Default ease: in_out for a single turn of a knob, linear for continuous spinning.
    """
    clip = clip or f"turn_{joint.name}"
    deg = joint["c3d_limits"][1] if degrees is None else degrees
    ease = ease or ("linear" if loops > 1 else DEFAULT_EASE)
    _joint_keys(joint, clip, [(0, 0), (round(seconds * fps() * loops), deg * loops)], ease)
    return clip


def glow_part(name, light_part, material, pad=None):
    """An emissive cap just in front of an indicator/screen that `power` switches on.

    It is a copy of `light_part` grown by `pad` (default core.gap()) so it never shares a
    plane with the lens. Hidden (scaled to ~0) at rest.
    """
    pad = core.gap() if pad is None else pad
    glow = light_part.copy()
    glow.data = light_part.data.copy()
    core.link(glow)
    lo, hi = core.bbox_world(light_part)
    size = hi - lo
    factor = [1 + 2 * pad / max(s, 1e-6) for s in size]
    core.part(glow, name, material=material)
    glow.scale = Vector([glow.scale[i] * factor[i] for i in range(3)])
    core.set_parent(glow, light_part)
    glow["c3d_glow"] = True
    glow["c3d_rest_scale"] = list(glow.scale)
    glow.scale = (1e-4, 1e-4, 1e-4)
    return glow


def power(glows, clip="power_on", seconds=0.5, buttons=()):
    """Switch indicator/screen glows on (and press the given buttons first)."""
    delay = 0
    for b in buttons:
        press(b, clip)
        delay = round(0.2 * fps())
    for g in glows:
        full = tuple(g["c3d_rest_scale"])
        keys = [(0, (1e-4,) * 3)]
        if delay:
            keys.append((delay, (1e-4,) * 3))
        keys += [(delay + 2, full), (delay + max(3, round(seconds * fps())), full)]
        _clip(g, clip, keys, "scale")
        g.scale = (1e-4, 1e-4, 1e-4)
    return clip


def explode(clip="explode", objects=None, distance=0.35, seconds=1.5, ease="smooth"):
    """Move every top-level assembly away from the product centre (assembly overview).

    distance is a fraction of the product size.
    """
    lo, hi = core.product_bbox()
    center = (lo + hi) / 2
    size = max(hi - lo)
    if objects is None:
        objects = [o for o in bpy.context.scene.objects if o.parent is None
                   and (o.get("c3d_part") or o.name.endswith("_frame"))]
    end = round(seconds * fps())
    for o in objects:
        if o.type == "MESH":
            olo, ohi = core.bbox_world(o)
            c = (olo + ohi) / 2
        else:
            c = o.matrix_world.translation
        d = c - center
        if d.length < 1e-6:
            continue
        rest = Vector(o.location)
        offset = d.normalized() * size * distance
        _clip(o, clip, [(0, rest.copy()), (end, rest + offset)], "location", eases=ease)
        o.location = rest
    return clip


def sequence(clip, steps, ease=DEFAULT_EASE):
    """Author several joints in one clip using absolute (seconds, value[, ease]) keys.

    steps = [(joint, [(0, 0), (0.5, 90, "settle"), (1.5, 90)]), ...].
    Each joint starts at rest. Shorter tracks hold their last value to the common end.
    Degrees for hinges/knobs, metres for sliders. A key's optional third item names the
    easing of the motion arriving at it (see EASES); otherwise `ease` is used.
    """
    steps = list(steps)
    if not steps or len({j.name for j, _ in steps}) != len(steps):
        raise ValueError("A sequence needs distinct joints")
    prepared = []
    for joint, raw in steps:
        raw = [tuple(k) for k in raw]
        if any(len(k) not in (2, 3) for k in raw):
            raise ValueError("Sequence keys are (seconds, value) or (seconds, value, ease)")
        keys = [k[:2] for k in raw]
        eases = [k[2] if len(k) == 3 else ease for k in raw]
        for e in eases:
            if e not in EASES:
                raise ValueError(f"Unknown ease {e!r}; use one of {sorted(EASES)}")
        if len(keys) < 2 or keys[0] != (0, 0):
            raise ValueError("Every joint sequence must start with (0, 0)")
        if any(not math.isfinite(t) or not math.isfinite(v) or t < 0 for t, v in keys):
            raise ValueError("Sequence times and values must be finite and times nonnegative")
        frames = [(round(t * fps()), v) for t, v in keys]
        if any(b[0] <= a[0] for a, b in zip(frames, frames[1:])):
            raise ValueError("Sequence times must increase by at least one frame")
        if any(t.name == clip for t in (joint.animation_data.nla_tracks if joint.animation_data else [])):
            raise ValueError(f"{joint.name} already has clip {clip!r}")
        if not joint.get("c3d_joint"):
            raise ValueError("Sequences accept c3d joints only")
        prepared.append((joint, frames, eases))
    end = max(keys[-1][0] for _, keys, _ in prepared)
    for joint, keys, eases in prepared:
        if keys[-1][0] < end:
            keys.append((end, keys[-1][1]))
            eases.append("linear")
        _joint_keys(joint, clip, keys, eases)
    return clip


def guide(clip='how_to_use', title='How to use', initial_state='assembled_off', initial=None):
    """Return a stateful Guide; .step(...).step(...).finish() writes one clip."""
    from .guide import Guide
    return Guide(clip, title, initial_state, initial)


def camera_clip(clip, camera, lead=None):
    """Finalize an independent clip with a stationary camera lead-in. Call after all
    channels of this clip have been authored; never apply to a continuous guide.
    Physical motion duration is preserved. Camera angles use glTF Y-up coordinates.
    """
    import json
    from guide_schema import validate_camera
    scene = bpy.context.scene
    validate_camera(camera, {o.get('c3d_part') for o in core.parts()})
    records = json.loads(scene.get('c3d_clip_cameras', '{}'))
    if clip in records or any(g['clip'] == clip for g in json.loads(scene.get('c3d_guides', '[]'))):
        raise ValueError('Camera clip already finalized or belongs to a guide')
    lead = camera.get('transitionSeconds', .8) if lead is None else lead
    if isinstance(lead, bool) or not isinstance(lead, (int,float)) or not math.isfinite(lead) or lead < camera.get('transitionSeconds', .8):
        raise ValueError('Lead must be finite and at least the camera transition')
    shift = math.ceil(lead * fps() - 1e-8)
    strips = [s for o in scene.objects if o.animation_data for t in o.animation_data.nla_tracks
              if t.name == clip for s in t.strips]
    if not strips or any(s.frame_start != 0 or s.scale != 1 or s.repeat != 1 for s in strips):
        raise ValueError('camera_clip requires unscaled clips starting at frame zero')
    end = max(s.frame_end for s in strips)
    for strip in strips:
        # Copy so another animation using the same action cannot be changed.
        strip.action = strip.action.copy()
        for fc in curves(strip.action):
            value = fc.evaluate(0)
            for key in fc.keyframe_points:
                key.co.x += shift
                key.handle_left.x += shift
                key.handle_right.x += shift
            if shift:
                fc.keyframe_points.insert(0, value).interpolation = 'LINEAR'
            if fc.keyframe_points[-1].co.x < end + shift:
                fc.keyframe_points.insert(end + shift, fc.keyframe_points[-1].co.y).interpolation = 'LINEAR'
            fc.update()
        strip.action_frame_start = 0
        strip.action_frame_end = end + shift
        strip.frame_start = 0
        strip.frame_end = end + shift
    records[clip] = dict(camera=dict(camera), motionStartSeconds=shift/fps(),
                         actionEndSeconds=(end+shift)/fps(), endSeconds=(end+shift)/fps())
    scene['c3d_clip_cameras'] = json.dumps(records)
    return clip
