# Z-fighting, gaps and contacts

## What goes wrong

**Z-fighting** is the flicker or stripe pattern when two surfaces sit in the same plane. The graphics card cannot decide which one is in front, so they swap from pixel to pixel and from frame to frame. In a web viewer it gets worse as the camera moves away, because depth precision drops with distance.

Typical causes in product models:

| Cause | Example | Fix |
|---|---|---|
| Detail placed exactly on a surface | logo plate, label, display glass with its back on the housing face | raise it by `core.gap()` or recess it into the surface |
| Two parts that meet flush | door front flush with body front, lid sitting on rim | real products have a **panel gap** (0.5–2 mm); model it |
| Duplicate geometry | the same part built twice, or a boolean that left a copy | the checker reports `zfight` *inside* one part |
| Boolean cutter ends exactly at a face | cutter for a recess stops at the surface | make every cutter overshoot by ≥ `core.gap()` |
| Emissive overlay on an indicator | glow mesh exactly on the lens | `anim.glow_part` already grows it by `core.gap()` |

## The gap rule

`core.gap()` = max(0.3 mm, 0.08 % of the product's largest dimension). That is 0.4 mm for a 0.5 m microwave and 1.6 mm for a 2 m wardrobe. Use it:

- between separate parts that face each other (door/body, panel/body, drawer/carcass);
- as the minimum step for details that should look flush (a label that is "on" the surface is 1 gap proud);
- for clearance around anything that moves (buttons in pockets need gap × 3 on every side).

Real products show their seams. A visible 1 mm dark line between door and body makes a render look **more** real, not less.

## Contacts that are intended

Some parts genuinely overlap: a handle's legs screwed into a door, a shaft inside a bearing, a fabric cover over foam. Declare them, so the check knows it is deliberate:

```python
core.allow_contact(handle, door, "handle ends are screwed into the door")
```

This allows the contact at rest and while the parts keep their relative placement
(for example, a handle fixed to an opening door). It does **not** excuse subsequent
relative movement through the housing. For a genuinely fitted sliding/rotating
interface represented approximately, name the particular clips:

```python
core.allow_contact(shaft, bearing, "shaft rotates inside the bearing bore",
                   motion_clips=["spin_shaft"])
```

This is a manual exemption for that pair/clip, not measured clearance. The reason
must describe the interface and evidence; list it in `REVIEW.md`. Never use it to
silence a bowl through a body, a lid through a hopper, or a button without a pocket.
Use an actual receiving hole wherever practical. Existing declarations without
`motion_clips` now have the stricter rest/rigid meaning. Invalid part/clip references
are check errors. No contact declaration suppresses z-fighting.

## Things that look like contacts but are not

- **Coincident faces facing opposite ways** (two boxes touching face to face) are hidden from the outside and do not flicker. The checker only reports same-direction faces as z-fighting. They still count as `overlap` if the triangles cross.
- **Parts inside parts** (a PCB inside a housing) are fine as long as no surfaces cross. Hidden internals are usually not worth modelling for a visual model; leave them out unless an animation reveals them.

## Clearance for motion

`check_model.py` samples every clip, including `explode`, and reports
`motion_collision` when a moving part's surface crosses another. Uniform samples,
authored keys and phase midpoints are inspected. Rest overlaps are reported at rest
and are no longer silently ignored during motion. Usual fixes, in order:

1. Pivot in the wrong place: a hinge sits on the **edge** that does not move, on the side the door opens towards.
2. Missing clearance: the door's back edge sweeps through the frame. Increase the gap on the hinge side or round the door edge more.
3. Range too large: a lid that really stops at 95° should not open 120°.
4. Wrong order or hierarchy: open/release the obstructing part first, hold it there,
   then extract along the opening. Use `anim.sequence`; do not move a parent that
   also carries a previously detached part.

The coplanar check samples face centres and inset corners. Very narrow/crossing
patches can still escape those probes. Crossing-triangle tests also miss a solid
wholly inside another solid without a surface crossing, and discrete motion samples
can miss brief collisions. Inspect section/cavity construction and critical swept
paths; passing this script is not a proof of mechanical clearance.
