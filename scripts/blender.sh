#!/usr/bin/env bash
# Runs Blender with the given arguments. Set BLENDER=/path/to/blender to override.
# Output is quiet by default: the full log goes to $C3D_LOG_DIR (default ./.c3d-logs) and only
# [c3d] summary lines and errors are printed. Set C3D_VERBOSE=1 to see everything.
set -euo pipefail
# Inside an agent sandbox where Blender cannot start (macOS seatbelt), an external launcher may start a
# broker and set C3D_BROKER_DIR: hand the request to it and wait for the result.
if [ -n "${C3D_BROKER_DIR:-}" ] && [ -z "${C3D_IN_BROKER:-}" ]; then
  id="$(date +%s)-$$-$RANDOM"
  python3 - "$C3D_BROKER_DIR/req-$id.json" "$PWD" "$@" <<'PY'
import json, os, sys
path, cwd, argv = sys.argv[1], sys.argv[2], sys.argv[3:]
tmp = path + ".tmp"
with open(tmp, "w") as fh:
    json.dump({"cwd": cwd, "argv": argv}, fh)
os.rename(tmp, path)
PY
  for _ in $(seq 1 14400); do
    if [ -f "$C3D_BROKER_DIR/res-$id.code" ]; then
      cat "$C3D_BROKER_DIR/res-$id.out"
      exit "$(cat "$C3D_BROKER_DIR/res-$id.code")"
    fi
    sleep 0.25
  done
  echo "[c3d] Blender broker did not answer within an hour" >&2
  exit 124
fi
find_blender() {
  if [ -n "${BLENDER:-}" ] && [ -x "$BLENDER" ]; then echo "$BLENDER"; return; fi
  if command -v blender >/dev/null 2>&1; then command -v blender; return; fi
  for p in \
    "/Applications/Blender.app/Contents/MacOS/Blender" \
    "$HOME/Applications/Blender.app/Contents/MacOS/Blender" \
    "/snap/bin/blender" "/usr/bin/blender" "/usr/local/bin/blender" \
    "/c/Program Files/Blender Foundation/Blender/blender.exe"; do
    if [ -x "$p" ]; then echo "$p"; return; fi
  done
  for p in "/c/Program Files/Blender Foundation"/Blender*/blender.exe; do
    if [ -x "$p" ]; then echo "$p"; return; fi
  done
  echo "Blender not found. Install Blender 4.2+ or set BLENDER=/path/to/blender" >&2
  exit 127
}
B="$(find_blender)"
case " $* " in *" --version "*|*" -v "*) exec "$B" --version ;; esac
if [ "${C3D_VERBOSE:-0}" = "1" ]; then exec "$B" --factory-startup --python-exit-code 1 "$@"; fi
LOG_DIR="${C3D_LOG_DIR:-$PWD/.c3d-logs}"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/blender-$(date +%Y%m%d-%H%M%S)-$$.log"
set +e
"$B" --factory-startup --python-exit-code 1 "$@" >"$LOG" 2>&1
code=$?
grep -E '^\[c3d\]|Traceback|^  File "|^[A-Za-z]*Error|Exception:' "$LOG" | grep -vE 'EGL Error|DeprecationWarning' | head -40
if [ "$code" -ne 0 ]; then
  echo "[c3d] blender exited with code $code; last lines of $LOG:"
  tail -12 "$LOG"
fi
exit "$code"
