# Component-level 3D modeling and animation

You build a product as **separate, named parts** that fit together like the real thing, give each part a believable material, add the motions a user expects, check the result with scripts, look at renders, and fix problems **before** showing the user.

The user should get a good model from one short request. Do not ask questions you can answer with a reasonable assumption; write the assumption down in `PLAN.md` and continue. Ask only when a wrong guess would waste the whole build (for example: which of two very different products is meant).

## Requirements

For a new installation, run `python3 scripts/doctor.py` first. `--agent` checks the terminal-agent prerequisites; `--smoke --out NEW_EMPTY_DIR` builds/checks/exports a generic example without AI calls. See [README.md](../README.md) in a full checkout for setup.

- Blender 4.2 or newer, run headless. Find it with `scripts/blender.sh --version`. If it is missing, tell the user to install Blender and stop.
- Geometry/check/render/export scripts run inside Blender's Python: `scripts/blender.sh -b --python <script> -- <args>`. Contact sheets and delivery verification use system `python3`.
- Units are **metres**. Blender is Z-up; the glTF exporter converts to Y-up. Front of the product faces **-Y** in Blender (towards the default front camera).

## Token budget (read this first)

Every step re-sends the whole conversation to the model, including every image and every
command output so far. Cost ≈ number of steps × conversation size. A good build takes about
30–45 steps. Follow these rules:

- **Use the documented API first.** [reference/api.md](api.md) lists the helpers. Read library source only to diagnose a specific failure. Read `examples/mini-oven/build.py` when a construction pattern is needed.
- **Look at photos through contact sheets:** `python3 SKILL_DIR/scripts/contact_sheet.py INPUT_DIR sheets/ --pdf MANUAL.pdf` makes a few labelled sheets plus `manual.txt`. Open a single original photo or manual page only for a specific detail you cannot read on a sheet (at most about 6 in the whole run).
- **Do not re-read your own files.** You wrote `build.py` and `PLAN.md`; edit them with targeted patches instead of printing them again. Never print large files, logs or JSON reports in full; use `grep`/`head` for the lines you need.
- **One command per build round:** `SKILL_DIR/scripts/iterate.sh PROJECT_DIR --clips none` builds, checks and renders, printing only summaries. Write `build.py` in whole sub-assemblies. Use small deterministic geometry/motion probes within the initial build when a risky interface is uncertain; do not wait until detail work to discover an impossible path.
- **Keep `build.py` fast (under about 30 s on a laptop; servers can be 10× slower).** Cut each piece with `shapes.boolean`/`cut_many` while it is still a closed solid, *then* join it to others. Joining overlapping solids first makes an open, non-watertight mesh that forces the slow exact solver on every later cut (several seconds per cut on a 40k-face body). Put many holes in one `cut_many` call on the small panel that has them. Use 16–32 segments for small round features. No custom collision/probe frameworks: `check_model.py` already tests rest overlaps and sampled motion.
- **Wait for long commands without monitoring loops.** Run each Blender command in the foreground; never wrap it in `timeout` and never background it (`&`, `nohup`). If the shell tool returns while the command is still running (a running-session id), wait on that same session with the tool's own wait/continue call using long waits (several minutes each). Do **not** run separate `sleep`/`ls`/`tail`/`date`/`ps` commands to watch logs or files: every extra call re-sends the whole conversation, so ten checks cost as much as ten build rounds. If a build is slow, make it faster (rule above) instead of watching it.
- **Small review images:** use `--size 320`; render clip sheets only for the clips you are reviewing. Open each new render sheet once.
- **Repair rounds:** after the first complete build, at most **one** repair round unless the caller allows more. Fix errors; list remaining warnings in `REVIEW.md`.

## Workflow

Use the caller's scope and budget; default to one automatic repair round for an initial
trial, rather than an open-ended polish loop. Preserve a usable partial checkpoint when
stopping. Treat product evidence as new: do not consult saved evaluations, old product build scripts or a previous product storyboard. Reusable helper guides and the generic worked examples are tooling, not product-specific evidence.

Work in a project folder (default `./c3d-<product>/`). Keep every step reproducible: retain `build.py` and every referenced helper or companion source. Record the skill version and its location needed to rebuild.

### 1. Plan (always, before any geometry)

Write `PLAN.md` with:

