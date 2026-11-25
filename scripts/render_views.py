"""Render review images of a c3d model.

  blender.sh -b model.blend --python render_views.py -- --out renders/ [--size 640] [--clips all|none|a,b]
                                                        [--engine auto|eevee|cycles] [--max-frames N]
  --max-frames caps the samples per clip sheet, spread evenly and always keeping the first and
  last (default: 12 when rendering with Cycles on the CPU, otherwise unlimited; 0 = unlimited).
  auto uses EEVEE when a GPU is available, otherwise Cycles on the CPU (slower, same look).

Writes:
  renders/views.png        4 x 2 grid: front, three-quarter front-left, left, back,
                           top, three-quarter front-right, right, low three-quarter
  renders/underside*.png   the product seen from below (floor hidden), front and back
  renders/clip-<name>.png  chronological phase boundaries and midpoints
  renders/<view>.png       the single images
The scene file is not modified.
"""
import math
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from camera_math import shot_at, position_for
from c3d import anim, core  # noqa: E402
from artifact_revision import revision, write_json  # noqa: E402

A = core.args()
OUT = os.path.abspath(A.get("out", "renders"))
SIZE = int(A.get("size", 640))
CLIPS = A.get("clips", "all")
ENGINE = A.get("engine", "auto")  # auto | eevee | cycles (CPU; for servers without a GPU)
MAX_FRAMES = A.get("max-frames")
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
WRITTEN = []

# (name, azimuth deg from front, elevation deg). Front camera looks along +Y.
VIEWS = [("front", 0, 8), ("front_left", -40, 22), ("left", -90, 8), ("back", 180, 12),
         ("top", 0, 89), ("front_right", 40, 22), ("right", 90, 8), ("low_front", -25, -6)]
# Underside views (floor hidden), single images only: switches, feet, battery doors and clip
# sockets live there, and underside photos are compared against them in reviews.
UNDERSIDE = [("underside", 0, -62), ("underside_back", 180, -62)]


PROBE = """
import bpy
s = bpy.context.scene
for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        s.render.engine = name
        break
    except TypeError:
        pass
s.render.resolution_x = s.render.resolution_y = 16
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
s.collection.objects.link(cam)
s.camera = cam
s.render.filepath = "{out}"
bpy.ops.render.render(write_still=True)
print("C3D_EEVEE_OK")
"""


def has_gpu():
    """Can EEVEE render here? Servers often expose a GPU device that cannot run it, and then
    Blender crashes instead of raising, so test in a separate process (Linux only)."""
    if not sys.platform.startswith("linux"):
        return True
    import subprocess
    import tempfile
    out = os.path.join(tempfile.mkdtemp(), "probe.png")
    try:
        r = subprocess.run([bpy.app.binary_path, "--factory-startup", "-b", "--python-expr",
                            PROBE.format(out=out)], capture_output=True, text=True, timeout=120)
        return r.returncode == 0 and "C3D_EEVEE_OK" in r.stdout
    except Exception:
        return False


def setup_render():
    engine = ENGINE
    if engine == "auto":
        engine = "eevee" if has_gpu() else "cycles"
    if engine == "cycles":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
        scene.cycles.max_bounces = 6
        scene.cycles.transparent_max_bounces = 16
    else:
        for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = name
                break
            except TypeError:
                continue
        ee = scene.eevee
        for attr, val in (("taa_render_samples", 48), ("use_shadows", True), ("use_raytracing", False)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    print(f"[c3d] render engine: {scene.render.engine}")
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in
        scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("c3d_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.66, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world


def add_lights(center, size):
    def area(name, loc, energy, s):
        L = bpy.data.lights.new(name, "AREA")
        L.energy = energy
        L.size = s
        o = core.link(bpy.data.objects.new(name, L))
        o.location = loc
        d = center - Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return o
    k = size
    p = 300 * k * k
    area("key", center + Vector((-1.6, -2.0, 2.2)) * k, p * 1.3, 1.5 * k)
    area("fill", center + Vector((2.2, -1.2, 0.8)) * k, p * 0.5, 2.5 * k)
    area("rim", center + Vector((0.5, 2.4, 2.0)) * k, p * 0.8, 1.5 * k)


def add_floor(lo, hi, size):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size * 4)
    me = bpy.data.meshes.new("c3d_floor")
    bm.to_mesh(me)
    o = core.link(bpy.data.objects.new("c3d_floor", me))
    o.location = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z - 0.0005)
    m = bpy.data.materials.new("c3d_floor")
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.5, 0.52, 0.54, 1)
    b.inputs["Roughness"].default_value = 0.9
    me.materials.append(m)
    return o


