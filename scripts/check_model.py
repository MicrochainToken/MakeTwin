"""Automatic quality checks for a c3d model.

  blender.sh -b model.blend --python check_model.py -- [--report checks.json] [--frames 12]

Exit code 1 when any error is found. Findings (severity / code):
  error   naming            default object names, unregistered mesh objects
  error   material          part without a material
  warning material_values   metallic between 0.2 and 0.8, pure black/white base colour, roughness 0
  error   zfight            two surfaces in the same plane facing the same way (will flicker)
  error   overlap           parts passing through each other at rest (not declared with allow_contact)
  error   motion_collision  a moving part passes through another part during a clip
  warning open_mesh         holes / non-manifold edges (rendering and booleans become unreliable)
  error   inside_out        closed mesh with inverted normals
  warning faceted           a curved surface built from visibly flat facets
  warning pivot_far         joint pivot far from the part it moves
  warning floating          part touching no other part at rest (e.g. a button over an opening)
  warning placement         product not resting on Z=0 or not centred
  warning scale             overall size outside 1 cm .. 10 m (wrong units?)
"""
import json
import math
import os
import re
import sys
import time

from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c3d import anim, core, joints  # noqa: E402
from guide_schema import validate_guides, validate_clip_cameras
from artifact_revision import revision  # noqa: E402

A = core.args()
REPORT = A.get("report")
N_FRAMES = int(A.get("frames", 12))
if N_FRAMES < 1:
    raise ValueError("--frames must be positive")
scene = bpy.context.scene
findings = []
DEFAULT_NAME = re.compile(r"^(Cube|Cylinder|Sphere|Plane|Cone|Torus|Circle|Mesh|Object|BézierCurve|Icosphere)"
                          r"(\.\d+)?$")


def add(severity, code, message, parts=(), where=None):
    findings.append({"severity": severity, "code": code, "message": message, "parts": list(parts),
                     "where": [round(v, 4) for v in where] if where is not None else None})


def mesh_parts():
    return [o for o in core.parts() if o.type == "MESH" and not o.get("c3d_glow")]


