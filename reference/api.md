# Helper API

Everything below is in `scripts/c3d/`. Sizes in metres, angles in degrees, colours as sRGB hex.
Every shape function returns a new mesh object in world space; register it with `core.part`.
`axis` accepts "X", "Y", "Z", "-X", "-Y", "-Z" or a vector.

## core
| Call | Does |
|---|---|
| `core.args()` | dict of `--key value` arguments after `--` |
| `core.reset_scene(product_size=(W, D, H))` | empty scene, metric units; call first |
| `core.gap()` | product-scaled separation (≥ 0.3 mm) for seams, insets, clearances |
| `core.part(obj, pid, material=None, parent=None, label=None)` | register a part (names object + mesh, centres its origin) |
| `core.set_parent(child, parent)` | parent, keeping world placement |
| `core.allow_contact(a, b, reason, motion_clips=())` | deliberate fitted contact at rest; persists for rigid attachments, relative movement needs specific clip names; never masks z-fighting |
| `core.smooth(obj, angle_deg=35)` | smooth shading, keeps edges sharper than the angle |
| `core.apply_modifiers(obj)` | bake modifiers |
| `core.bbox_world(obj)` → `(lo, hi)` | world bounds |
| `core.product_bbox(objs=None)` → `(lo, hi)` | bounds of all parts, or of `objs` |
| `core.finish(path)` | reset joints, set frame range, save `.blend`; call last |

## shapes
| Call | Use for |
|---|---|
| `rounded_box(name, (w, d, h), radius, center, segments=4, top_radius=None)` | bodies, housings, any rounded block |
| `rounded_slab(name, width, height, depth, radius, center, axis="Y")` | panels, glass, buttons, doors, recess cutters (straight walls) |
| `box(name, (w, d, h), center)` | cutters only (sharp) |
| `cylinder(name, radius, height, center, axis="Z", segments=64, bevel=0)` | shafts, feet, LEDs, round buttons |
| `lathe(name, [(r, h), ...], center, axis="Z", segments=96)` | knobs, bowls, bottles, lids; start/end at r=0 to close |
| `sweep(name, [(x, y, z), ...], radius, segments=24, cap=True, smooth_path=True)` | handles, cables, tube frames |
| `section_rounded_rect(w, d, r, z, n_corner=8, center=(0, 0))` / `section_superellipse(w, d, z, exponent=2.5, n=64)` | loops for `loft` (same point count) |
| `loft(name, [loop, loop, ...], cap_start=True, cap_end=True)` | bodies whose section changes (hoppers, kettles, shells) |
| `subdivided(name, verts, faces, levels=2, creases={(i, j): 1.0})` | organic shapes from a coarse cage |
| `extrude_outline(name, [(u, v), ...], depth, plane="XZ"/"XY"/"YZ", offset=0, bevel=0)` | brackets, plates, flat outlines |
| `boolean(target, cutter, operation="DIFFERENCE")` | one cut/union; cutter overshoots by ≥ `core.gap()`; fast only when both are closed solids, so cut before joining |
| `cut_many(target, [cutters])` | many cuts (vents, slots, holes) |
| `bevel(obj, width, segments=3, angle_deg=30)` | round edges after booleans |
| `shell(obj, thickness, inward=True)` | give an open surface real thickness |
| `move(obj, (dx, dy, dz))`, `rotate(obj, degrees, axis, pivot)` | reposition geometry |

## materials
`materials.get(preset, color="#rrggbb", name=None, **overrides)`; overrides: `metallic`, `roughness`, `alpha`, `coat`, `emission_strength`.
Presets: abs_matte, abs_satin, plastic_glossy, plastic_textured, plastic_frosted, silicone, rubber, aluminum_brushed, aluminum_anodized, stainless_steel, chrome, painted_metal, cast_iron, glass_clear, glass_tinted, acrylic_smoked, fabric_mesh, leather, wood_oak, ceramic_glazed, led_lens, display_off, emissive.

## joints (moving parts are parented to the joint; rest = 0 = closed/off)

`joints.frame(joint)` returns the fixed frame that carries its pivot and axis.
When nesting joints or attaching the entire mechanism, parent this frame, never
the animated joint handle. The checker reports `joint_hierarchy` if detached.

```python
hinge = joints.hinge(lid, pivot, "-X")
lift = joints.slider(joints.frame(hinge), "Z", origin=pivot)
park = joints.slider(joints.frame(lift), "X", origin=pivot)
core.set_parent(joints.frame(park), hopper)
```

