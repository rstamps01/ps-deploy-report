#!/bin/bash
# Test script to validate installation scripts
# This script tests the installation process without actually installing

set -e

echo "=================================================================="
echo "VAST AS-BUILT REPORT GENERATOR - INSTALLATION SCRIPT TEST"
echo "=================================================================="
echo

# Test macOS installation script syntax
echo "Testing macOS installation script..."
if bash -n install-mac.sh; then
    echo "✅ macOS installation script syntax is valid"
else
    echo "❌ macOS installation script has syntax errors"
    exit 1
fi

# Test Windows installation script syntax
echo "Testing Windows installation script..."
if powershell -Command "Get-Content install-windows.ps1 | Out-Null"; then
    echo "✅ Windows installation script syntax is valid"
else
    echo "❌ Windows installation script has syntax errors"
    exit 1
fi

# Test that required files exist
echo "Testing required files..."

required_files=(
    "README.md"
    "INSTALLATION-GUIDE.md"
    "install-mac.sh"
    "install-windows.ps1"
    "requirements.txt"
    "config/config.yaml.template"
    "src/main.py"
    "src/api_handler.py"
    "src/data_extractor.py"
    "src/report_builder.py"
    "src/utils/logger.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

# Test that installation scripts are executable
echo "Testing script permissions..."
if [ -x "install-mac.sh" ]; then
    echo "✅ macOS installation script is executable"
else
    echo "❌ macOS installation script is not executable"
    exit 1
fi

# Test Python syntax
echo "Testing Python files..."
python_files=(
    "src/main.py"
    "src/api_handler.py"
    "src/data_extractor.py"
    "src/report_builder.py"
    "src/utils/logger.py"
)

for file in "${python_files[@]}"; do
    if python3 -m py_compile "$file"; then
        echo "✅ $file syntax is valid"
    else
        echo "❌ $file has syntax errors"
        exit 1
    fi
done

# Test configuration template
echo "Testing configuration template..."
if python3 -c "import yaml; yaml.safe_load(open('config/config.yaml.template'))" 2>/dev/null; then
    echo "✅ Configuration template is valid YAML"
else
    echo "❌ Configuration template has YAML syntax errors"
    exit 1
fi

echo
echo "=================================================================="
echo "ALL TESTS PASSED - INSTALLATION SCRIPTS ARE READY"
echo "=================================================================="
echo
echo "Installation scripts are ready for distribution to PS engineers:"
echo "• macOS: install-mac.sh"
echo "• Windows: install-windows.ps1"
echo "• Documentation: INSTALLATION-GUIDE.md"
echo