def world_bm(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(obj.evaluated_get(dg), dg)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    return bm


def size_scale():
    lo, hi = core.product_bbox()
    return lo, hi, max(hi - lo)


# ------------------------------------------------------------------ naming & materials

def check_naming_materials():
    for o in scene.objects:
        if o.type in ("MESH", "CURVE") and DEFAULT_NAME.match(o.name):
            add("error", "naming", f"'{o.name}' has a default name; give every part a meaningful id", [o.name])
        if o.type == "MESH" and not o.get("c3d_part"):
            add("error", "naming", f"mesh '{o.name}' is not registered with core.part()", [o.name])
    for o in mesh_parts():
        mats = [m for m in o.data.materials if m]
        if not mats:
            add("error", "material", f"'{o.name}' has no material", [o.name])
        for m in mats:
            bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
            if not bsdf:
                continue
            metal = bsdf.inputs["Metallic"].default_value
            rough = bsdf.inputs["Roughness"].default_value
            col = list(bsdf.inputs["Base Color"].default_value)[:3]
            if 0.2 < metal < 0.8:
                add("warning", "material_values", f"material '{m.name}' metallic={metal:.2f}: real materials are "
                    "metal (1) or not (0)", [o.name])
            if rough < 0.01:
                add("warning", "material_values", f"material '{m.name}' roughness 0 looks like a perfect mirror; "
                    "use >= 0.02", [o.name])
            if max(col) < 0.002:
                add("warning", "material_values", f"material '{m.name}' base colour is pure black; real black "
                    "plastic is about #151617..#2a2c2f", [o.name])
            if min(col) > 0.95 and metal < 0.5:
                add("warning", "material_values", f"material '{m.name}' base colour is pure white; use about "
                    "#f0f0ee or darker", [o.name])


# ------------------------------------------------------------------ mesh health

def check_mesh_health(scale):
    angle_lo, angle_hi = math.radians(8), math.radians(40)
    for o in mesh_parts():
        bm = world_bm(o)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        nonman = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
        if boundary or nonman:
            add("warning", "open_mesh", f"'{o.name}': {boundary} open edges, {nonman} non-manifold edges; "
                "close holes or give the surface thickness (shapes.shell)", [o.name])
        elif bm.faces:
            vol = bm.calc_volume(signed=True)
            if vol < 0:
                add("error", "inside_out", f"'{o.name}' normals point inwards (signed volume {vol:.3g})", [o.name])
        # faceting: many adjacent faces meeting at 8-40 degrees on a flat-shaded or sharp-marked surface
        smooth_faces = sum(1 for f in bm.faces if f.smooth)
        mid, total = 0, 0
        for e in bm.edges:
            if len(e.link_faces) != 2:
                continue
            a = e.calc_face_angle(0.0)
            if a < math.radians(1):
                continue
            total += 1
            shaded_flat = not e.smooth or not all(f.smooth for f in e.link_faces)
            if angle_lo < a < angle_hi and shaded_flat:
                mid += 1
        if mid >= 8 and mid / total > 0.25:
            add("warning", "faceted", f"'{o.name}': {mid} of {total} creased edges are shallow (8-40 deg) and "
                f"shaded flat ({smooth_faces}/{len(bm.faces)} faces smooth): add segments/subdivision and use "
                "core.smooth()", [o.name])
        bm.free()


# ------------------------------------------------------------------ coplanar (z-fighting)

def check_zfight(scale):
    thr = max(0.0002, 0.0004 * scale)  # closer than this in depth = flicker risk
    objs = mesh_parts()
    verts, polys, owner, normals, centers = [], [], [], [], []
    for oi, o in enumerate(objs):
        bm = world_bm(o)
        base = len(verts)
        verts.extend(v.co.copy() for v in bm.verts)
        for f in bm.faces:
            polys.append([base + v.index for v in f.verts])
            owner.append(oi)
            normals.append(f.normal.copy())
            centers.append(f.calc_center_median())
        bm.free()
    if not polys:
        return
    tree = BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)
    pairs = {}
    for i, c in enumerate(centers):
        n = normals[i]
        # Centres alone miss partial overlaps when neither face centre lies on the
        # other face. Inset corner probes catch those without flagging shared edges.
        probes = [c] + [verts[v].lerp(c, .001) for v in polys[i]]
        for probe in probes:
            for co, nn, j, dist in tree.find_nearest_range(probe, thr):
                if j == i or j is None:
                    continue
                if n.dot(normals[j]) < 0.996:
                    continue
                if owner[i] == owner[j] and set(polys[i]) & set(polys[j]):
                    continue
                d = probe - co
                along = abs(d.dot(normals[j]))
                inplane = (d - normals[j] * d.dot(normals[j])).length
                if inplane > 1e-7 or along > thr:
                    continue
                key = tuple(sorted((objs[owner[i]].name, objs[owner[j]].name)))
                pairs.setdefault(key, [set(), probe])[0].add(tuple(sorted((i, j))))
    for (a, b), (count, where) in pairs.items():
        what = f"inside '{a}'" if a == b else f"between '{a}' and '{b}'"
        add("error", "zfight", f"{len(count)} face pairs lie in the same plane {what} (closer than {thr * 1000:.2f} mm): "
            f"inset/raise one side by core.gap() = {core.gap() * 1000:.2f} mm", sorted({a, b}), where)


# ------------------------------------------------------------------ interpenetration

def trees(objs):
    out = {}
    for o in objs:
        bm = world_bm(o)
        out[o.name] = (BVHTree.FromBMesh(bm), core.bbox_world(o))
        bm.free()
    return out


def boxes_touch(a, b, pad):
    (alo, ahi), (blo, bhi) = a, b
    return all(alo[i] - pad <= bhi[i] and blo[i] - pad <= ahi[i] for i in range(3))


def overlap_pairs(objs, pad):
    t = trees(objs)
    names = list(t)
    hits = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not boxes_touch(t[a][1], t[b][1], pad):
                continue
            ov = t[a][0].overlap(t[b][0])
            if ov:
                hits[frozenset((a, b))] = len(ov)
    return hits


def check_overlaps(scale):
    allowed = core.allowed_contacts()
    hits = overlap_pairs(mesh_parts(), scale * 0.001)
    for pair, n in hits.items():
        if pair in allowed:
            continue
        a, b = sorted(pair)
        add("error", "overlap", f"'{a}' and '{b}' pass through each other ({n} crossing triangle pairs): leave a "
            "gap or cut a receiving pocket; declare contact only for a real fitted interface", [a, b])
    return hits


# ------------------------------------------------------------------ motion

def clips():
    out = {}
    for o in scene.objects:
        ad = o.animation_data
        if not ad:
            continue
        for t in ad.nla_tracks:
            for s in t.strips:
                lo, hi = out.get(t.name, (s.frame_start, s.frame_end))
                out[t.name] = (min(lo, s.frame_start), max(hi, s.frame_end))
    return out


