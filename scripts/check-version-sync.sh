#!/usr/bin/env bash
# Validate that all version references in the codebase are synchronized.
# This script is run by CI to catch version mismatches before release.
#
# Usage:
#   bash scripts/check-version-sync.sh
#
# Exit codes:
#   0 - All versions match
#   1 - Version mismatch detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Version Synchronization Check ==="

# Extract canonical version from src/__init__.py (supports prerelease suffixes like -beta, -rc1)
CANONICAL_VERSION=$(grep -E '^__version__\s*=' "$PROJECT_ROOT/src/__init__.py" | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?)".*/\1/')
BASE_VERSION=$(echo "$CANONICAL_VERSION" | sed -E 's/-.*//')

if [ -z "$CANONICAL_VERSION" ]; then
    echo "ERROR: Could not extract version from src/__init__.py"
    exit 1
fi

echo "Canonical version (src/__init__.py): $CANONICAL_VERSION"
echo "Base version (numeric only): $BASE_VERSION"
echo ""

ERRORS=0

# Check src/__init__.py docstring
INIT_DOCSTRING=$(grep -E 'Version:\s*[0-9]' "$PROJECT_ROOT/src/__init__.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?' || echo "")
if [ "$INIT_DOCSTRING" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/__init__.py docstring has '$INIT_DOCSTRING', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/__init__.py docstring"
fi

# Check src/app.py APP_VERSION
APP_VERSION=$(grep -E '^APP_VERSION\s*=' "$PROJECT_ROOT/src/app.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?')
if [ "$APP_VERSION" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/app.py APP_VERSION has '$APP_VERSION', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/app.py APP_VERSION"
fi

# Check src/main.py APP_VERSION (the argparse --version output derives from it
# via an f-string, so the constant is the authoritative value to compare).
MAIN_VERSION=$(grep -E '^APP_VERSION\s*=' "$PROJECT_ROOT/src/main.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?')
if [ "$MAIN_VERSION" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/main.py APP_VERSION has '$MAIN_VERSION', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/main.py APP_VERSION"
fi

# Check packaging/vast-reporter.spec CFBundleShortVersionString
# Apple CFBundle versions only support numeric X.Y.Z — compare against BASE_VERSION
SPEC_SHORT=$(grep -E 'CFBundleShortVersionString' "$PROJECT_ROOT/packaging/vast-reporter.spec" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$SPEC_SHORT" != "$BASE_VERSION" ]; then
    echo "MISMATCH: packaging/vast-reporter.spec CFBundleShortVersionString has '$SPEC_SHORT', expected '$BASE_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: packaging/vast-reporter.spec CFBundleShortVersionString"
fi

# Check packaging/vast-reporter.spec CFBundleVersion
SPEC_BUNDLE=$(grep -E 'CFBundleVersion' "$PROJECT_ROOT/packaging/vast-reporter.spec" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$SPEC_BUNDLE" != "$BASE_VERSION" ]; then
    echo "MISMATCH: packaging/vast-reporter.spec CFBundleVersion has '$SPEC_BUNDLE', expected '$BASE_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: packaging/vast-reporter.spec CFBundleVersion"
fi

# Check README.md version badge
README_VERSION=$(grep -E '\*\*Version:\*\*' "$PROJECT_ROOT/README.md" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?')
if [ "$README_VERSION" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: README.md version badge has '$README_VERSION', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: README.md version badge"
fi

echo ""
if [ $ERRORS -gt 0 ]; then
    echo "=== FAILED: $ERRORS version mismatch(es) found ==="
    echo ""
    echo "To fix, update all version references to match src/__init__.py __version__"
    echo "Files to check:"
    echo "  - src/__init__.py (docstring and __version__)"
    echo "  - src/app.py (APP_VERSION)"
    echo "  - src/main.py (--version argument)"
    echo "  - packaging/vast-reporter.spec (CFBundleShortVersionString, CFBundleVersion)"
    echo "  - README.md (version badge)"
    exit 1
else
    echo "=== PASSED: All versions synchronized ($CANONICAL_VERSION) ==="
    exit 0
fi
