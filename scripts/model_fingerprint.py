"""Fingerprint everything a camera pass must not change; compare two fingerprints.

  In Blender:  blender.sh -b model.blend --python model_fingerprint.py -- --out fingerprint.json
  Compare:     python3 model_fingerprint.py --compare before.json after.json   (exit 1 if changed)

Covered: part names, mesh geometry, rest placement, materials, joints (type, axis, limits,
pivot, parts) and every animation channel's sequence of values with the duration of each
change. Ignored on purpose: timing shifts from camera lead-ins (a held value inserted before a
motion), camera metadata and render settings.
"""
import hashlib
import json
import sys


def _r(v, nd=5):
    return round(float(v), nd) + 0.0


def collapse(keys):
    """[(frame, value)] -> [(value, frames since the previous value change)], holds removed."""
    out, last_frame = [], None
    for frame, value in keys:
        v = _r(value, 4)
        if out and out[-1][0] == v:
            last_frame = frame  # a hold: remember where the held value ends
            continue
        out.append([v, None if last_frame is None else _r(frame - last_frame, 2)])
        last_frame = frame
    return out


def fingerprint():
    import bpy
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    from c3d import anim, core

    scene = bpy.context.scene
    for o in scene.objects:
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = True
    scene.frame_set(0)
    parts = {}
    for o in sorted(core.parts(), key=lambda o: o.name):
        h = hashlib.sha256()
        if o.type == "MESH":
            # Order-independent: Blender's exact boolean is multithreaded and may emit the same
            # vertices and faces in a different order on every build.
            co = ["%.5f,%.5f,%.5f" % tuple(v.co) for v in o.data.vertices]
            faces = []
            for p in o.data.polygons:
                f = [co[i] for i in p.vertices]
                k = f.index(min(f))
                faces.append("|".join(f[k:] + f[:k]))  # same winding, canonical start
            h.update("\n".join(sorted(co)).encode())
            h.update("\n".join(sorted(faces)).encode())
        parts[o.name] = {
            "mesh": h.hexdigest()[:16],
            "matrix": [[_r(x) for x in row] for row in o.matrix_world],
            "materials": [m.name if m else None for m in getattr(o.data, "materials", [])],
            "parent": o.parent.name if o.parent else None,
        }
    materials = {}
    for m in bpy.data.materials:
        if not m.users or not m.use_nodes:
            continue
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b:
            materials[m.name] = {k: ([_r(x, 4) for x in b.inputs[k].default_value]
                                     if hasattr(b.inputs[k].default_value, "__len__") else _r(b.inputs[k].default_value, 4))
                                 for k in ("Base Color", "Metallic", "Roughness", "Alpha") if k in b.inputs}
    joints = {}
    for j in scene.objects:
        if j.get("c3d_joint"):
            joints[j.name] = {"type": j["c3d_joint"], "axis": [_r(x, 4) for x in j["c3d_axis"]],
                              "limits": [_r(x, 4) for x in j["c3d_limits"]], "parts": list(j["c3d_parts"]),
                              "pivot": [_r(x) for x in j.matrix_world.translation]}
    motion = {}
    for o in scene.objects:
        ad = o.animation_data
        if not ad:
            continue
        for t in ad.nla_tracks:
            for s in t.strips:
                if not s.action:
                    continue
                for fc in anim.curves(s.action):
                    keys = sorted((k.co.x, k.co.y) for k in fc.keyframe_points)
                    motion[f"{t.name}|{o.name}|{fc.data_path}[{fc.array_index}]"] = collapse(keys)
    for o in scene.objects:
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = False
    return {"parts": parts, "materials": materials, "joints": joints, "motion": motion}


def compare(a, b):
    diffs = []
    for section in ("parts", "materials", "joints", "motion"):
        x, y = a.get(section, {}), b.get(section, {})
        for k in sorted(set(x) | set(y)):
            if k not in x:
                diffs.append(f"{section}: added {k}")
            elif k not in y:
                diffs.append(f"{section}: removed {k}")
            elif x[k] != y[k]:
                diffs.append(f"{section}: changed {k}")
    return diffs


def main():
    argv = sys.argv
    if "--compare" in argv:
        i = argv.index("--compare")
        a, b = (json.load(open(p)) for p in argv[i + 1:i + 3])
        diffs = compare(a, b)
        for d in diffs[:30]:
            print("[c3d] model changed:", d)
        if len(diffs) > 30:
            print(f"[c3d] ... {len(diffs) - 30} more differences")
        print(f"[c3d] fingerprint {'CHANGED' if diffs else 'unchanged'}"
              + (f" ({len(diffs)} differences)" if diffs else ": camera pass left the model intact"))
        sys.exit(1 if diffs else 0)
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    out = args[args.index("--out") + 1] if "--out" in args else "fingerprint.json"
    data = fingerprint()
    with open(out, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
    print(f"[c3d] fingerprint: {len(data['parts'])} parts, {len(data['joints'])} joints, "
          f"{len(data['motion'])} motion channels -> {out}")


if __name__ == "__main__":
    main()
