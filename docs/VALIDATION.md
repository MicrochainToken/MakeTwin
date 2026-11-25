# Validation status — v1.0.1 release candidate

The deliverable is a named-part Blender/glTF model plus parts.json with functions,
evidence, assemblies, interfaces, attachments and supported movement. The viewer
demonstrates those assets. Approximate internals must be labeled; metadata/schema
checks do not certify physical or manufacturer accuracy.

The synthetic mini-oven has no product photos or manual. Its smoke command builds,
checks and exports the model and validates bundled part/take-apart metadata.
The bundled engine preview and docs/demo.gif are separate illustrative generated
assets; the engine manifest remains partial. See [provenance](../PROVENANCE.md).

## Release checks

Local release checks on 2026-11-25 used Python 3.11.2, Pillow 13.0.0, Node.js
22.23.5, Blender 4.2.23 LTS and Chromium 159.0.8154.6 (Playwright 1.65.1).
Blender's official Linux x86-64 build ran through Rosetta on an ARM Linux host;
this is not a native Linux or Windows version matrix.

- Clean venv/requirements installation and `doctor.py --smoke`: passed.
- Synthetic oven: 0 geometry errors, 0 warnings; 13 physical parts plus one
  illustrative indicator overlay. All 14 exported IDs pass part and take-apart
  validation. The export contains seven animation clips.
- `bash tests/run_tests.sh`: passed all Blender regression fixtures, camera
  build/check/export/render coverage, 48 Python tests with no skips, and all five
  Node suites. The camera fixture uses CPU Cycles to avoid software EEVEE overhead.
- Chromium: model.glb, manifest and explorer.json load successfully; no page or
  console errors or failed resource requests. Authored separation at 0, .25, .5,
  .75 and 1, selection/isolation/section, playback reset and mobile navigation
  are exercised. Desktop and 390-pixel mobile screenshots were reviewed.
- Release packaging: stable install root, VERSION, complete preview, required
  licenses, file hashes and README/SKILL relative links checked after extraction.

The normal GitHub unit job runs only the non-Blender subset. A separate
Blender/browser workflow (`.github/workflows/integration.yml` in a Git checkout) covers integration
checks and retains logs/screenshots; its hosted execution has not been claimed
from these local results. The release handoff retains local logs and screenshots
outside the source tree.

## Scope and limitations

Normal export preserves joint hierarchy. Fast transform export flattens rigid
mesh-node transforms; physical hierarchy stays in Blender and logical assemblies
in parts.json. It does not export mesh deformation/skinning. The checker caches
rigid BVHs and uses an AABB broad phase while retaining its collision tests and
authored samples. Sampled collision checks can miss containment and collisions
between samples; passing them is not continuous-clearance certification.

The 1.0.0 notes reported an older local 448-part comparison (1,321 errors, 58
warnings; 425.484 versus 90.950 seconds). The original benchmark artifacts are
not bundled, so those figures are historical context, not reproduced 1.0.1
release evidence. The executable collision-cache fixtures are part of the suite.

Geometry/motion checks, semantic coverage, display-layout validation and browser
interaction must be reported separately. The delivery checker validates revision
and render/export consistency; run validate_parts.py and audit_explosion.py as
well. Human fidelity and evidence review remain required. Native Windows and
other unlisted platform/version combinations are not certified by these checks.