1. **Overall size** in metres (W × D × H). Use given dimensions; otherwise estimate from a known reference in the photos (a hand, a power plug, a standard screw, a door) and say which one. Write down the estimate's uncertainty.
2. **Parts list.** One row per part the user could see, touch, remove or that moves: id, name, approximate size, shape strategy (see step 2), material preset/colour/opacity, evidence label, parent part. Mark optional items as included or omitted; included items remain registered even if hidden. Never hide unregistered meshes at zero scale to remove check errors.
3. **Mating:** how each part attaches (sits on, clips into, hinged at, slides in). Record the receiving pocket/hole, wall thickness, insertion depth and numerical clearance for each fitted or moving interface. Real products have **gaps and seams** (typically 0.5–2 mm between panels). A button needs a pocket, an insert needs a cavity, and a gasket needs its own seat; intersecting solid blocks are insufficient.
4. **Motions:** every user-visible motion with type (hinge, slide, press, turn, light), axis, pivot location and range. For removal/service clips, give an ordered timeline: prerequisite release/opening, extraction direction, any later lateral move, which parts travel together, and the final pose held by each joint. Every independent clip must work from assembled rest; guides may declare a nonzero initial state explicitly. Read [reference/animations.md](animations.md).
5. **Details that make it look real:** seams, chamfers, vents, buttons, labels, screws, rubber feet, transparent windows. Order them by how visible they are.
6. **Assumptions and unknowns.**
7. **Manual storyboard.** A primary `how_to_use` continuous guide with ordered instructions, manual page/figure evidence, initial state, action durations, end holds and real-world pauses. Preserve state between steps. Independent clips are secondary exploration controls. Read [reference/manual-guides.md](manual-guides.md). **Do not plan or author cameras here**: cameras are a separate pass after the model is finished (step 8).

Read [reference/evidence-and-scale.md](evidence-and-scale.md) when you work from photos or a manual. Read [reference/construction-fidelity.md](construction-fidelity.md) too: stacked parts sit on each other, every lock has both halves, one moulded piece stays one part, openings are cut, details are counted from close-ups (underside photos are mirrored).

### 2. Build with `build.py`

Use the skeleton in [reference/api.md](api.md) (and `examples/mini-oven/PLAN.md` for the plan format). Import the helper library:

```python
import sys; sys.path.insert(0, SKILL_DIR + "/scripts")
from c3d import core, shapes, materials, joints, anim
```

Rules (each one prevents a common failure):

