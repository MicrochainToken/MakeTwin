# Animations

Every motion is a **joint** (where and how a part moves) plus a **clip** (when it moves). The rest pose, value 0, is always closed / off / assembled, so every clip starts from the same model and can be played backwards to undo it.

## Joints

| Joint | Function | Pivot | Axis | Limits |
|---|---|---|---|---|
| Hinge | `joints.hinge(parts, pivot, axis, limits_deg)` | on the hinge line, at the edge that stays put | along the hinge; sign by right-hand rule so positive opens | degrees |
| Knob / dial / turntable / fan | `joints.knob(parts, axis, center, limits_deg)` | on the part's own centre line | the shaft | degrees |
| Drawer / tray / slider | `joints.slider(parts, axis, limits)` | part centre | direction of travel | metres |
| Push button | `joints.button(parts, press_axis, travel)` | part centre | **into** the product | 1–4 mm |

Group moving parts: pass every part that moves together (a door with its glass and handle), or parent the details to the main part first so they ride along.

### Getting the hinge direction right

Right-hand rule: point your thumb along the axis; your fingers curl in the positive direction. Blender axes: X right, Y away from the viewer (front faces −Y), Z up.

| Hinge | Pivot on | Axis that opens with a positive angle |
|---|---|---|
| Side door hinged on the **left**, opens towards the viewer | left edge line | `"-Z"` |
| Side door hinged on the **right**, opens towards the viewer | right edge line | `"Z"` |
| Lid hinged at the **back**, lifts up | back top edge line | `"-X"` |
| Door hinged at the **bottom**, drops forward (oven, dishwasher) | bottom front edge line | `"X"` |
| Flap hinged at the **top**, swings out at the bottom (printer cover) | top front edge line | `"-X"` |

If the end frame of the clip render shows the part swinging into the product, the sign is wrong; `check_model.py` will also report a `motion_collision`.

## Clip presets

| Preset | Use for | Notes |
|---|---|---|
| `anim.open_close(joint, clip, seconds)` | doors, lids, drawers, flaps | default 1.2 s; plays to the joint's open limit |
| `anim.press(joint, clip)` | buttons | 0.35 s in and out |
| `anim.turn(joint, clip, degrees, seconds, loops)` | knobs, dials, turntables, fans | `loops` for continuous spinning |
| `anim.power(glows, clip, buttons)` | power on, screens, indicators | presses the buttons, then switches the glows on |
| `anim.explode(clip, distance)` | simple unobstructed assembly overview | radial candidate only; enclosed parts need an extraction sequence |
| `anim.sequence(clip, steps)` | removal, service, nested doors, multi-step assembly | ordered keys and automatic held poses through the end |

Several presets can share a clip name. For example, `power_on` presses the button and lights the LED, and both become one glTF animation.

Each object may have only one track for a given clip. Put all of that joint's keys in
one `sequence` entry rather than adding another preset on the same joint/clip.

## Prerequisites, extraction and held poses

Build each clip from assembled rest, including every prerequisite inside that clip.
Do not rely on the viewer playing `open_lid` before `remove_insert`. Avoid incidental
parent chains: moving an upper rotor must not carry an independently removed lower
rotor. Parent only parts that really remain attached. A removable insert must clear
the enclosing wall before it moves sideways; a bowl may need forward travel before
lifting if the body overhangs it. Determine this from the evidence and clearance.

For a hatch that must open before its insert lifts, use two joints already created
at their true pivots. The values below are illustrative, not feeder dimensions:

```python
anim.sequence("remove_insert", [
    (hatch_hinge, [(0, 0), (0.8, 100)]),
    (insert_lift, [(0, 0), (0.8, 0), (1.8, 0.15)]),
])
```

The helper extends the hatch's final 100° value to 1.8 s, so it stays open while the
insert lifts. For lift-then-sideways removal, use nested sliders on distinct axes,
with repeated values to hold the second slider until the first clears the rim.
Check the nesting in world space: the outer joint moves its complete descendant
assembly. Do not use object scale, visibility or teleporting to dodge collisions.

When building this nesting, pass `joints.frame(inner_joint)` to the outer joint
constructor. Attach `joints.frame(outer_joint)` to the physical assembly parent.
The returned joint is an animated handle; reparenting it alone detaches it from
the fixed frame that supplies its pivot and axis. See the example in `api.md`.

Prove the critical sequence with simple shells and inserts during initial
construction, before adding small details. Motion is eased by default (`in_out`, which
never overshoots); `settle` overshoots on purpose, so use it only with clearance past the
stop. Easing does not make a blocked path safe. The checker samples keys and phase
midpoints as well as a uniform grid, including clips named `explode`. Inspect the
chronological render sheet and play/reverse the exported GLB. Sampling can miss
collisions between samples, and surface crossing checks miss complete containment.

## Make motion feel natural

Real parts accelerate and slow down; constant-speed motion looks robotic. Pick an ease for
each move (`reference/api.md`, **Easing**): `in_out` by default, `out` when something is
lowered or dropped into place, `in` when it is pushed until it latches, `settle` for a lid or
door that swings to its stop, `smooth` for long travels, and `linear` only for continuous
spinning. Give each step a short hold (0.3–0.6 s) after the move so the eye can follow, and
stagger related parts by 0.1–0.2 s instead of moving everything at once.

## Standard clip names

Use these names so viewers and apps can find the clips: `open_door`, `open_lid`, `open_drawer`, `power_on`, `press_<button>`, `turn_<knob>`, `spin_<part>`, `explode`. Add the part name when there are several (for example `open_door_left`).

## What every product should get

- Every door, lid, flap, drawer and removable tray: an open clip.
- Every button the user presses often: a press clip; the power button combines with `power_on`.
- Every indicator, screen or light: included in `power_on`.
- Every knob or dial: a turn clip.
- Rotating parts that are the product's purpose (turntable, fan, blender blade): a spin clip.
- Assembly overview: `explode` with clear extraction paths. Prefer a staged sequence
  over radial spreading when parts start inside a shell. Keep fixed details attached.

Do not animate what the evidence does not show: invented internal mechanisms, flexing parts or liquids. Say in `PLAN.md` what was left out.

## Lights and screens

`anim.glow_part(name, lens, material)` makes an emissive copy slightly larger than the lens. It is hidden at rest and switched on by `anim.power`, using standard glTF scale animation. Confirm contrast in the target viewer. For a screen showing content, add an image texture on the glow part's material. Reverse `power_on` for off; a separate off clip is only needed if the destination app requires it.
