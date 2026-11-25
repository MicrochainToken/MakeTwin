# Camera-directed walkthroughs

Begin with an isometric overview. For each manual chapter, choose a view that exposes the upcoming action, including its moving part and mounting context. Read the geometry as well as the manual: fitting a bounding box does not prove the part is visible through an opaque housing. Review the authored shots and change an occluded angle.

```python
shot = dict(view="rear", parts=["panel", "housing"],
            padding=1.5, transitionSeconds=.8)
g.step("open", "Open the panel", {hinge:95}, seconds=1.2, hold=1,
       evidence=evidence, camera=shot)
# After authoring every channel of an independent clip:
anim.camera_clip("panel_open", shot)
```

`Guide.step(..., camera=None, lead=None)` defaults the stationary lead-in to the camera transition, rounded up to whole frames. `seconds` remains the mechanical action duration; `hold` follows it. Explicit `lead` must cover the transition. The manifest adds `motionStartSeconds` between chapter start and action end. Unchanged joints preserve the previous chapter state. Independent `anim.camera_clip(clip, camera, lead=None)` shifts all authored channels together and inserts a stationary lead; call it once, after authoring the complete clip. It must not be used on a guide clip. Its manifest record is `clipCameras[clip]` with camera and timing fields.

The optional camera dictionary supports:

| Field | Meaning |
| --- | --- |
| `view` | isometric, front, rear, left, right, top, underside; defaults to isometric |
| `parts` | registered stable component IDs to frame; omission frames the product |
| `padding` | framing multiplier, 1.05–4, default 1.5 |
| `transitionSeconds` | 0–5, default .8; must finish before motion |
| `azimuth` | optional -180–180 degree override |
| `elevation` | optional -85–85 degree override |
| `minContext` | .05–1 of overview radius, default .15 |

Angles use glTF coordinates: Y up, front +Z, positive azimuth toward +X. Blender uses Z up and front -Y. Named angles live centrally in `templates/viewer/camera-views.json`; the Blender render math reads the same file. Do not move the physical model to manufacture visibility. Use an oblique angle to see beneath a raised lid; a strictly overhead shot may still hide the opening.

The shared director evaluates the timeline deterministically, samples current moving bounds, eases the target, fits the viewport and keeps the camera outside the product's conservative bounding sphere. It holds the shot after motion. Seek/replay produce the same timeline shot; restart returns to overview. Previous/Next play the selected chapter, including its camera lead-in, and stop at its end. Pause freezes the timeline camera. Manual orbit/zoom suspends automatic direction; Auto view resumes with a short blend. Reduced-motion mode uses immediate shots. Old clips without metadata remain playable with overview framing.

Serve the generated `model.glb`, its manifest, and the portable viewer files copied by `export_glb.py` together over localhost. The portable viewer uses the shared playback/director modules. `render_views.py --clips all` records directed camera samples around lead-in, action and held poses. Check the actual GLB in a browser too, including narrow framing, occlusion, caption overlap, pause/restart, chapter seek and manual override. A passing schema, bounding-box test or collision report does not certify instructional visibility. Record unavailable checks honestly in REVIEW.md.
