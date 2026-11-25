# Working from photos, manuals and descriptions

## Get the size right first

Wrong proportions ruin a model more than anything else, and they are the hardest thing to fix late.

1. **Use stated dimensions** (manual, spec sheet, product page) when available. Note which dimension is which. Manuals often give W × D × H including handles and feet.
2. Otherwise, **scale from a known object** in the photo: a standard power plug (UK 50 mm wide, EU Schuko 36 mm diameter, US 2-pin face about 30 × 20 mm), a USB-A port (12 mm), a USB-C port (8.3 mm), an M4 screw head (7 mm), an adult hand (about 85 mm wide across the palm), a credit card (85.6 × 54 mm), an A4 sheet.
3. Otherwise, use **typical sizes for the category** (a 20 L microwave is about 480 × 360 × 280 mm) and mark it as an estimate.
4. Measure **ratios** in the photos with straight-on views: width/height, door width/total width, button spacing. Ratios from a photo are more reliable than absolute sizes.

Write all sizes and their source in `PLAN.md`.

## Read the photos properly

- **Perspective:** wide-angle phone photos exaggerate the near side. Take proportions from the most straight-on photo, and measure the distant face in a different photo.
- **Hidden sides:** if there is no photo of the back or bottom, keep them simple and plausible (vents, feet, label recess), and say so.
- **Colour:** see `materials.md`.
- **Parts:** look for seams (dark lines), different colours or finishes, screws, and parts that would be removed for cleaning. Each is a likely separate part.

## Manuals

- Exploded diagrams list the parts and how they come apart. Use them for the part list and for the `explode` clip's direction.
- Part names in the manual make good labels (`c3d_label`).
- Assembly steps tell you which parts move and how (slide in, clip on, turn to lock).

## Short descriptions only

When the user gives only a description ("a retro toaster with two slots"):

1. Pick a typical real product of that kind and use its usual proportions and parts.
2. Include the standard interactive parts for the category (toaster: lever, browning dial, crumb tray, slots) with their clips.
3. Say what you assumed, in one short list, when you deliver.

## Proportion check (do this after the first build)

Render `front` and `right` with `render_views.py` and compare them with the straight-on photos at the same scale:

- overall aspect ratio within about 3 %;
- position of the main features (door edge, control panel, display) within about 5 % of the width;
- silhouette: the same corners are rounded, the same faces slope.

Fix proportions before adding any further detail.


## Product dimensions versus scene bounds

A power adapter, detached tray or cable staged next to the product enlarges the scene
bounding box. Do not compare that envelope to the manual's assembled-product dimensions.
Record the main assembly's dimensions separately from accessory sizes and the overall
scene envelope. `core.product_bbox([body, hopper, lid])` accepts an explicit object list;
include the required assembled parts rather than loose staged accessories. Exported
`size_m` describes all registered non-glow meshes unless explicitly documented otherwise.
