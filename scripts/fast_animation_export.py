"""Export rest geometry once and attach evaluated world-space animation tracks.

The source .blend is unchanged. This exporter flattens GLB physical transforms;
logical assemblies and documented motion interfaces remain in parts.json.
"""
import array
import json
import math
import struct
from pathlib import Path
import bpy
from mathutils import Matrix


def export_flattened(out):
    scene = bpy.context.scene
    parts = sorted([o for o in scene.objects if o.type == 'MESH' and o.get('c3d_part')], key=lambda o: o.name)
    assert parts, "No registered mesh parts to export"
    objects = list(scene.objects)
    fps = scene.render.fps / scene.render.fps_base
    conversion = Matrix.Rotation(-math.pi / 2, 4, 'X')
    inverse = conversion.inverted()
    ranges = {}
    for o in objects:
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                for s in t.strips:
                    low, high = ranges.get(t.name, (s.frame_start, s.frame_end))
                    ranges[t.name] = min(low, s.frame_start), max(high, s.frame_end)


    baseline = {o.name: o.matrix_basis.copy() for o in objects}

    def activate(name):
        for o in objects:
            o.matrix_basis = baseline[o.name]
            if o.animation_data:
                o.animation_data.action = None
                o.animation_data.use_nla = True
                for t in o.animation_data.nla_tracks:
                    t.mute = t.name != name
        scene.frame_set(0)
        bpy.context.view_layer.update()


    activate(None)
    rest = {o.name: o.matrix_world.copy() for o in parts}
    sampled = []
    for name in sorted(ranges):
        activate(name)
        start, end = ranges[name]
        step = 1  # sample at the authored Blender frame rate
        frames = list(range(int(start), int(end) + 1, step))
        if frames[-1] != int(end): frames.append(int(end))
        times = [(f - start) / fps for f in frames]
        tracks = {o.name: {'translation': [], 'rotation': [], 'scale': []} for o in parts}
        for index, frame in enumerate(frames):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            for o in parts:
                pos, quat, scale = (conversion @ o.matrix_world @ inverse).decompose()
                q = [quat.x, quat.y, quat.z, quat.w]
                previous = tracks[o.name]['rotation']
                if previous and sum(a * b for a, b in zip(q, previous[-1])) < 0:
                    q = [-v for v in q]
                tracks[o.name]['translation'].append(list(pos))
                tracks[o.name]['rotation'].append(q)
                tracks[o.name]['scale'].append(list(scale))
            if index % 300 == 0:
                print(f'[c3d] fast export: {name} sample {index}/{len(frames)}', flush=True)
        sampled.append((name, times, tracks))

    # Flatten only the preview copy in memory; the source .blend is never saved.
    for o in objects:
        o.animation_data_clear()
    for o in parts:
        o.parent = None
        o.matrix_world = rest[o.name]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    static_path = Path(out).with_suffix('.geometry.glb')
    bpy.ops.export_scene.gltf(filepath=str(static_path), export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_extras=True,
                              export_cameras=False, export_lights=False, export_animations=False)
    raw = static_path.read_bytes()
    assert raw[:4] == b'glTF'
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    bin_header = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, bin_header)[0]
    binary = bytearray(raw[bin_header + 8:bin_header + 8 + binary_length])
    nodes = {n.get('extras', {}).get('c3d_part', n.get('name')): i for i, n in enumerate(document['nodes'])}
    assert all(o.name in nodes for o in parts), 'Missing exported part node'


    def accessor(values, kind):
        while len(binary) % 4: binary.append(0)
        offset = len(binary)
        flat = values if kind == 'SCALAR' else [v for row in values for v in row]
        data = array.array('f', flat).tobytes()
        binary.extend(data)
        vi = len(document.setdefault('bufferViews', []))
        document['bufferViews'].append(dict(buffer=0, byteOffset=offset, byteLength=len(data)))
        ai = len(document.setdefault('accessors', []))
        entry = dict(bufferView=vi, componentType=5126, count=len(values), type=kind)
        if kind == 'SCALAR': entry.update(min=[min(values)], max=[max(values)])
        document['accessors'].append(entry)
        return ai


    rest_channels = {}
    for o in parts:
        p, q, s = (conversion @ rest[o.name] @ inverse).decompose()
        rest_channels[o.name] = {'translation':list(p), 'rotation':[q.x,q.y,q.z,q.w], 'scale':list(s)}
    document['animations'] = []
    for name, times, tracks in sampled:
        animation = dict(name=name, channels=[], samplers=[])
        for part, channels in tracks.items():
            for channel, values in channels.items():
                tolerance = 1e-7 if channel == 'translation' else 1e-6
                close = lambda a, b: max(abs(x-y) for x,y in zip(a,b)) < tolerance
                if all(close(values[0], row) for row in values):
                    neutral = rest_channels[part][channel]
                    if close(values[0], neutral) or (channel == 'rotation' and close(values[0], [-v for v in neutral])):
                        continue
                # Preserve the boundaries of constant intervals and all changing samples.
                keep = [0] + [i for i in range(1, len(values)-1)
                              if not (close(values[i-1], values[i]) and close(values[i], values[i+1]))] + [len(values)-1]
                input_accessor = accessor([times[i] for i in keep], 'SCALAR')
                output_accessor = accessor([values[i] for i in keep], 'VEC4' if channel == 'rotation' else 'VEC3')
                si = len(animation['samplers'])
                animation['samplers'].append(dict(input=input_accessor, output=output_accessor, interpolation='LINEAR'))
                animation['channels'].append(dict(sampler=si, target=dict(node=nodes[part], path=channel)))
        document['animations'].append(animation)
        print(f'[c3d] fast export: {name}: {len(animation["channels"])} channels', flush=True)
    for o in parts:
        p, q, s = (conversion @ rest[o.name] @ inverse).decompose()
        node = document['nodes'][nodes[o.name]]
        node.pop('matrix', None)
        node.update(translation=list(p), rotation=[q.x,q.y,q.z,q.w], scale=list(s))
    document['buffers'][0]['byteLength'] = len(binary)
    json_bytes = json.dumps(document, separators=(',', ':')).encode()
    json_bytes += b' ' * (-len(json_bytes) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    result = (struct.pack('<III', 0x46546C67, 2, 12+8+len(json_bytes)+8+len(binary))
              + struct.pack('<II', len(json_bytes), 0x4E4F534A) + json_bytes
              + struct.pack('<II', len(binary), 0x004E4942) + binary)
    Path(out).write_bytes(result)
    static_path.unlink()

    print(f"[c3d] fast export: {len(parts)} parts, {len(sampled)} clips, {len(result)/1e6:.2f} MB", flush=True)
