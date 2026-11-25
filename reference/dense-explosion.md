# Dense exploded exhibits

Use when the user requests an impressive all-component exploded view and allows approximate hidden construction. This mode emphasizes visual richness while keeping observed, inferred and illustrative geometry distinct. It does not assert manufacturer part counts or service order.

## Parts that justify their presence

Choose detail according to the product and references; there is no mandatory component count. An existing detailed engine baseline may already contain several hundred useful parts; refine their coherence and usability instead of multiplying them. Repeated genuine hardware counts separately. Empty nodes, faces, disconnected mesh islands, decorative particles and duplicate coincident objects do not count. Keep cast cooling fins attached to their casting rather than inflating the count by detaching fins. Do not pad the scene with arbitrary gears or hardware.

Plan families and generate them parametrically: casings and covers; cylinder barrels, liners and heads; pistons, rings, wrist pins and retainers; rods, bushings and thrust washers; crankshaft and bearings; cams, followers, pushrods, rockers, valves, seats, guides, springs and spring retainers; intake/exhaust connectors and gaskets; studs, nuts, washers and screws. Adapt to this mechanism. Include only plausible components; approximate unseen construction freely where allowed. Prioritize silhouettes, hollow sleeves, ring profiles, spring coils and metallic material variation over costly threads and booleans.

Separate rigid components with meaningful interfaces. Maintain the recognizable exterior and coherent shared-state main mechanism. Added illustrative parts can remain static at assembled rest when their real motion is unknown. Save an early buildable baseline before multiplication. Never conceal inherited checker failures or call unchecked geometry engineering-valid.

## Every modeled component separates

The current schema supports one group per part without viewer changes. Create a distinct group with parts:[part_id] for EVERY exported part, including the crankcase. Physical parenting and display grouping serve different purposes. No unassigned parts, zero offsets, or groups that move a complete cylinder as one block. Use stable semantic IDs and concise readable labels.

Use a deterministic hierarchy of lanes: expand the seven cylinder stations radially, distribute each station's components along its own axis and slightly fan small hardware tangentially, and spread front/rear drive components in axial layers. Give adjacent rings, washers, bolts and springs different final offsets. Keep each family's original order visible and leave the center recognizable. Avoid a random spherical cloud and avoid co-locating all hardware at one endpoint. Fit both the complete layout and a selected cylinder in the viewport.

Stage outer hardware/covers at slider 0–0.3, cylinder/head/valvetrain layers at 0.2–0.65, piston/rod/crank and bearings at 0.45–0.9, and fine internal stacks at 0.65–1.0; overlap stages for continuous motion. These are illustrative display offsets, not validated extraction paths. All transforms must restore exactly at slider zero and before playback.

## Presentation and verification

Show the assembled hero, a gradual complete explosion held long enough to inspect, one cylinder's internal stack, the central crank/rod assembly, and reverse reassembly. Keep the existing interactive viewer and guide controls. A baked guide explosion is optional: when supplied, label it a display layout and keep it separate from physical run_cycle tracks/check claims. Review the actual browser slider at 0, .25, .5, .75 and 1, then reset and replay. Save screenshots and report which poses were inspected; do not claim browser review from Blender frames alone.

After export run scripts/audit_explosion.py --manifest model.manifest.json --explorer explorer.json --minimum 1 --out explosion-audit.json. This verifies count, exact coverage and per-part nonzero offsets; it does not prove visual spacing, collision freedom or CAD accuracy. Report modeled part count, moving part count, display-group count, evidence limits and remaining technical failures separately. Report the actual count. The meaningful decomposition, function metadata and visual coherence decide quality; a high count alone does not.
