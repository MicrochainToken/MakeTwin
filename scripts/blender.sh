#!/usr/bin/env bash
# Runs Blender with the given arguments. Set BLENDER=/path/to/blender to override.
# Output is quiet by default: the full log goes to $C3D_LOG_DIR (default ./.c3d-logs) and only
# [c3d] summary lines and errors are printed. Set C3D_VERBOSE=1 to see everything.
set -euo pipefail
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