def solo(name, rest):
    for o in scene.objects:
        o.matrix_basis = rest[o.name]
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = t.name != name


def check_contacts():
    names = {o.name for o in mesh_parts()}
    for item in json.loads(scene.get("c3d_allowed_contacts", "[]")):
        pair = [item.get("a"), item.get("b")]
        requested = item.get("motion_clips", [])
        if (any(p not in names for p in pair) or pair[0] == pair[1]
                or not isinstance(item.get("reason"), str) or not item["reason"].strip()
                or not isinstance(requested, list)
                or any(not isinstance(c, str) or c not in clips() for c in requested)):
            add("error", "contact", "Invalid contact: use registered parts, a reason and existing motion clips",
                [p for p in pair if isinstance(p, str)])


def contact_during_motion(pair, clip, rest_world):
    for item in json.loads(scene.get("c3d_allowed_contacts", "[]")):
        if pair != frozenset((item["a"], item["b"])):
            continue
        if clip in item.get("motion_clips", []):
            return True
        a, b = item["a"], item["b"]
        # A handle fixed to a door may move, but their relative transform cannot change.
        old = rest_world[a].inverted_safe() @ rest_world[b]
        new = scene.objects[a].matrix_world.inverted_safe() @ scene.objects[b].matrix_world
        if max(abs(old[i][j] - new[i][j]) for i in range(4) for j in range(4)) < 1e-6:
            return True
    return False


def check_motion(scale):
    scene.frame_set(0)
    rest = {o.name: o.matrix_basis.copy() for o in scene.objects}
    rest_world = {o.name: o.matrix_world.copy() for o in mesh_parts()}
    for name, (s, e) in clips().items():
        solo(name, rest)
        reported = set()
        samples = anim.sample_frames(name, s, e, N_FRAMES)
        for sample_index, f in enumerate(samples):
            if sample_index % 100 == 0:
                print(f"[c3d] motion {name}: {sample_index}/{len(samples)} snapshots",flush=True)
            scene.frame_set(int(f), subframe=f - int(f))
            objs = mesh_parts()
            moved = {o.name for o in objs if any(abs(o.matrix_world[i][j] - rest_world[o.name][i][j]) > 1e-7
                                                  for i in range(4) for j in range(4))}
            if not moved:
                continue
            hits = overlap_pairs(objs, scale * 0.001, include=moved, exclude=reported)
            for pair, n in hits.items():
                if not (pair & moved) or pair in reported or contact_during_motion(pair, name, rest_world):
                    continue
                reported.add(pair)
                a, b = sorted(pair)
                add("error", "motion_collision", f"clip '{name}' frame {f:.0f}: '{a}' passes through '{b}' "
                    f"({n} crossing triangle pairs): move the pivot, add clearance or reduce the range", [a, b])
    for o in scene.objects:
        o.matrix_basis = rest[o.name]
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = False
    scene.frame_set(0)


def check_pivots(scale):
    for j in scene.objects:
        if not j.get("c3d_joint"):
            continue
        try:
            joints.frame(j)
        except ValueError:
            add("error", "joint_hierarchy", f"joint '{j.name}' is detached from its fixed frame; "
                "nest/attach joints.frame(joint), not the animated joint handle", [j.name])
        p = j.matrix_world.translation
        for name in j.get("c3d_parts", []):
            o = scene.objects.get(name)
            if not o:
                continue
            lo, hi = core.bbox_world(o)
            d = Vector([max(lo[i] - p[i], 0, p[i] - hi[i]) for i in range(3)]).length
            if d > max(0.1 * max(hi - lo), 0.005):
                add("warning", "pivot_far", f"joint '{j.name}' pivot is {d * 1000:.0f} mm from '{name}'; hinges sit "
                    "on the part's edge, knobs on its axis", [name], p)


