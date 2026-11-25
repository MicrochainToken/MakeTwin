# Take-apart presentation

## Why this differs from independent clips

The visitor should see a relationship: a cover clears, its assembly opens, the camera follows, and the inner mechanism becomes the next focal point. Reassemble in reverse stage order. Use the same known whole, not unrelated objects in each shot. For a standard explanation, prioritize a good whole and a few convincing mechanisms. For a requested all-component spectacle, follow dense-explosion.md and detail plausible internal component families after saving that baseline.

A staged exploded **layout** may use separation distances chosen for readability. Declare it illustrative and avoid describing it as a wrench-by-wrench service procedure. If authoring a physical extraction animation, show prerequisites and check the real swept path. Approximate internals are permitted, provided their assumptions and limits are visible.

## explorer.json contract

The viewer resolves the layout beside the selected GLB. Use `explorer.json` for `model.glb` and `name.explorer.json` for a custom `name.glb`. If the layout is unavailable or invalid for the loaded part IDs, the panel uses an automatic radial layout and explains the fallback under **About this view**. Validate the authored layout before delivery so the intended staged paths are available.

This optional project file is loaded next to model.glb. All positions are world offsets in **glTF Y-up metres**, not Blender Z-up coordinates. Convert a Blender vector (x, y, z) to (x, z, -y) for the default exporter. IDs are exact exported c3d_part values. Each part belongs to at most one display group. Unassigned parts stay fixed and remain available in the Whole machine view.

```json
{
  "schemaVersion": 1,
  "notice": "Illustrative separation; internal details include estimates.",
  "groups": [
    {"id":"cover","label":"Outer cover","parts":["cover_part"],
     "offset":[0,0.08,0],"start":0,"end":0.4,
     "evidence":"observed","note":"Appearance from photo 03; display offset is illustrative."},
    {"id":"drive","label":"Drive assembly","parts":["shaft","gear"],
     "offset":[0.06,0,0],"start":0.35,"end":1,
     "evidence":"inferred","note":"Simplified transmission; hidden topology not shown in the manual."}
  ]
}
```

`start` and `end` are normalized separation-slider positions; require 0 <= start < end <= 1. Each group uses a smooth interpolation within that interval. The assembled position is always zero offset. Group offsets do not modify baked GLB tracks or physical checker inputs. Large offsets can exaggerate component spacing; keep mounting context and fit the reveal inside the available view.

`evidence` describes modeled geometry/topology: `observed`, `inferred`, or `illustrative`. The separation itself is always a display layout unless independently verified. Unknown IDs, duplicate membership, non-finite offsets and invalid intervals are errors, not silently ignored metadata. Fix metadata when renaming a part. Missing or malformed metadata triggers the automatic layout with a visible explanation and preserves the normal guide.

## Display behavior and review

The viewer cancels physical playback, restores the scene to assembled rest, then applies offsets from that rest on every update. Selection can keep other parts translucent, isolate one group, or apply a clipping plane. Owned material copies prevent a transparent group from altering another group that shared its GLB material. Returning to the guide restores original transforms/materials first.

Section preview intentionally has no solid caps; label it that way. It can reveal the back of a hollow mesh but cannot validate wall thickness. Use Blender geometry and native clips for a shareable physical cutaway.

Review assembled, an early outer-layer reveal, half exploded, fully exploded, selected mechanism, and reset/replay. Ensure selected labels agree with metadata, all groups reset exactly, repeated slider changes do not drift, and pause/orbit remain responsive. Full model and physical-motion failures stay visible in the delivery report.

## Design purpose

Use component-level geometry, a coherent mechanism, readable staged separation and honest evidence notes to explain the user’s product. Images and manuals determine recognizable structure. Guessed internals fill gaps only when explicitly identified. The display layer never substitutes for physical model validation.

## All-component profile

For a dense exploded exhibit, read [dense-explosion.md](dense-explosion.md). Use one single-part group per exported part, including the outer body. Physical parent assemblies still govern mechanism motion; they must not collapse the display explosion into a dozen moving blocks.
