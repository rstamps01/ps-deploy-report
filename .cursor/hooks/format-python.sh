#!/bin/bash
# afterFileEdit: run black on an edited Python file under src/ or tests/ so
# formatting never fails the gate and never costs an agent fix loop.
# Fails open (always exits 0, prints nothing the agent must act on).
set -uo pipefail

input=$(cat 2>/dev/null) || exit 0
file=$(printf '%s' "$input" | jq -r '.file_path // empty' 2>/dev/null) || exit 0
case "$file" in
    *.py) ;;
    *) exit 0 ;;
esac

root=$(git -C "$(dirname "$file")" rev-parse --show-toplevel 2>/dev/null) || exit 0
case "$file" in
    "$root"/src/*|"$root"/tests/*|src/*|tests/*) ;;
    *) exit 0 ;;
esac

black="$root/venv/bin/black"
[ -x "$black" ] || black=$(command -v black 2>/dev/null) || exit 0
"$black" -q --line-length 120 "$file" >/dev/null 2>&1 || true
exit 0