def camera(center, radius):
    cam = bpy.data.cameras.new("c3d_cam")
    cam.lens = 50
    cam.clip_start = radius * 0.01
    cam.clip_end = radius * 100
    o = core.link(bpy.data.objects.new("c3d_cam", cam))
    scene.camera = o
    return o


def aim(cam, center, radius, az, el):
    fov = cam.data.angle
    dist = radius / math.sin(fov / 2) * 1.08
    a, e = math.radians(az), math.radians(el)
    off = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = center + off * dist
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    if abs(el) >= 80:
        cam.rotation_euler = (0, 0, 0)
        cam.location = center + Vector((0, 0, dist))


def render_to(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    WRITTEN.append(path)
    return path


def load(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def save_grid(paths, cols, out):
    tiles = [load(p) for p in paths]
    h, w, _ = tiles[0].shape
    rows = math.ceil(len(tiles) / cols)
    sheet = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        r = rows - 1 - r  # Blender images are stored bottom-up
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = t
    img = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    img.pixels.foreach_set(sheet.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    WRITTEN.append(out)
    bpy.data.images.remove(img)
    return out


def cap_frames(frames, limit):
    """Evenly spaced subset of `frames` (sorted), keeping the first and last."""
    if not limit or limit <= 0 or len(frames) <= limit:
        return list(frames)
    if limit == 1:
        return [frames[0]]
    idx = sorted({round(i * (len(frames) - 1) / (limit - 1)) for i in range(limit)})
    return [frames[i] for i in idx]


def clip_names():
    names = []
    for o in scene.objects:
        ad = o.animation_data
        if ad:
            for t in ad.nla_tracks:
                if t.name not in names:
                    names.append(t.name)
    return names


REST = {}


def remember_rest():
    for o in scene.objects:
        REST[o.name] = o.matrix_basis.copy()


def solo(clip):
    """Mute every NLA track except `clip` (None = rest pose). Returns its frame range.

    Muting a track does not undo what it already wrote, so the rest pose is restored first.
    """
    for o in scene.objects:
        if o.name in REST:
            o.matrix_basis = REST[o.name]
    start, end = None, 0
    for o in scene.objects:
        ad = o.animation_data
        if not ad:
            continue
        for t in ad.nla_tracks:
            t.mute = t.name != clip
            if t.name == clip:
                for s in t.strips:
                    start = s.frame_start if start is None else min(start, s.frame_start)
                    end = max(end, s.frame_end)
    return int(start or 0), int(end)


def moving_parts(clip, s, e):
    """Mesh parts whose world placement or size differs anywhere between frames s and e."""
    frames = anim.sample_frames(clip, s, e, intervals=4, neighbors=False)
    mats = {}
    for f in frames:
        scene.frame_set(int(f), subframe=f - int(f))
        for o in core.parts():
            if o.type == "MESH":
                mats.setdefault(o.name, []).append(o.matrix_world.copy())
    out = []
    for name, ms in mats.items():
        if any(max(abs(a[i][j] - ms[0][i][j]) for i in range(4) for j in range(4)) > 1e-6 for a in ms[1:]):
            out.append(scene.objects[name])
    return out, frames


def motion_frame(clip, s, e, product_radius):
    """Camera target and radius covering the moving parts over the whole clip.

    Small motions (a button, an indicator) get a close-up, never less than 30% of the product.
    """
    movers, frames = moving_parts(clip, s, e)
    if not movers:
        lo, hi = core.product_bbox()
        return (lo + hi) / 2, (hi - lo).length / 2
    los, his = [], []
    for f in frames:
        scene.frame_set(int(f), subframe=f - int(f))
        for o in movers:
            if o.get("c3d_glow"):
                o = o.parent or o
            lo, hi = core.bbox_world(o)
            los.append(lo)
            his.append(hi)
    lo = Vector([min(v[i] for v in los) for i in range(3)])
    hi = Vector([max(v[i] for v in his) for i in range(3)])
    return (lo + hi) / 2, max((hi - lo).length / 2 * 1.6, 0.3 * product_radius)


def main():
    source = revision(bpy.data.filepath)
    manifest_path = os.path.join(OUT, "render-manifest.json")
    manifest = {"provenance": {"sourceBlend": source, "renderer": revision(__file__)},
                "complete": False, "size": SIZE, "requestedClips": CLIPS, "files": [], "clipSamples": {}, "cameraShots": {}}
    write_json(manifest_path, manifest)
    if CLIPS not in ("all", "none"):
        unknown = set(CLIPS.split(",")) - set(clip_names())
        if unknown:
            raise ValueError("Unknown requested animation clips: " + ", ".join(sorted(unknown)))
    setup_render()
    for obj in scene.objects:
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                track.mute = True
        if obj.get('c3d_joint'):
            from c3d.joints import set_value
            set_value(obj,0)
        if obj.get('c3d_glow'):
            obj.scale=(1e-4,)*3
    scene.frame_set(0)
    remember_rest()
    solo(None)
    scene.frame_set(0)
    lo, hi = core.product_bbox()
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2
    add_lights(center, radius * 2)
    floor = add_floor(lo, hi, radius * 2)
    cam = camera(center, radius)
    paths = []
    for name, az, el in VIEWS:
        aim(cam, center, radius, az, el)
        paths.append(render_to(os.path.join(OUT, f"{name}.png")))
    print("[c3d] wrote", save_grid(paths, 4, os.path.join(OUT, "views.png")))
    floor.hide_render = True
    for name, az, el in UNDERSIDE:
        aim(cam, center, radius, az, el)
        render_to(os.path.join(OUT, f"{name}.png"))
    floor.hide_render = False

    names = clip_names()
    if CLIPS == "none":
        names = []
    elif CLIPS != "all":
        names = [n for n in names if n in CLIPS.split(",")]
    for clip in names:
        s, e = solo(clip)
        c2, r2 = motion_frame(clip, s, e, radius)
        shots = []
        aim(cam, c2, r2, -35, 25)
        guide = next((g for g in json.loads(scene.get('c3d_guides','[]')) if g['clip']==clip), None)
        record = json.loads(scene.get('c3d_clip_cameras','{}')).get(clip)
        steps = guide['steps'] if guide else ([dict(record, startSeconds=0)] if record else [])
        directed = any(step.get('camera') for step in steps)
        def bounds_at(t, parts=None):
            f = t * anim.fps() + s
            scene.frame_set(int(f), subframe=f-int(f))
            selected = [o for o in core.parts() if o.type=='MESH' and not o.get('c3d_glow') and (not parts or o.get('c3d_part') in parts)]
            lo,hi = core.product_bbox(selected)
            return {'min':[lo.x,lo.z,-hi.y], 'max':[hi.x,hi.z,-lo.y]}
        overview = bounds_at(0)
        manifest['cameraShots'][clip] = []
        frames = anim.sample_frames(clip, s, e, intervals=2, neighbors=False)
        limit = int(MAX_FRAMES) if MAX_FRAMES is not None else (12 if scene.render.engine == "CYCLES" else 0)
        if limit and len(frames) > limit:
            print(f"[c3d] {clip}: rendering {limit} of {len(frames)} sample frames (--max-frames)")
            frames = cap_frames(frames, limit)
        manifest["clipSamples"][clip] = frames
        for i, f in enumerate(frames):
            tag = f"phase-{i:02d}"
            if directed:
                shot = shot_at(steps, (f-s)/anim.fps(), bounds_at, overview)
                pose = position_for(shot, 35, scene.render.resolution_x/scene.render.resolution_y, overview)
                # Blender camera horizontal sensor fit, square review image.
                cam.data.type = 'PERSP';cam.data.angle = math.radians(35)
                cam.data.clip_start = max(1e-5, shot['radius']/1000)
                cam.data.clip_end = max(pose['distance']*10,shot['radius']*100)
                cam.location = Vector((pose['position'][0],-pose['position'][2],pose['position'][1]))
                target=Vector((pose['target'][0],-pose['target'][2],pose['target'][1]))
                cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
                # A presentation floor would hide an underside view. No physical part is hidden.
                scene.objects['c3d_floor'].hide_render = shot['pitch'] < 0
                manifest['cameraShots'][clip].append(dict(timeSeconds=(f-s)/anim.fps(), shot=shot, pose=pose))
            scene.frame_set(int(f), subframe=f - int(f))
            shots.append(render_to(os.path.join(OUT, f"clip-{clip}-{tag}.png")))
        scene.objects['c3d_floor'].hide_render = False
        print("[c3d] wrote", save_grid(shots, 3, os.path.join(OUT, f"clip-{clip}.png")))
    solo(None)
    for o in scene.objects:
        if o.animation_data:
            for t in o.animation_data.nla_tracks:
                t.mute = False
    manifest.update(complete=True, engine=scene.render.engine, clips=names,
                    files=[revision(p) for p in WRITTEN])
    write_json(manifest_path, manifest)


main()
