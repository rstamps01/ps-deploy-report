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

# 1. Clean previous build
rm -rf "$DIST_DIR" "$PROJECT_ROOT/build"

# 2. Run PyInstaller
echo "Running PyInstaller..."
cd "$PROJECT_ROOT"
pyinstaller packaging/vast-reporter.spec --noconfirm

# 3. Verify output
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

# 4. Create DMG (if create-dmg is installed)
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
