"""Deterministic planar linkage math, plus an optional Blender rigid-pose baker."""
import math


def slider_point(pin, axis_angle, rod_length):
    """Outward intersection of a radial slider axis with a fixed-length rod."""
    x, y = map(float, pin)
    if not all(math.isfinite(v) for v in (x, y, axis_angle, rod_length)) or rod_length <= 0:
        raise ValueError('Finite coordinates/angle and a positive rod length are required')
    u = (math.cos(axis_angle), math.sin(axis_angle))
    along = x*u[0] + y*u[1]
    across = x*u[1] - y*u[0]
    discriminant = rod_length*rod_length - across*across
    if discriminant < -1e-12 * rod_length*rod_length:
        raise ValueError('Unreachable slider pose; do not stretch the rod')
    distance = along + math.sqrt(max(0., discriminant))
    return (distance*u[0], distance*u[1])


def radial_state(theta, crank_radius, master_length, link_length, cylinders=7,
                 hub_radius=0., master_axis=0.):
    """Generic articulated radial mechanism; dimensions/topology need product evidence."""
    values = (theta, crank_radius, master_length, link_length, hub_radius, master_axis)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('All mechanism parameters must be finite')
    if isinstance(cylinders, bool) or not isinstance(cylinders, int) or cylinders < 1:
        raise ValueError('cylinders must be a positive integer')
    if crank_radius <= 0 or min(master_length, link_length) <= 0 or hub_radius < 0:
        raise ValueError('Positive crank/rod dimensions and non-negative hub radius required')
    c = (crank_radius*math.cos(theta), crank_radius*math.sin(theta))
    p0 = slider_point(c, master_axis, master_length)
    phi = math.atan2(p0[1]-c[1], p0[0]-c[0])
    result = []
    for i in range(cylinders):
        axis = master_axis + 2*math.pi*i/cylinders
        beta = 2*math.pi*i/cylinders
        big = c if i == 0 else (c[0]+hub_radius*math.cos(phi+beta),
                               c[1]+hub_radius*math.sin(phi+beta))
        length = master_length if i == 0 else link_length
        piston = p0 if i == 0 else slider_point(big, axis, length)
        result.append(dict(axis=axis, big_end=big, piston=piston, rod_length=length,
                           rod_angle=math.atan2(piston[1]-big[1], piston[0]-big[0])))
    return dict(crank_pin=c, master_angle=phi, cylinders=result)


def bake_transform(handle, clip, samples):
    """Bake (frame, local xyz, local quaternion wxyz) to one named NLA track."""
    import bpy
    from mathutils import Quaternion
    from .anim import curves
    samples = list(samples)
    if not clip or len(samples) < 2 or samples[0][0] != 0:
        raise ValueError('Need a clip and at least two samples starting at frame zero')
    previous_frame = -1
    for frame, position, quaternion in samples:
        if (not math.isfinite(frame) or frame <= previous_frame or len(position) != 3
                or len(quaternion) != 4 or not all(math.isfinite(v) for v in (*position, *quaternion))
                or sum(v*v for v in quaternion) < 1e-15):
            raise ValueError('Invalid rigid-pose samples')
        previous_frame = frame
    ad = handle.animation_data or handle.animation_data_create()
    if ad.action is not None or any(t.name == clip for t in ad.nla_tracks):
        raise ValueError('Handle already has an active action or this clip')
    rest = (handle.location.copy(), handle.rotation_mode, handle.rotation_euler.copy(),
            handle.rotation_quaternion.copy())
    first_position, first_rotation = samples[0][1:]
    rest_q = (rest[3] if rest[1] == 'QUATERNION' else rest[2].to_quaternion())
    if (sum((a-b)**2 for a,b in zip(first_position,rest[0])) > 1e-12
            or abs(Quaternion(first_rotation).normalized().dot(rest_q.normalized())) < 1-1e-6):
        raise ValueError('Frame-zero pose must match the attachment rest transform')
    action = bpy.data.actions.new(f'{clip}__{handle.name}')
    ad.action = action
    previous_q = None
    try:
        handle.rotation_mode = 'QUATERNION'
        for frame, position, rotation in samples:
            q = Quaternion(rotation).normalized()
            if previous_q is not None and previous_q.dot(q) < 0:
                q.negate()
            handle.location = position
            handle.rotation_quaternion = q
            handle.keyframe_insert(data_path='location', frame=frame)
            handle.keyframe_insert(data_path='rotation_quaternion', frame=frame)
            previous_q = q.copy()
        for fc in curves(action):
            for key in fc.keyframe_points:
                key.interpolation = 'LINEAR'
        ad.action = None
        track = ad.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 0, action)
        strip.extrapolation = 'HOLD_FORWARD'
        strip.influence = 1.0
        strip.blend_type = 'REPLACE'
        strip.use_auto_blend = False
        strip.blend_in = strip.blend_out = 0
        if hasattr(strip, 'action_slot') and action.slots:
            strip.action_slot = action.slots[0]
    finally:
        ad.action = None
        handle.location = rest[0]
        # Keep quaternion animation channels evaluable for Euler-authored handles too.
        handle.rotation_mode = 'QUATERNION'
        handle.rotation_quaternion = (rest[3] if rest[1] == 'QUATERNION'
                                      else rest[2].to_quaternion())
    # All independent clips start at their declared frame-zero rest pose.
    # Keep the action evaluable during construction; downstream exporters/checkers
    # isolate NLA tracks themselves.
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    return action
