#!/usr/bin/env bash
# Local quality gate in one call (mirrors the blocking CI gate).
#
# Runs version-sync, black --check, flake8 (+E722), mypy, and pytest with the
# coverage floor. Full logs go to test_output/quality-gate/<step>.log; stdout is
# one PASS/FAIL line per step plus the tail of the first failing log, so an
# agent reads a few lines instead of thousands.
#
# Usage: bash scripts/quality-gate.sh [--fix] [--all] [--parallel]
#   --fix       run black (write) before the format check
#   --all       keep going after a failure (default: stop at the first)
#   --parallel  run pytest with -n auto (requires pytest-xdist)
set -uo pipefail

COV_FLOOR=60
TAIL_LINES=40

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$root" || exit 2
PY=python3
[ -x venv/bin/python ] && PY=venv/bin/python

fix=0; all=0; parallel=0
for arg in "$@"; do
    case "$arg" in
        --fix) fix=1 ;;
        --all) all=1 ;;
        --parallel) parallel=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

logdir=test_output/quality-gate
mkdir -p "$logdir"
failed=0

run_step() {
    local name=$1; shift
    local log="$logdir/$name.log"
    local start=$SECONDS
    if "$@" >"$log" 2>&1; then
        printf 'PASS  %-12s %4ss\n' "$name" "$((SECONDS - start))"
        return 0
    fi
    printf 'FAIL  %-12s %4ss  (full log: %s)\n' "$name" "$((SECONDS - start))" "$log"
    echo "----- last $TAIL_LINES lines of $log -----"
    tail -n "$TAIL_LINES" "$log"
    echo "-----"
    failed=1
    [ "$all" -eq 1 ] || exit 1
}

lint() {
    "$PY" -m flake8 src/ tests/ && "$PY" -m flake8 src/ tests/ --select=E722 --extend-ignore=
}

pytest_args=(tests/ --ignore=tests/test_ui.py --ignore=tests/test_integration.py -m "not flaky"
    --cov=src --cov-report=term:skip-covered --cov-report=xml --cov-fail-under="$COV_FLOOR"
    --junitxml="$logdir/junit.xml")
[ "$parallel" -eq 1 ] && pytest_args+=(-n auto)

[ "$fix" -eq 1 ] && "$PY" -m black -q --line-length 120 src/ tests/

run_step version-sync bash scripts/check-version-sync.sh
run_step format "$PY" -m black --check --line-length 120 src/ tests/
run_step lint lint
run_step types "$PY" -m mypy src/ --ignore-missing-imports --no-strict-optional
run_step tests "$PY" -m pytest "${pytest_args[@]}"

if [ "$failed" -eq 0 ]; then
    total=$(grep -E '^TOTAL' "$logdir/tests.log" | awk '{print $NF}')
    echo "Quality gate PASSED (coverage ${total:-n/a}, floor ${COV_FLOOR}%)"
else
    echo "Quality gate FAILED; failure summary:"
    "$PY" scripts/junit_summary.py "$logdir/junit.xml" --max 10
    exit 1
fi