def check_floating(scale, samples=600):
    """Warn about parts that touch nothing at rest: a button over an opening, a part hanging in the air.

    A part is supported when some vertex lies within a seam's width of another part, or when it rests
    on the ground (z ~ 0). Air gaps between stacked parts that are still joined somewhere else (posts,
    collars) are not detected; those need the side-view inspection in the look step.
    """
    tolerance = max(0.0015, scale * 0.004)
    parts = mesh_parts()
    data = {}
    for o in parts:
        bm = world_bm(o)
        if not bm.verts:
            bm.free()
            continue
        co = [v.co.copy() for v in bm.verts]
        step = max(1, len(co) // samples)
        lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
        hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
        data[o.name] = (BVHTree.FromBMesh(bm), co[::step], lo, hi)
        bm.free()
    for name, (_, pts, lo, hi) in data.items():
        if lo.z <= tolerance:
            continue  # rests on the ground
        best, near = 10 * tolerance, None
        for other, (tree, _, olo, ohi) in data.items():
            if other == name or any(lo[i] > ohi[i] + best or hi[i] < olo[i] - best for i in range(3)):
                continue
            for p in pts:
                hit = tree.find_nearest(p, min(best, 10 * tolerance))
                if hit[0] is not None and hit[3] < best:
                    best, near = hit[3], other
                    if best <= tolerance:
                        break
            if best <= tolerance:
                break
        if best > tolerance:
            where = (lo + hi) / 2
            gap = f"nearest is '{near}', {best * 1000:.1f} mm away" if near else f"nothing within {best * 1000:.0f} mm"
            add("warning", "floating", f"'{name}' touches no other part at rest ({gap}): seat it in a recess, on "
                "a surface or on its mount; a part over an opening or in the air looks wrong", [name], where)


def check_placement():
    lo, hi, scale = size_scale()
    if not (0.01 <= scale <= 10):
        add("warning", "scale", f"largest dimension is {scale:.3f} m; are the units metres?")
    if abs(lo.z) > max(0.001, 0.005 * scale):
        add("warning", "placement", f"product bottom is at z={lo.z * 1000:.1f} mm; it should rest on z=0")
    c = (lo + hi) / 2
    if math.hypot(c.x, c.y) > 0.15 * scale:
        add("warning", "placement", f"product centre is ({c.x:.3f}, {c.y:.3f}) m; centre the main body on x=y=0")
    return scale



completed_stages = []
def stage(name, fn):
    started = time.monotonic()
    print('[c3d] START ' + name, flush=True)
    result = fn()
    completed_stages.append({'stage':name,'seconds':round(time.monotonic()-started,3)})
    print('[c3d] DONE '+name+' '+str(completed_stages[-1]['seconds'])+' s',flush=True)
    if REPORT:
        progress = {'status':'incomplete','completedStages':completed_stages,'findings':findings,
                    'sourceBlend':revision(bpy.data.filepath)}
        target = Path(REPORT).with_name(Path(REPORT).stem + '.progress.json')
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(progress,indent=2))
        temporary.replace(target)
    return result

def main():
    scene.frame_set(0)
    for error in validate_guides(json.loads(scene.get("c3d_guides", "[]")),
                                 {n: (e-s) / anim.fps() for n,(s,e) in clips().items()},
                                 {o.get("c3d_part") for o in core.parts()}):
        add("error", "guide", error)
    for error in validate_clip_cameras(json.loads(scene.get('c3d_clip_cameras', '{}')),
                                       {n: (e-s) / anim.fps() for n,(s,e) in clips().items()},
                                       {o.get('c3d_part') for o in core.parts()}):
        add('error', 'camera', error)
    stage('naming/materials', lambda: check_naming_materials())
    scale = stage("placement", check_placement)
    stage('mesh health', lambda: check_mesh_health(scale))
    stage('z-fighting', lambda: check_zfight(scale))
    stage('contact declarations', lambda: check_contacts())
    stage('rest overlaps', lambda: check_overlaps(scale))
    stage('support/floating', lambda: check_floating(scale))
    stage('joint pivots', lambda: check_pivots(scale))
    stage('motion collisions', lambda: check_motion(scale))
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    provenance = {"sourceBlend": revision(bpy.data.filepath), "checker": revision(__file__)}
    report = {"provenance": provenance, "validationStages": completed_stages,
              "motionSampling": {"uniformIntervals": N_FRAMES, "includesKeyframesAndPhaseMidpoints": True,
                                 "includesExplode": True, "continuousCollisionDetection": False},
              "summary": {"errors": errors, "warnings": warnings, "parts": len(mesh_parts()),
                          "clips": sorted(clips())}, "findings": findings}
    shown = sorted(findings, key=lambda f: f["severity"] != "error")[:12]
    for f in shown:
        print(f"[c3d] {f['severity'].upper():7} {f['code']:16} {f['message']}")
    if len(findings) > len(shown):
        print(f"[c3d] ... {len(findings) - len(shown)} more findings in the report file")
    print(f"[c3d] {errors} errors, {warnings} warnings, {len(mesh_parts())} parts, clips: {', '.join(sorted(clips()))}")
    if REPORT:
        with open(REPORT, "w") as fh:
            json.dump(report, fh, indent=2)
    sys.stdout.flush()
    os._exit(1 if errors else 0)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collision_cache import install
install(globals())
main()
