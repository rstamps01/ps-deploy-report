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

# Extract canonical version from src/__init__.py
CANONICAL_VERSION=$(grep -E '^__version__\s*=' "$PROJECT_ROOT/src/__init__.py" | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')

if [ -z "$CANONICAL_VERSION" ]; then
    echo "ERROR: Could not extract version from src/__init__.py"
    exit 1
fi

echo "Canonical version (src/__init__.py): $CANONICAL_VERSION"
echo ""

ERRORS=0

# Check src/__init__.py docstring
INIT_DOCSTRING=$(grep -E 'Version:\s*[0-9]' "$PROJECT_ROOT/src/__init__.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "")
if [ "$INIT_DOCSTRING" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/__init__.py docstring has '$INIT_DOCSTRING', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/__init__.py docstring"
fi

# Check src/app.py APP_VERSION
APP_VERSION=$(grep -E '^APP_VERSION\s*=' "$PROJECT_ROOT/src/app.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$APP_VERSION" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/app.py APP_VERSION has '$APP_VERSION', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/app.py APP_VERSION"
fi

# Check src/main.py --version argument
MAIN_VERSION=$(grep -E 'version="VAST As-Built Report Generator' "$PROJECT_ROOT/src/main.py" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$MAIN_VERSION" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: src/main.py --version has '$MAIN_VERSION', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: src/main.py --version"
fi

# Check packaging/vast-reporter.spec CFBundleShortVersionString
SPEC_SHORT=$(grep -E 'CFBundleShortVersionString' "$PROJECT_ROOT/packaging/vast-reporter.spec" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$SPEC_SHORT" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: packaging/vast-reporter.spec CFBundleShortVersionString has '$SPEC_SHORT', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: packaging/vast-reporter.spec CFBundleShortVersionString"
fi

# Check packaging/vast-reporter.spec CFBundleVersion
SPEC_BUNDLE=$(grep -E 'CFBundleVersion' "$PROJECT_ROOT/packaging/vast-reporter.spec" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
if [ "$SPEC_BUNDLE" != "$CANONICAL_VERSION" ]; then
    echo "MISMATCH: packaging/vast-reporter.spec CFBundleVersion has '$SPEC_BUNDLE', expected '$CANONICAL_VERSION'"
    ERRORS=$((ERRORS + 1))
else
    echo "OK: packaging/vast-reporter.spec CFBundleVersion"
fi

# Check README.md version badge
README_VERSION=$(grep -E '\*\*Version:\*\*' "$PROJECT_ROOT/README.md" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
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
