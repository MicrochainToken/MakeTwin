# Construction fidelity: how real products are put together

Use these construction rules while planning and reviewing a product. Derive every product-specific part, dimension and mechanism from the current supplied evidence.

## Parts that stack sit on each other

- When one part rests on another (hopper on base, lid on hopper, tray against body), the lower edge of
  the top part meets the rim of the part below with only a seam (`core.gap()`, 0.3–1 mm).
- There is no visible air gap, and there are no posts or sticks bridging one. If geometry is needed
  inside the joint (a neck, a collar), hide it inside the parts.
- Check this in the assembled rest pose from the side view, not only in `checks.json`. An air gap
  produces no check error.

## A lock or latch is always two parts

Every catch the manual or photos show has two halves, and both must be modelled:

- the moving part: latch, slider tongue, spring bolt, clip prongs;
- the part it engages: hook, lug, slot, ledge, or a pocket with a window.

Typical pairs:

- a lid latch retracts into the lid and catches a small hook on the hopper rim;
- a sliding lock has a tongue that reaches inward over a tab on the removable part;
- a tab on one part enters a pocket moulded on the other.

Animate the release in order: the latch or slider moves first, then the part opens or lifts. A slider
that reveals a colour (an orange "unlocked" strip) needs that coloured strip in the slot.

## Ask "one moulded piece?" before splitting

- Paddles and their shaft, a button and its stem, a lid and its hinge knuckles: if the photo shows them
  joined without a seam or fastener, they are one part.
- Split only where the product comes apart, or where something moves relative to something else.
- A merged part keeps the id the manual or guide uses. Update every guide step, label and camera that
  named the old parts.

## Things sit on something

- Buttons, switches, LEDs and pins sit in their own recess or hole in solid material.
- Never place one over an opening, a cable channel or another part's cavity, where it would float in
  the air.
- Thin features (ribs, webs, clip tongues) connect to the wall they grow from: a cantilever tongue is
  joined to its plate along one edge by a U-shaped slot, not cut free.

## Openings are cut, not added

- A chute, outlet or drain is a hole cut through the floor or wall, usually with a sloped surface
  leading into it.
- Do not add a free-standing tube or duct to represent it unless the photos show one.
- Funnels and hopper floors slope toward their outlet steeply enough for food or liquid to slide (often
  30–45°), so it shows clearly in the side view.

## Count and place details from close-ups

- Holes, slots, ribs and slats: count them on the close-up photo, and copy their shape (round, oval,
  curved trapezoid). Do not invent a symmetric pattern.
- Underside photos are taken with the product turned over, so left and right are mirrored. Record in
  `PLAN.md` which side each control is on as seen from the front, then place it.
- Note what a feature is next to (for example "switch, then reset, then the cable socket") and keep that
  order.
- Underneath parts are visible when the product is flipped: receiving sockets for clips and keys,
  support ribs between a curved seat and the outer wall, battery-door latch tabs in finger recesses.

## Visible shape and colour of small parts

- Clips, keys and latches have a recognisable silhouette: a forked Y, a U-loop with a centre tongue, a
  flared head.
- Small loose parts are often a contrasting colour (red keys, an orange lock indicator). Match it, and
  say so in `PLAN.md`.
