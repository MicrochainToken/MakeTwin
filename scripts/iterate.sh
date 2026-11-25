#!/usr/bin/env bash
# One build round in one command: build.py -> model.blend -> checks.json -> renders/.
#   scripts/iterate.sh PROJECT_DIR [--clips none|all|a,b] [--size 320] [--no-render]
# Prints only summaries. Use this instead of running the three steps separately.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
P="$(cd "${1:?usage: iterate.sh PROJECT_DIR [--clips ...] [--size N] [--no-render]}" && pwd)"; shift
CLIPS=none; SIZE=320; RENDER=1
while [ $# -gt 0 ]; do
  case "$1" in
    --clips) CLIPS="$2"; shift 2 ;;
    --size) SIZE="$2"; shift 2 ;;
    --no-render) RENDER=0; shift ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
done
cd "$P"
echo "== build"
"$HERE/blender.sh" -b --python build.py -- --out model.blend || { echo "[c3d] build failed; fix build.py"; exit 1; }
echo "== check"
"$HERE/blender.sh" -b model.blend --python "$HERE/check_model.py" -- --report checks.json
check=$?
if [ "$RENDER" = 1 ]; then
  echo "== render ($SIZE px, clips: $CLIPS)"
  "$HERE/blender.sh" -b model.blend --python "$HERE/render_views.py" -- --out renders --size "$SIZE" --clips "$CLIPS"
  render=$?
  if [ "$render" -ne 0 ]; then
    echo "[c3d] render failed"
    if [ "$check" -eq 0 ]; then check=$render; fi
  fi
fi
exit $check
