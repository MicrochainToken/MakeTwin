# Curved surfaces

Most "AI-made" 3D models look fake for two reasons: hard 90° edges everywhere, and curved surfaces made from too few flat facets. Both are easy to avoid if you choose the right construction for each shape.

## Pick the construction from the shape

| The real shape | Build it with | Examples |
|---|---|---|
| Box-like with rounded edges | `shapes.rounded_box` (radius 0.5–3 mm for metal and sharp plastic, 3–15 mm for moulded consumer plastic) | appliance bodies, cases, panels |
| Flat panel with rounded corners and straight walls | `shapes.rounded_slab` | glass, displays, buttons, doors, recess cutters |
| Round in plan, profile changes with height | `shapes.lathe` with a profile of (radius, height) points | knobs, bottles, cups, plates, lamp bases, feet |
| Constant section that follows a path | `shapes.sweep` | handles, cables, tube frames, chair legs, rims |
| Section changes shape along its length | `shapes.loft` of `section_rounded_rect` / `section_superellipse` loops | kettles, computer mice, shells, car-like bodies |
| Free-form, organic | `shapes.subdivided` from a coarse cage | ergonomic seats, backrests, grips |
| Flat outline with thickness | `shapes.extrude_outline` | brackets, plates, logos, gaskets |
| Holes, slots, recesses, vents | `shapes.boolean` / `shapes.cut_many` with rounded cutters | vents, ports, screen recesses |

Never approximate a curve by stacking or rotating many boxes.

## Resolution

Curves need enough segments that the silhouette looks round **at the closest camera distance**:

- around a full circle: 64 segments for parts under 5 cm, 96–128 for larger visible round parts, 24–32 for tiny parts (screws, LEDs);
- each 90° fillet: 4 segments for small radii, 6–8 for large visible ones;
- lathe profiles: add points where the curvature changes; repeat a point to keep a deliberate crease.

The checker's `faceted` warning means many adjacent faces meet at 8–40° and are shaded flat: add segments, subdivide, or shade smooth.

## Shading

Call `core.smooth(obj)` on every part. It shades curved faces smoothly and keeps edges sharper than 35° crisp. Use a lower angle (20–25°) for very precise machined parts, and a higher one (45–60°) for soft organic shapes.

## Free-form parts (subdivision)

For organic parts, model a **coarse cage** (8–60 points) that captures the overall shape, then subdivide 2 levels:

1. Start from the part's bounding box in the photos.
2. Place cage points on the silhouette in front, side and top views.
3. Use `creases={(i, j): 1.0}` for edges that must stay sharp (a seat's front lip).
4. Render, compare the silhouette with the photos, and move cage points; do not add detail before the silhouette matches.

For an ergonomic chair, keep seat shell, cushion/mesh, back frame, lumbar support,
armrests, gas lift, base and casters as real separate parts. A rounded box for the
seat or back is only an early size blockout. Capture the seat pan's bowl, front-edge
roll, side taper and backrest's lumbar/S-curve in separate front/side/top profiles.
Use shared, evenly ordered section loops for a loft or a quad cage with support
loops at the perimeter. Check both outer silhouette and interior concavity;
subdivision rounds a bad cage but does not infer the missing curvature.

Set a fidelity target from available evidence: e.g. a stated outline tolerance in
matched orthographic views, plus close-up inspection for pinching and thickness.
Do not compare a perspective photo to an orthographic render as a dimensional
measurement. With only one view, label unseen curvature as inferred and avoid
claiming a measured reconstruction. Add shell thickness after the surface shape is
stable; inspect the lip and underside for self-intersections. Preserve a continuous
surface under fabric rather than using floating strips to imitate upholstery.

Use a solid material override during silhouette/curvature review so reflections
and transparency cannot conceal dents. Review the actual finish afterward. This
is a construction strategy; the supplied oven and motion tests do not establish
chair reconstruction quality. Evaluate the finish against supported source photos after a
trial.

## Booleans

- Use rounded cutters (`rounded_slab`, `rounded_box`) so cut edges are not knife-sharp, or call `shapes.bevel(obj, width)` afterwards.
- Overshoot every cutter by at least `core.gap()` beyond the surface it passes through.
- Use `shapes.cut_many` for sequential exact cuts. Joining overlapping cutters only concatenates their surfaces; it does not form a clean union. Inspect topology after cuts.
- A boolean result is n-gons: fine for rendering, but do booleans **before** smoothing, and check `open_mesh` afterwards.

## Thin parts

Real sheets have thickness. Give open surfaces a wall with `shapes.shell(obj, thickness)` (0.8–3 mm for plastic shells, 0.5–1.5 mm for sheet metal). Zero-thickness planes render as one-sided and break the checks.
