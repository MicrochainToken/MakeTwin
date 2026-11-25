#!/usr/bin/env bash
# Builds the example and the deliberately broken scene, then checks both.
# Pass: the example has 0 errors, and every planted defect in the broken scene is reported.
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
B="$SKILL/scripts/blender.sh"
OUT="${1:-$(mktemp -d)}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
cd "$OUT"
fail=0
if ! "$B" --version >blender-version.log 2>&1; then
  cat blender-version.log
  exit 1
fi

"$B" -b --python "$SKILL/examples/mini-oven/build.py" -- --out mini-oven.blend >build.log 2>&1 || { echo "FAIL build example"; fail=1; }
if "$B" -b mini-oven.blend --python "$SKILL/scripts/check_model.py" -- --report checks.json >check.log 2>&1; then
  echo "ok   example passes checks"
else
  echo "FAIL example has check errors:"; grep "\[c3d\]" check.log; fail=1
fi
"$B" -b mini-oven.blend --python "$SKILL/scripts/export_glb.py" -- --out mini-oven.glb >export.log 2>&1 \
  && [ -s mini-oven.glb ] && echo "ok   example exports GLB" || { echo "FAIL export"; fail=1; }

"$B" -b --python "$SKILL/tests/broken_scene.py" -- --out broken.blend >broken-build.log 2>&1 || { echo "FAIL build broken scene"; fail=1; }
"$B" -b broken.blend --python "$SKILL/scripts/check_model.py" -- --report broken.json >broken.log 2>&1
for code in naming material zfight overlap motion_collision faceted inside_out pivot_far; do
  if grep -q "\"code\": \"$code\"" broken.json; then echo "ok   detects $code"; else echo "FAIL misses $code"; fail=1; fi
done
for suite in geometry_regression motion_regression boolean_solver mechanism_bake collision_cache_regression fast_export_regression; do
  if "$B" -b --python "$SKILL/tests/$suite.py" >"$suite.log" 2>&1; then
    echo "ok   $suite"
  else
    echo "FAIL $suite"; tail -50 "$suite.log"; fail=1
  fi
done
"$B" -b mechanism-baked.blend --python "$SKILL/scripts/check_model.py" -- --report mechanism-checks.json >mechanism-check.log 2>&1 \
  && "$B" -b mechanism-baked.blend --python "$SKILL/scripts/export_glb.py" -- --checks mechanism-checks.json --out mechanism-baked.glb >mechanism-export.log 2>&1 \
  && echo "ok   baked mechanism checks and exports" || { echo "FAIL baked mechanism export"; cat mechanism-check.log mechanism-export.log; fail=1; }
mkdir -p "$OUT/camera"
if "$B" -b --python "$SKILL/examples/camera-fixture/build.py" -- --out "$OUT/camera/model.blend" >camera-build.log 2>&1 \
  && "$B" -b "$OUT/camera/model.blend" --python "$SKILL/scripts/check_model.py" -- --report "$OUT/camera/checks.json" >camera-check.log 2>&1 \
  && "$B" -b "$OUT/camera/model.blend" --python "$SKILL/scripts/export_glb.py" -- --out "$OUT/camera/model.glb" >camera-export.log 2>&1 \
  && "$B" -b "$OUT/camera/model.blend" --python "$SKILL/scripts/render_views.py" -- --out "$OUT/camera/renders" --clips all --size 128 --max-frames 0 --engine cycles >camera-render.log 2>&1; then
  echo "ok   camera fixture builds, checks, exports and renders"
else
  echo "FAIL camera fixture (see camera-*.log)"; fail=1
fi
if C3D_CAMERA_FIXTURE="$OUT/camera" C3D_EXPORT_FIXTURE="$OUT" python3 -m unittest discover -s "$SKILL/tests" -p 'test_*.py' -v >python-tests.log 2>&1; then
  echo "ok   Python delivery and actual GLB export tests"
else
  echo "FAIL Python tests"; tail -60 python-tests.log; fail=1
fi
for suite in camera_math_test guide_player_test showcase_state_test explorer_state_test explorer_controller_test; do
  if node "$SKILL/tests/$suite.cjs" >"$suite.log" 2>&1; then echo "ok   $suite"; else cat "$suite.log"; fail=1; fi
done
echo "outputs in $OUT"
exit $fail
