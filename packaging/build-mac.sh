#!/usr/bin/env bash
# Build VAST As-Built Reporter for macOS.
#
# Prerequisites:
#   pip install pyinstaller
#   brew install create-dmg   (optional, for DMG creation)
#
# Usage:
#   cd <project-root>
#   bash packaging/build-mac.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"

echo "=== VAST Reporter macOS Build ==="
echo "Project root: $PROJECT_ROOT"

# 0. Ensure system-level Cairo is installed (required by cairosvg for SVG diagrams)
if ! pkg-config --exists cairo 2>/dev/null; then
    echo "Installing Cairo via Homebrew (required for SVG diagram rendering)..."
    brew install cairo
fi

# 1. Clean previous build
rm -rf "$DIST_DIR" "$PROJECT_ROOT/build"

# 2. Ensure required config files exist (gitignored files that may not be present in CI)
if [ ! -f "$PROJECT_ROOT/config/cluster_profiles.json" ]; then
    echo "{}" > "$PROJECT_ROOT/config/cluster_profiles.json"
    echo "Created empty cluster_profiles.json"
fi

# 3. Run PyInstaller
echo "Running PyInstaller..."
cd "$PROJECT_ROOT"
pyinstaller packaging/vast-reporter.spec --noconfirm

# 4. Verify output
APP_PATH="$DIST_DIR/VAST Reporter.app"
if [ -d "$APP_PATH" ]; then
    echo "App bundle created: $APP_PATH"
else
    # Fallback to folder mode
    APP_PATH="$DIST_DIR/VAST Reporter"
    if [ -d "$APP_PATH" ]; then
        echo "App folder created: $APP_PATH"
    else
        echo "ERROR: Build output not found"
        exit 1
    fi
fi

# 5. Create DMG (if create-dmg is installed)
if command -v create-dmg &> /dev/null; then
    VERSION=$(grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' "$PROJECT_ROOT/src/app.py" | head -1) || VERSION="1.4.0"
    DMG_NAME="VAST-Reporter-v${VERSION}-mac.dmg"
    echo "Creating DMG: $DMG_NAME"
    create-dmg \
        --volname "VAST Reporter" \
        --window-pos 200 120 \
        --window-size 540 380 \
        --icon-size 100 \
        --icon "VAST Reporter.app" 150 100 \
        --app-drop-link 390 100 \
        "$DIST_DIR/$DMG_NAME" \
        "$APP_PATH"
    echo "DMG created: $DIST_DIR/$DMG_NAME"
else
    echo "create-dmg not found — skipping DMG creation."
    echo "Install with: brew install create-dmg"
    echo "You can distribute the app bundle directly: $APP_PATH"
fi

echo ""
echo "=== Build complete ==="
echo "Output: $DIST_DIR/"
ls -lh "$DIST_DIR/"