- **One Blender object per part**, named by its part id. Use `core.part(...)` so the checks and exporter recognise it. Small details that never move separately (a vent pattern, a logo) belong to their parent part's mesh, not to new floating objects.
- **Never let two surfaces share a plane.** Inset, raise or gap every detail by at least 0.3 mm (`core.EPS_GAP`). Separate parts that touch must have a real gap or a deliberate overlap listed with `core.allow_contact`. Read [reference/z-fighting-and-contacts.md](z-fighting-and-contacts.md).
- **Round every visible edge.** Real objects have no perfectly sharp edges. Use `shapes.rounded_box`, `shapes.rounded_slab` (panels, glass, buttons, recess cutters) or a bevel of 0.5–3 mm; larger radii for moulded plastic. Hard 90° edges look fake in renders.
- **Curved surfaces need the right method, not more boxes.** Revolve profiles (`shapes.lathe`), sweep along paths (`shapes.sweep`), loft between sections (`shapes.loft`), or model a cage and subdivide (`shapes.subdivided`). Then `core.smooth(obj)`. Read [reference/curved-surfaces.md](curved-surfaces.md).
- **Materials from presets**, adjusted to the photos: `materials.get("abs_matte", color="#2b2d30")`. Read [reference/materials.md](materials.md).
- **Preserve joint frames when nesting.** Use `joints.frame(inner_joint)` as the part passed to an outer joint, and attach `joints.frame(outer_joint)` to the assembly parent. Reparenting an animated joint handle detaches its fixed pivot/axis frame.
- **A part that sits inside another needs a real pocket.** A battery tray, button, LED lens, drawer or insert must sit in a cavity cut into its host (cut the pocket with `shapes.boolean` before joining the host's pieces), with 0.3–1 mm clearance on every side it slides along. Never place a solid part inside a solid host and rely on `core.allow_contact`; that is the most common source of `overlap` and `motion_collision` errors.
- **Moving parts hang from joints.** `joints.hinge(...)`, `joints.slider(...)`, `joints.button(...)`, `joints.knob(...)` create a pivot object at the real pivot and parent the part to it. Never animate a part around its own centre when the real pivot is a hinge line.
- **Prove interfaces before adding detail.** Build the major shells with real openings, their inserts and the critical joints first. Pose and check the closed, intermediate and open states before adding vents, labels and screws. Record any necessary plan correction. These probes belong to the initial build; the one-repair limit still applies after the complete first build.
- **Animations from presets:** `anim.open_close(...)`, `anim.press(...)`, `anim.turn(...)`, `anim.power(...)` for simple motions; `anim.sequence(...)` for prerequisite actions and held poses. `anim.explode(...)` is a radial candidate for unobstructed assemblies, not a general removal path. Use a staged sequence for enclosed parts. Each becomes a named clip in the GLB.
- **Eased, not robotic, motion.** Every move gets an easing curve (`ease=` on presets, a third item on `anim.sequence` keys, `ease=` on guide steps): `in_out` by default, `out` for lowering into place, `in` for pushing until it latches, `settle` for a lid or door swinging to its stop (only with clearance past the stop), `linear` only for continuous spinning. Add short holds and stagger related parts by 0.1–0.2 s. See [reference/animations.md](animations.md).

Run steps 2–4 together with `scripts/iterate.sh PROJECT_DIR --clips none` (add `--clips name1,name2` when reviewing motion). The individual commands below are what it runs. Blender output is quiet by default; full logs are in `PROJECT_DIR/.c3d-logs/`.

Build only: `scripts/blender.sh -b --python build.py -- --out model.blend`

### 3. Check (scripts, not opinion)

```
scripts/blender.sh -b model.blend --python scripts/check_model.py -- --report checks.json
```

It reports: sampled same-plane faces (z-fighting), crossing surfaces, sampled collisions during every animation clip including `explode`, open or inside-out meshes, faceted curved surfaces, pivots far from their part, and suspicious material values. Motion samples include uniform intervals, authored keys and phase midpoints. It cannot certify continuous clearance or detect every contained/partial overlap. **Fix every `error` within the permitted repair budget.** Fix `warning`s unless `PLAN.md` explains why it is intended. A contact declaration is evidence of an intended fit, never a substitute for a missing cavity or a collision repair.

### 4. Look (renders, compared with the evidence)

```
scripts/blender.sh -b model.blend --python scripts/render_views.py -- --out renders/
```

This writes `renders/views.png` (front, back, sides, top, three-quarter) and `renders/clip-<name>.png` (chronological samples including phase boundaries and midpoints). **Open and inspect these images.** Compare them side by side with the reference photos using [reference/review-checklist.md](review-checklist.md): proportions first, then silhouette, then parts and seams, then materials, then motion. Check dark transparent parts over an actual cavity/backing, not just the background. Checks cannot see air gaps between stacked parts, missing latch halves, floating buttons or wrong hole counts; look for them in the side and underside views against the close-up photos. Render all exported clips for final delivery, and state any not visually inspected in `REVIEW.md`.

### 5. Fix and repeat

Fix the most visible problem first. Re-run steps 2–4 within the agreed repair/time/usage budget (one automatic repair round by default for an initial trial). Stop at that boundary and list remaining findings in `REVIEW.md`. Do not silently buy more attempts. Keep each saved revision separate so an old export cannot appear to be the latest build.

### 6. Deliver

```
scripts/blender.sh -b model.blend --python scripts/export_glb.py -- --out model.glb
```

This writes `model.glb` (parts as named nodes, one animation clip per motion) and `model.manifest.json` (parts, materials, clips, check summary and source-file hash). Export requires a matching, zero-error check report. Use `--partial` only to save an explicitly unfinished checkpoint; its manifest records the limitations. After final renders/export, run `python3 SKILL_DIR/scripts/verify_delivery.py PROJECT_DIR --report PROJECT_DIR/delivery-report.json`. A technical pass is not human acceptance or proof of visual fidelity. The exporter copies the complete portable viewer, including its libraries and licenses. Serve that output folder with `python3 -m http.server --bind 127.0.0.1`; do not copy only the HTML or one JavaScript file.

Give the user: the GLB, the viewer, `views.png`, the clip sheets, and a short note of assumptions and known limitations from `PLAN.md` and `REVIEW.md`.

### 7. Camera pass (separate, only after the model is finished)

Spend the modeling budget on geometry and motion first. Directed cameras are presentation only and come last, ideally in their own session with its own small budget.

1. Snapshot the model: `scripts/blender.sh -b model.blend --python scripts/model_fingerprint.py -- --out fingerprint-before.json`.
2. Read [reference/manual-camera.md](manual-camera.md). In `build.py`, change **only** camera direction: add `camera=dict(...)` to every step of **every** guide (not only `how_to_use`), and call `anim.camera_clip(clip, camera)` once after each independent clip is fully authored. Do not change geometry, materials, part names, joints, motion targets or durations.
3. Rebuild, run `check_model.py`, then `render_views.py --clips all` and inspect the directed shots once. Fix occluded or cropped shots in at most one round (choose another view, angle or padding; never move the product to make a shot work).
4. Fingerprint again (`--out fingerprint-after.json`) and compare: `python3 scripts/model_fingerprint.py --compare fingerprint-before.json fingerprint-after.json`. If the model changed, the camera pass is invalid: restore the complete pre-camera delivery (`build.py`, model, GLB, manifest, checks, renders, REVIEW.md), not just `build.py`. Keep a copy of the complete delivery before starting the camera pass so it can be restored.
5. Export (as in step 6) and add a short "Camera pass" section to `REVIEW.md`: shots changed, remaining occlusions, unverified browser behaviour.

Deliver the generated GLB, its manifest, and the portable viewer files copied by `export_glb.py`. The page is a step-by-step guide: numbered steps, the instruction as a caption over the model, part labels for the parts each step's camera names, playback with step ticks, and a GLB download button. Add `?embed=1` to embed it in another page.

## Hard rules

- Every part has a material, a name and a real size. No default grey, no `Cube.001`.
- Units in metres, product sits on Z = 0, centred on X/Y.
- No coplanar surfaces, no unintended overlaps, no faceted curves on smooth products.
- Every moving part rotates about its real pivot or slides along its real axis, and stops at a believable limit.
- Do not claim accuracy you do not have. Estimated sizes, hidden internals and guessed pivots are marked as estimates.
- Never describe a result as finished without running `check_model.py` and inspecting the renders for that same saved revision. An interrupted partial result may be delivered with explicit unverified/failed findings.
- Never list a file in README.md, REVIEW.md or a summary that does not exist yet. Write the README last, from the files actually present.
