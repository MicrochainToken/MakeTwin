# Linked mechanisms

Use a mechanism equation to produce rigid poses, then bake those poses. Keep geometry construction, mechanism state, physical poses and camera presentation distinct. Use consistent metres/radians in equations, and record the mapping to Blender coordinates.

## Planar helper API

`from c3d import mechanism` works without Blender for math checks.

`mechanism.slider_point(pin, axis_angle, rod_length)` intersects a cylinder axis through the origin with a circle around the rod's big end. It returns the outward slider solution. Invalid/unreachable geometry raises `ValueError` rather than stretching a rod.

`mechanism.radial_state(theta, crank_radius, master_length, link_length, cylinders=7, hub_radius=0.0, master_axis=0.0)` returns `crank_pin`, `master_angle`, and a `cylinders` list. Angles are radians and distances are metres. Each cylinder record gives `axis`, `big_end`, `piston`, `rod_angle`, `rod_length`. Cylinder zero is the master rod. Each other big-end pin sits on a circle of `hub_radius` attached rigidly to the master rod, and its piston is solved from a fixed-length articulated rod. The pin angles are an evenly spaced generic example; **this does not certify the manufacturer's actual pin layout**. Supply a more specific solver if the evidence differs. `link_length` is not the master length when a nonzero hub radius is used.

Compare piston-axis residual, fixed rod length and rigid hub pin locations across the full cycle. Check 0 and 2π return the same pose. Firing phases and valve timing are separate from geometric closure. Do not infer all timing from cylinder spacing or use fictional measurements as sourced values.

A convenient engine-plane mapping is `(x, y)` from this solver to Blender `(x, 0, y)`, plus an assembly translation. A planar rod angle then corresponds to rotation about **negative Blender Y** when the rod mesh points along local +X. Record a different mapping explicitly; do not mix world coordinates with a rotated parent frame.

## Baking local rigid poses in Blender

`mechanism.bake_transform(handle, clip, samples)` takes `(frame, location_xyz, quaternion_wxyz)` samples starting at frame zero, in the handle's local parent coordinates. Use a stable attachment/pivot Empty, with its visible parts parented underneath, rather than rotating a rod mesh around its geometric centre. One transform action is produced per handle/clip. The first sample must match the attachment rest pose. After baking, frame zero is evaluated and the track remains evaluable; renderers/exporters isolate named tracks. All independent clips must share their declared rest pose. Quaternion signs are made continuous; sample rotation frequently enough to avoid a shortest-path shortcut. Baking uses linear interpolation between solved samples, so verify intermediate poses and tighten sampling if interpolation introduces visible closure error.

Example pattern (not a product model):

```python
from c3d import mechanism
states = [mechanism.radial_state(a, r, master_L, link_L, hub_radius=h)
          for a in angles]
# Derive each attachment frame from those shared states and call bake_transform.
# Do not feed independent approximations to the piston and rod.
```

Only include mechanism parameters/readouts in a public exhibit when they are sourced or explicitly identified as illustrative. Do not turn a geometry demonstration into an implied thermodynamic, flight or durability simulation.

## Optional cycle display

In build.py, set `bpy.context.scene["c3d_mechanism"] = json.dumps({"cycleClip": "run_cycle", "cycleDegrees": 720})` only if that clip really represents a 720-degree crank cycle. The viewer derives angle from the clip time after removing its declared camera lead-in. Other guides show no crank-angle reading rather than invented telemetry. UI geometry remains in the GLB; this metadata supplies no mechanism simulation by itself.

## Optional product-specific metric

Prefer `c3d_metrics` for new products. Set this Blender scene property to a JSON list;
the exporter writes it to the manifest as `metrics`. Use an empty list to explicitly
suppress all metrics, including the legacy cycle-angle fallback. Omit it if no metric
is meaningful and do not add engine metadata to non-engine products.

Example for a drawer clip whose actual motion is linear from 0 to 120 mm over
seconds 2–4, holds until second 5, then returns by second 7:

```python
bpy.context.scene["c3d_metrics"] = json.dumps([{
    "label": "Drawer extension", "unit": "mm", "clip": "open_drawer",
    "precision": 0,
    "samples": [[0, 0], [2, 0], [4, 120], [5, 120], [7, 0]]
}])
```

Each sample is `[absolute_clip_seconds, value]`, including any camera lead-in.
Times must be finite, nonnegative and strictly increasing; values must be finite.
Provide at least two samples. The viewer linearly interpolates and holds endpoint
values outside the sampled interval. Derive samples from the same joint/solver
state used to animate the model. Sample eased or nonlinear movement densely enough
to match the displayed precision; never assume every clip is a linear ramp. Include
return strokes and holds. Review seek/reverse playback against the corresponding
poses. Units and label must describe the modeled quantity, not inferred telemetry.

The first valid metric matching the active clip is displayed. Missing, malformed,
or unrelated metrics are hidden; inspection mode also hides the metric because its
display offsets are independent of mechanism playback. No extra metric is required.
Door angle (degrees), drawer extension (mm), or a slider position (%) can be useful.
Temperature, pressure, power and RPM must not be invented from animation speed.
Legacy `c3d_mechanism` cycle metadata remains supported as “Crank angle”.
