# Python 3.14 Installation Fix

## Issue

When installing on Python 3.14.0, the installation fails with:
```
ImportError: cannot import name 'get_abi_tag' from 'wheel.bdist_wheel'
```

This occurs when `rl-renderPM` tries to build from source because it doesn't have pre-built wheels for Python 3.14 yet.

## Root Cause

1. **Python 3.14 Compatibility**: Python 3.14 is very new and some packages don't have pre-built wheels yet
2. **Build Tools**: The `wheel` package version may be too old for Python 3.14
3. **rl-renderPM**: This package requires building from source on Python 3.14, which fails due to wheel compatibility

## Solution Implemented

The installation script (`install-mac.sh`) has been updated to:

1. **Upgrade Build Tools First**: Automatically upgrades `wheel` and `setuptools` before installing dependencies
2. **Python 3.14 Detection**: Detects Python 3.14+ and uses a compatibility installation strategy
3. **Separate rl-renderPM Installation**: Installs `rl-renderPM` separately after core dependencies
4. **Graceful Fallback**: If `rl-renderPM` fails, the installation continues (it's not critical for basic functionality)

## Manual Fix (If Installation Still Fails)

If you encounter this issue, you can manually fix it:

### Option 1: Upgrade Build Tools Manually

```bash
cd ~/vast-asbuilt-reporter
source venv/bin/activate
pip install --upgrade wheel setuptools pip
pip install -r requirements.txt
```

### Option 2: Install rl-renderPM Separately

```bash
cd ~/vast-asbuilt-reporter
source venv/bin/activate

# Install all dependencies except rl-renderPM
pip install requests urllib3 PyYAML reportlab weasyprint cairocffi pycairo Pillow click pytest pytest-cov pytest-mock flake8 black colorlog python-dateutil jsonschema python-dotenv pexpect

# Try installing rl-renderPM with different options
pip install rl-renderPM --no-build-isolation
# OR
pip install rl-renderPM --upgrade --force-reinstall
```

### Option 3: Skip rl-renderPM (If Not Needed)

If you don't need PNG conversion features, you can skip `rl-renderPM`:

```bash
cd ~/vast-asbuilt-reporter
source venv/bin/activate

# Create a modified requirements file
grep -v "^rl-renderPM" requirements.txt > requirements-no-renderpm.txt

# Install without rl-renderPM
pip install -r requirements-no-renderpm.txt
```

**Note**: The tool will work without `rl-renderPM`, but some PNG conversion features may be limited.

## Verification

After installation, verify critical packages are installed:

```bash
source venv/bin/activate
pip show requests reportlab PyYAML pexpect
```

All should show as installed. If `rl-renderPM` is missing, that's okay for basic functionality.

## Alternative: Use Python 3.13

If you continue to have issues with Python 3.14, consider using Python 3.13 instead:

```bash
# Install Python 3.13 via Homebrew
brew install python@3.13

# Create virtual environment with Python 3.13
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

## Status

- ✅ Installation script updated to handle Python 3.14
- ✅ Build tools upgrade added
- ✅ Graceful fallback for rl-renderPM
- ⚠️ rl-renderPM may still fail on Python 3.14 (non-critical)

## Related Files

- `docs/deployment/install-mac.sh` - Updated installation script
- `requirements.txt` - Dependencies list

---

**Last Updated**: November 21, 2025
**Tested On**: macOS Sequoia 15.4.1, Python 3.14.0
