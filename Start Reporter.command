#!/bin/bash
# asbuilt-reporter — double-click to launch
cd "$(dirname "$0")/src"
echo ""
echo "  Starting asbuilt-reporter..."
echo ""
python3 main.py
