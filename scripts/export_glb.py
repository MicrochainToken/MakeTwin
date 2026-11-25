"""Export a c3d model to GLB with one animation clip per motion, plus a manifest.

  blender.sh -b model.blend --python export_glb.py -- --out model.glb [--checks checks.json]

model.glb            parts as named nodes (origin at each part's centre), joints as nodes,
                     PBR materials, animations named after the clips (open_door, power_on...)
model.manifest.json  parts, labels, materials, sizes, joints, clips and the check summary
"""
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guide_schema import validate_guides, validate_clip_cameras, CAMERA_ANGLES
from c3d import core  # noqa: E402
from delivery_files import copy_asset, viewer_assets
from artifact_revision import revision, check_report_issues, write_json  # noqa: E402

A = core.args()
OUT = os.path.abspath(A.get("out", "model.glb"))
CHECKS = A.get("checks")
scene = bpy.context.scene


def clips():
    out = {}
    for o in scene.objects:
        ad = o.animation_data
        if not ad:
            continue
        for t in ad.nla_tracks:
            t.mute = True
            for s in t.strips:
                lo, hi = out.get(t.name, (s.frame_start, s.frame_end))
                out[t.name] = (min(lo, s.frame_start), max(hi, s.frame_end))
    return out


def main():
    source = revision(bpy.data.filepath)
    checks_path = CHECKS or os.path.join(os.path.dirname(OUT), "checks.json")
    report = None
    issues = ["No check report exists; run check_model.py for this revision."]
    if os.path.exists(checks_path):
        with open(checks_path) as fh:
            report = json.load(fh)
        issues = check_report_issues(report, source)
    partial = bool(A.get("partial", False))
    if issues and not partial:
        raise ValueError("Export blocked: " + " ".join(issues) + " Use --partial only to preserve an explicitly unfinished draft.")
    scene.frame_set(0)
    clip_ranges = clips()
    # NLA_TRACKS exports muted tracks individually. Keep all other tracks muted
    # while sampling so a guide initial pose cannot contaminate other clips.
    for j in bpy.context.scene.objects:
        if j.get("c3d_joint"):
            from c3d.joints import set_value
            set_value(j, 0)
    scene.frame_set(0)
    bpy.context.view_layer.update()
    fps = scene.render.fps / scene.render.fps_base
    parts = []
    for o in core.parts():
        if o.type != "MESH":
            continue
        lo, hi = core.bbox_world(o)
        chain, p = [], o.parent
        while p is not None:
            chain.append(p.name)
            p = p.parent
        parts.append({"id": o.name, "label": o.get("c3d_label", o.name), "glow": bool(o.get("c3d_glow")),
                      "materials": [m.name for m in o.data.materials if m],
                      "presets": sorted({m.get("c3d_preset", "") for m in o.data.materials if m} - {""}),
                      "size_m": [round(v, 4) for v in (hi - lo)],
                      "center_m": [round(v, 4) for v in (lo + hi) / 2], "parents": chain})
    joints = [{"id": j.name, "type": j["c3d_joint"], "limits": list(j["c3d_limits"]),
               "parts": list(j["c3d_parts"]), "pivot_m": [round(v, 4) for v in j.matrix_world.translation]}
              for j in scene.objects if j.get("c3d_joint")]
    lo, hi = core.product_bbox()
    manifest = {
        "model": os.path.basename(OUT),
        "units": "metres", "up": "+Y (glTF)", "front": "+Z (glTF) = -Y (Blender)",
        "size_m": [round(v, 4) for v in (hi - lo)],
        "boundsScope": "All registered non-glow parts, including loose accessories; not necessarily nominal assembled-product dimensions.",
        "parts": parts, "joints": joints,
        "clips": [{"name": n, "seconds": round((e - s) / fps, 6)} for n, (s, e) in sorted(clip_ranges.items())],
        "schemaVersion": 5,
        "mechanism": json.loads(scene.get("c3d_mechanism", "{}")),
        **({"metrics": json.loads(scene["c3d_metrics"])} if "c3d_metrics" in scene else {}),
        "cameraViews": CAMERA_ANGLES,
        "clipCameras": json.loads(scene.get('c3d_clip_cameras', '{}')),
        "guides": json.loads(scene.get("c3d_guides", "[]")),
        "allowed_contacts": json.loads(scene.get("c3d_allowed_contacts", "[]")),
    }
    durations = {c['name']: c['seconds'] for c in manifest['clips']}
    ids = {p['id'] for p in parts}
    metadata_errors = validate_guides(manifest['guides'], durations, ids) + validate_clip_cameras(manifest['clipCameras'], durations, ids)
    if metadata_errors:
        raise ValueError('; '.join(metadata_errors))
    # Scene extras are portable alongside the sidecar, and audited against it.
    scene['c3d_camera_metadata'] = json.dumps({k: manifest[k] for k in ('schemaVersion', 'cameraViews', 'guides', 'clipCameras')})
    # measure everything above at rest; the exporter leaves objects posed mid-animation
    kwargs = dict(filepath=OUT, export_format="GLB", use_selection=False, export_apply=True,
                  export_yup=True, export_extras=True, export_cameras=False, export_lights=False,
                  export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
                  export_def_bones=False, export_optimize_animation_size=True, export_optimize_animation_keep_anim_object=True)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    if 'export_optimize_animation_keep_anim_object' not in props:
        kwargs['export_optimize_animation_size'] = False
    kwargs = {k: v for k, v in kwargs.items() if k in props or k == "filepath"}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".glb", dir=os.path.dirname(OUT), delete=False) as temp:
        temporary = temp.name
    try:
        kwargs["filepath"] = temporary
        if A.get("fast-transform-export", False):
            from fast_animation_export import export_flattened
            export_flattened(temporary)
        else:
            bpy.ops.export_scene.gltf(**kwargs)
        os.replace(temporary, OUT)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    scene.frame_set(0)
    if A.get("fast-transform-export", False):
        manifest["representation"] = {"animatedTransforms": "flattened world-space part nodes", "assemblyHierarchy": "Blender source and parts.json", "sampling": "authored Blender frame rate"}
    manifest["provenance"] = {"sourceBlend": source, "exporter": revision(__file__)}
    manifest["artifact"] = revision(OUT)
    manifest["validation"] = {"status": "partial" if partial else "checks_passed",
                              "issues": issues, "reviewStatus": "human_review_required"}
    if report is not None:
        manifest["checks"] = report["summary"]
    mpath = os.path.splitext(OUT)[0] + ".manifest.json"
    write_json(mpath, manifest)
    for asset in viewer_assets():
        copy_asset(asset, Path(OUT).parent / asset.name)
    size = os.path.getsize(OUT) / 1e6
    print(f"[c3d] wrote {OUT} ({size:.2f} MB, {len(parts)} parts, clips: {', '.join(sorted(clip_ranges))})")
    print(f"[c3d] wrote {mpath}")


main()
