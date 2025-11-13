# Release v1.3.0 - Installation Script Enhancements

**Release Date:** November 12, 2025  
**Target VAST Version:** 5.3+  
**API Version:** v7

## 🎉 Major Features

### Installation Script Enhancements

#### Enhanced Features Documentation
- **Clear messaging**: Installation scripts now provide clear documentation about enhanced features during dependency installation
- **Feature visibility**: Users are informed about port mapping, network topology, and enhanced hardware inventory capabilities
- **Dependency verification**: Installation scripts verify and confirm installation of all enhanced feature dependencies

#### Port Mapping Usage Examples
- **Mac installation script**: Added port mapping collection examples to usage instructions
- **Windows installation script**: Added port mapping collection examples to usage instructions
- **Better onboarding**: New users can immediately see how to use port mapping features

## 📋 What's Changed

### Installation Scripts
- **`docs/deployment/install-mac.sh`**:
  - Added descriptive messages during Python dependency installation listing enhanced features
  - Added port mapping usage example in usage instructions
  - Improved user experience with clear feature documentation

- **`docs/deployment/install-windows.ps1`**:
  - Added descriptive messages during Python dependency installation listing enhanced features
  - Added port mapping usage example in usage instructions
  - Improved user experience with clear feature documentation

### Documentation Updates
- **README.md**: Updated to version 1.3.0 with installation script enhancements section
- **CHANGELOG.md**: Added v1.3.0 entry documenting installation script improvements
- **Installation guides**: Updated all version references to v1.3.0

## 🔧 Technical Details

### Files Modified
- `src/main.py`: Updated version to 1.3.0
- `README.md`: Updated version and added v1.3.0 section
- `CHANGELOG.md`: Added v1.3.0 entry
- `docs/deployment/install-mac.sh`: Added enhanced features documentation
- `docs/deployment/install-windows.ps1`: Added enhanced features documentation
- `docs/deployment/INSTALLATION-GUIDE.md`: Updated version references
- `docs/deployment/UNINSTALL-GUIDE.md`: Updated version references

## 📦 Installation

### Quick Start

**For Mac Users:**
```bash
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.3.0/docs/deployment/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

**For Windows Users:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.3.0/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\install-windows.ps1
```

## 🚀 Upgrade from v1.2.0

If you're upgrading from v1.2.0, simply pull the latest changes:

```bash
cd ~/vast-asbuilt-reporter
git fetch origin
git checkout main
git pull origin main
```

Or use the update script:
```bash
cd ~/vast-asbuilt-reporter
./scripts/update.sh
```

## 📝 Notes

- This release focuses on improving the installation experience and documentation
- All existing functionality from v1.2.0 is preserved
- No breaking changes
- Installation scripts now use v1.3.0 tag for downloads

## 🙏 Acknowledgments

Thank you for using the VAST As-Built Report Generator!

---

**Full Changelog**: See [CHANGELOG.md](../CHANGELOG.md) for complete details.

