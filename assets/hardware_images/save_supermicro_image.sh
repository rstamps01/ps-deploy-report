#!/bin/bash

# Script to help save the Supermicro Gen5 CBox image

echo "================================================"
echo "Supermicro Gen5 CBox Image Setup"
echo "================================================"
echo ""

TARGET_DIR="/Users/ray.stamps/Documents/as-built-report/ps-deploy-report/assets/hardware_images"
TARGET_FILE="$TARGET_DIR/supermicro_gen5_cbox_1u.png"

echo "Target location:"
echo "  $TARGET_FILE"
echo ""

# Check if image already exists
if [ -f "$TARGET_FILE" ]; then
    echo "✅ Image already exists!"
    ls -lh "$TARGET_FILE"
    echo ""
    echo "To regenerate the report with this image:"
    echo "  cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report"
    echo "  python3 -m src.main --cluster-ip 10.143.11.204 --username support --password 654321"
    exit 0
fi

echo "❌ Image not found."
echo ""
echo "Please save the Supermicro Gen5 CBox image to:"
echo "  $TARGET_FILE"
echo ""
echo "Options to save the image:"
echo ""
echo "1. From clipboard (if you copied the image):"
echo "   - On Mac: Use Preview > File > New from Clipboard > Save As"
echo ""
echo "2. From Downloads folder:"
echo "   cp ~/Downloads/supermicro_gen5_cbox.png \"$TARGET_FILE\""
echo ""
echo "3. From drag-and-drop:"
echo "   - Drag the image file to the terminal"
echo "   - Type: cp "
echo "   - Paste the path (it will auto-complete)"
echo "   - Add: \"$TARGET_FILE\""
echo ""
echo "4. Manual save:"
echo "   - Right-click the image in the conversation"
echo "   - Save As..."
echo "   - Navigate to: $TARGET_DIR"
echo "   - Save as: supermicro_gen5_cbox_1u.png"
echo ""
echo "================================================"
