# Photo intake routes

## Route 1: Guided photo taking

### Review the manual first

Ask for the manual file or accessible link and the product model if not already supplied. Read the relevant pages and diagrams before prescribing product-specific shots. Confirm the manual matches the product; distinguish variants and optional accessories. Extract dimensions, component names, user-removable parts, assembly steps, controls, and the motions needed for the requested model or walkthrough. Record actual page/figure references; never invent citations or infer that an illustrated service part is user-removable.

If the manual is unavailable or unreadable, explain what is missing and offer to use existing photos instead. Do not silently claim to have completed manual review. Reuse any photos already supplied to avoid requesting duplicate views.

### Give the user a tailored checklist

Write `PHOTO_GUIDE.md` in the project folder and present the checklist in chat. For each shot include a short ID, the exact part name/product state, camera angle, what must be visible, and the relevant manual page/figure where applicable. The description of the shot must be precise and accurate, no vague descriptions. Separate essential shots for the requested scope from optional detail shots. Do not request for multiple angles in one shot and do not request for a ruler or reference object to be placed in any image. 

Choose the smallest useful set for this product:

- Assembled front, back, sides and top as needed to establish shape and proportions; include a three-quarter view for depth.
- Close-ups of important seams, controls, material transitions and attachment points.
- For requested motions, closed/open states and a useful intermediate position showing the hinge or sliding path.
- For removable parts documented for user removal, the part and its receiving cavity, including mating surfaces and orientation.

Use the manual's preparation and removal instructions. Do not request opening sealed housings or exposing powered internals for photos. If a view cannot be obtained safely, mark it unavailable. Do not request unsafe access to fill evidence gaps; any internal approximation remains subject to the Explorer skill’s observed/inferred/illustrative labeling policy.

Give brief capture guidance: diffuse light, plain background, sharp focus, whole part in frame, and straight-on shots taken from sufficient distance to reduce perspective distortion. Suggest filenames matching the shot IDs, but accept uploads with any names.

**Wait for the photo upload.** This stage delivers guidance, not geometry. Do not start `build.py`, Blender generation, or an unattended model run while waiting. The user can switch to existing photos at any time.

### Review the uploaded photos

Inspect the upload (contact sheets where useful), map files to checklist IDs and identify which essential features are covered. Request only specific missing or unreadable views that materially affect the requested geometry or motion. If the user cannot provide them or asks to proceed, record the uncertainty and use a simplified or estimated representation; do not repeat the whole checklist. Once sufficient evidence is available, continue to planning and generation without an extra approval ceremony when generation was already requested. A request only for photo guidance does not itself request generation.

## Route 2: Use existing photos

Accept the user's available photos without requiring a manual, prescribed angles, filenames or a minimum count. Inspect them first, then use any supplied manual or dimensions to supplement the evidence. Do not turn this route into mandatory guided photography.

Summarize what is supported and the important gaps: unseen sides, uncertain size, unclear joints, hidden interfaces or ambiguous product variants. Proceed with reasonable assumptions and clearly label estimates. Ask a focused question only when ambiguity would make the requested build unusable; otherwise, additional photos are optional. If no images arrived, ask for the intended upload or use the description-only workflow if that is what the user requests.

Without a manual, do not invent manual citations or present inferred actions as manufacturer instructions. Record unsupported walkthrough steps as unknown and adapt the scope to the available evidence.

## Handoff to the shared workflow

In `PLAN.md`, record the chosen route, manual identity/page references when present, photo filenames and covered parts/states, dimensions and sources, plus unresolved assumptions or omitted details. Apply the same build, check, render, repair and delivery rules for both routes.

Complete guided intake interactively before modeling starts. For existing-photo runs, supply the available images and include relevant evidence gaps in the run notes.