Animate `hinge`, `lift`, `park` in a sequence; their fixed frames stay in the
hierarchy. This preserves assembled placement and independent extraction axes.
| Call | Motion |
|---|---|
| `joints.hinge(parts, pivot, axis, limits_deg=(0, 90), name)` | rotate about a hinge line (axis signs: `animations.md`) |
| `joints.knob(parts, axis, center=None, limits_deg=(0, 300), name)` | rotate about the part's own axis |
| `joints.slider(parts, axis, limits=(0, 0.1), origin=None, name)` | straight travel |
| `joints.button(parts, press_axis, travel=0.002, name)` | press; axis points into the product |
| `joints.set_value(joint, value)` | pose a joint (testing only; `core.finish` resets) |

## anim (each call adds a named clip; same clip name = one combined clip)
| Call | Clip |
|---|---|
| `anim.open_close(joint, clip="open_lid", seconds=1.2, to=None, ease="in_out")` | rest → open limit |
| `anim.press(joint, clip=None, seconds=0.35)` | in and back |
| `anim.turn(joint, clip=None, seconds=1.0, degrees=None, loops=1)` | rotate / spin |
| `anim.glow_part(name, light_part, material)` → glow | emissive overlay, hidden at rest |
| `anim.power(glows, clip="power_on", buttons=())` | press buttons, light glows |
| `anim.explode(clip="explode", objects=None, distance=0.35, ease="smooth")` | move top-level parts outward |
| `anim.sequence(clip, [(joint, [(seconds, value[, ease]), ...]), ...], ease="in_out")` | phased joint motion; every channel starts at `(0, 0)`, shorter channels hold their last value through the common end; a key's optional ease shapes the move arriving at it |

Use degrees for hinge/knob values and metres for sliders. Sequence times are absolute
seconds, strictly increasing by at least one scene frame. Motion is eased (see
**Easing** below); repeated values create holds. Give a joint one key list per clip. Use a parent slider
for a second extraction axis; do not replace a hinge's channel with a translation.
Animation timing uses the scene's FPS. Clips start from rest and play backwards to undo.

Material calls cache the complete specification, including opacity and roughness
overrides. Reusing an explicit `name` with a different specification raises an error;
choose a separate name for a separate finish.

## Skeleton

```python
import os, sys
SKILL_DIR = "/path/to/mechanical-explorer-test"
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
from c3d import anim, core, joints, materials, shapes
OUT = os.path.abspath(core.args().get("out", "model.blend"))
core.reset_scene(product_size=(W, D, H)); G = core.gap()
body = core.part(shapes.rounded_box("body", (W, D, H), 0.01, center=(0, 0, H / 2)), "body",
                 material=materials.get("abs_satin", color="#e9e9e6"))
core.smooth(body)
# ... parts, joints, anim clips ...
anim.explode()
core.finish(OUT)
```

`examples/mini-oven/build.py` is a complete worked example (read it once if you need a pattern).

## Easing

Motion between keys uses a named curve from `anim.EASES` (glows and holds stay instant/linear):

| ease | feel | use for |
|---|---|---|
| `in_out` (default) | gentle start and stop | most hinges, slides, knobs |
| `smooth` | stronger acceleration, long soft landing | large parts travelling far, explode |
| `out` | quick start, soft stop | dropping/lowering into place, releasing |
| `in` | soft start, firm stop | pushing until something latches |
| `settle` | ~10% overshoot, then settles | lids, doors, snapping clips with room to swing |
| `linear` | constant speed | continuous spinning, conveyors, indicators |

Set it per call (`ease=`), per sequence key (`(1.0, 90, "settle")`) or per guide step
(`ease="out"`, or a dict `{joint: ease}` for different targets in one step). `turn` uses
`linear` for `loops > 1`. Never use `settle` where an overshoot would hit another part.

## Continuous manual guides

`g = anim.guide(clip="how_to_use", title="How to use", initial_state="assembled_off", initial=None)`
creates a stateful authoring builder. `initial` optionally maps joints/glows to initial numeric values.
`g.step(id, instruction, targets={joint: value, glow: 1}, seconds=1, hold=.5,
 evidence=[{"source":"manual.pdf", "locator":"PDF page 8, lid figure"}], pause_after=False, ease="in_out")`
appends an ordered chapter. Use degrees/metres for joints, 0/1 for glow intensity/visibility.
Targets not changed in the next step retain their values; a caption-only step uses no targets.
`g.finish()` writes the continuous clip and chapter metadata. Do not author another preset
on the same target/clip. The source/locator must be checked against the provided evidence.
Read `manual-guides.md`; retain all viewer assets and licenses copied by the exporter alongside the manifest.

## Directed cameras

`Guide.step(..., camera=None, lead=None)` adds a stationary camera lead-in without shortening the action. `anim.camera_clip(clip, camera, lead=None)` finalizes an independent clip after all its channels are authored. See [manual-camera.md](manual-camera.md) for supported fields, timing, packaging and visibility review.
