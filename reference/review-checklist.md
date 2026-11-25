# Review checklist

Use it after every render pass (`renders/views.png` and `renders/clip-*.png`), comparing side by side with the reference photos. Write findings in `REVIEW.md` as **important** (anyone would notice), **minor** (only a close look shows it) or **ok**. Fix important findings first, largest first.

## 1. Proportions and silhouette (most important)
- [ ] Overall width : depth : height matches the photos.
- [ ] Main features sit in the right place (door edge, control panel, display, handle).
- [ ] The outline in front and side views matches: which corners are rounded, which faces slope or curve.
- [ ] Nothing is missing that is visible in the photos at normal viewing distance.

## 2. Parts and construction
- [ ] Every separate real part is a separate object, and the seams between them are visible as thin gaps.
- [ ] Edges are rounded like the real product (no knife-sharp 90° edges).
- [ ] Curved surfaces look smooth at the closest view: no facets on round knobs, handles or bodies.
- [ ] No flicker or stripes where two surfaces meet (`zfight` is clean).
- [ ] Details have depth: vents are cut in, buttons stand proud, screens sit behind glass.

## 3. Materials
- [ ] Each part's colour and gloss matches the photo (see `materials.md`).
- [ ] Metal parts look metallic, plastic does not.
- [ ] Glass shows what is behind it.
- [ ] No pure-black or pure-white surfaces, no mirror-perfect plastic.

## 4. Motion (per clip sheet: chronological phases and midpoints)
- [ ] Each part moves about the right pivot: a hinged door stays attached at its hinge edge.
- [ ] Direction is right (doors open outwards, buttons go in).
- [ ] The end pose is believable (door opening angle, drawer travel).
- [ ] Nothing passes through anything (`motion_collision` is clean).
- [ ] Lights visibly change in `power_on`.
- [ ] Prerequisites are inside the same clip and remain held while later steps move.
- [ ] Enclosed parts exit through an opening before moving sideways; fixed details ride with their parent.
- [ ] `explode` has been checked too; all exported clips have actual sheet files.

## 5. Delivery
- [ ] `check_model.py`: 0 errors; every warning fixed or explained in `PLAN.md`.
- [ ] GLB opens in `templates/viewer/index.html` and every clip plays and reverses.
- [ ] Assumptions and known limitations are listed for the user.
- [ ] Optional parts are registered and included, or genuinely omitted from the export; zero scale is not an omission.

## Common problems and fixes

| You see | Likely cause | Fix |
|---|---|---|
| Model looks like a toy | sharp edges, uniform colours | bevel everything; add seams and two-tone finishes |
| Looks like plastic when it should be metal | metallic 0 or high roughness | metal preset, roughness 0.2–0.4 |
| Stripes or flicker on a face | coplanar surfaces | `core.gap()` offset |
| Round part looks polygonal | too few segments or flat shading | more segments, `core.smooth` |
| Door detaches when opening | pivot not on the hinge line | move the pivot to the fixed edge |
| Door swings into the body | axis sign wrong | flip the axis (see `animations.md`) |
| Glass looks like a grey sheet | nothing behind it, or it is opaque | cut an opening behind it; use the glass preset |
