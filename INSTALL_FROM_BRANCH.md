# Installing from Different Branches

**Version**: 1.0.0  
**Date**: October 18, 2025  
**Status**: ✅ Available on `develop` branch

---

## 📋 Overview

The installation scripts now support installing from any Git branch, not just `main`. This is useful for:
- **Testing** new features on the `develop` branch
- **Preview** releases before they go to production
- **Custom** branch deployments for specific environments

---

## 🚀 Quick Start

### Install from `develop` Branch

**Mac/Linux:**
```bash
# Download installer from develop branch
curl -o install-mac.sh https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-mac.sh

# Make executable
chmod +x install-mac.sh

# Install from develop branch
VAST_INSTALL_BRANCH=develop ./install-mac.sh
```

**Windows PowerShell:**
```powershell
# Download installer from develop branch
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"

# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install from develop branch
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
```

---

## 📖 Detailed Instructions

### Method 1: Environment Variable (Recommended)

This method allows you to specify which branch to install from using an environment variable.

#### Mac/Linux

```bash
# Step 1: Download the installer
curl -o install-mac.sh https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-mac.sh

# Step 2: Make it executable
chmod +x install-mac.sh

# Step 3: Set branch and run
VAST_INSTALL_BRANCH=develop ./install-mac.sh
```

**Alternative (persistent setting):**
```bash
# Set environment variable for current session
export VAST_INSTALL_BRANCH=develop

# Run installer
./install-mac.sh
```

#### Windows PowerShell

```powershell
# Step 1: Download the installer
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"

# Step 2: Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Step 3: Set branch and run
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
```

---

### Method 2: Direct Download from Specific Branch

Download the installer directly from the branch you want to install.

#### Mac/Linux

```bash
# For develop branch
curl -o install-mac.sh https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-mac.sh
chmod +x install-mac.sh
VAST_INSTALL_BRANCH=develop ./install-mac.sh

# For main branch (default)
curl -o install-mac.sh https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

#### Windows PowerShell

```powershell
# For develop branch
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1

# For main branch (default)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
.\install-windows.ps1
```

---

### Method 3: Clone and Install Manually

For advanced users who want full control.

#### Mac/Linux

```bash
# Clone specific branch
git clone -b develop https://github.com/rstamps01/ps-deploy-report.git
cd ps-deploy-report

# Run installer from cloned repo
cd docs/deployment
./install-mac.sh
```

#### Windows PowerShell

```powershell
# Clone specific branch
git clone -b develop https://github.com/rstamps01/ps-deploy-report.git
cd ps-deploy-report

# Run installer from cloned repo
cd docs\deployment
.\install-windows.ps1
```

---

## 🎯 Branch Selection Options

### Available Branches

| Branch | Purpose | Stability | Recommended For |
|--------|---------|-----------|-----------------|
| `main` | Production releases | ✅ Stable | Production use |
| `develop` | Latest features & fixes | ⚠️ Testing | Testing, development |
| Custom | Feature branches | ❓ Varies | Specific testing |

### How It Works

The installation scripts check for the `VAST_INSTALL_BRANCH` environment variable:

**Mac/Linux:**
```bash
INSTALL_BRANCH="${VAST_INSTALL_BRANCH:-main}"  # Defaults to 'main'
```

**Windows:**
```powershell
$script:InstallBranch = if ($env:VAST_INSTALL_BRANCH) { $env:VAST_INSTALL_BRANCH } else { "main" }
```

If not set, it defaults to `main`.

---

## 📦 Installation Modes

All three installation modes work with branch selection:

### 1. Full Installation + Develop Branch
```bash
# Mac/Linux
VAST_INSTALL_BRANCH=develop ./install-mac.sh
# Select option 1 (Full Installation)

# Windows
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
# Select option 1 (Full Installation)
```

**Result**: ~215 MB installation with full Git history from `develop` branch

### 2. Production + Develop Branch
```bash
# Mac/Linux
VAST_INSTALL_BRANCH=develop ./install-mac.sh
# Select option 2 (Production Deployment)

# Windows
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
# Select option 2 (Production Deployment)
```

**Result**: ~114 MB installation, `.git` folder removed after cloning from `develop`

### 3. Minimal + Develop Branch
```bash
# Mac/Linux
VAST_INSTALL_BRANCH=develop ./install-mac.sh
# Select option 3 (Minimal Installation)

# Windows
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
# Select option 3 (Minimal Installation)
```

**Result**: ~20 MB installation, source archive downloaded from `develop` branch

---

## 🔄 Updating Existing Installations

If you have an existing installation, you can switch branches:

### Mac/Linux
```bash
cd ~/vast-asbuilt-reporter

# Switch to develop branch
git checkout develop
git pull origin develop

# Or switch back to main
git checkout main
git pull origin main
```

### Windows PowerShell
```powershell
cd $env:USERPROFILE\vast-asbuilt-reporter

# Switch to develop branch
git checkout develop
git pull origin develop

# Or switch back to main
git checkout main
git pull origin main
```

**Note**: This only works if you used "Full Installation" mode. Production and Minimal modes don't include the `.git` folder.

---

## ⚙️ Examples

### Example 1: Test Latest Features
```bash
# Install latest develop branch to test new features
VAST_INSTALL_BRANCH=develop ./install-mac.sh
```

### Example 2: Install Specific Feature Branch
```bash
# Install from a specific feature branch
VAST_INSTALL_BRANCH=feature/new-report-format ./install-mac.sh
```

### Example 3: Install Release Candidate
```bash
# Install from release candidate branch
VAST_INSTALL_BRANCH=release/v1.1.0 ./install-mac.sh
```

### Example 4: Production with Latest Develop
```bash
# Production mode with develop branch (no .git folder)
VAST_INSTALL_BRANCH=develop ./install-mac.sh
# Select option 2 (Production Deployment)
```

---

## 🧪 Verification

After installation, verify which branch was installed:

### If You Used Full Installation (has .git)
```bash
cd ~/vast-asbuilt-reporter
git branch  # Shows current branch
git log --oneline -5  # Shows recent commits
```

### If You Used Production/Minimal (no .git)
Check the version in the code or README:
```bash
cd ~/vast-asbuilt-reporter
cat README.md | grep Version
```

---

## 🚨 Important Notes

### 1. **Stability Warning**
- `main` branch: Production-ready, fully tested
- `develop` branch: Latest features, may have bugs
- Feature branches: Experimental, use with caution

### 2. **No Automatic Updates**
- Production mode: Requires manual reinstall to update
- Minimal mode: Requires manual reinstall to update
- Full mode: Can use `git pull` to update

### 3. **Branch Switching**
Only possible with "Full Installation" mode:
```bash
cd ~/vast-asbuilt-reporter
git checkout develop
git pull origin develop
```

### 4. **Environment Variable Scope**
The `VAST_INSTALL_BRANCH` variable only affects installation. Once installed, the branch is fixed (unless using Full mode with Git).

---

## 🔧 Troubleshooting

### Error: "Branch not found"
```bash
fatal: Remote branch xyz not found in upstream origin
```

**Solution**: Verify the branch exists:
```bash
# List all branches
git ls-remote --heads https://github.com/rstamps01/ps-deploy-report.git
```

### Error: "Archive not found (404)"
```
curl: (22) The requested URL returned error: 404
```

**Solution**: The branch name may be incorrect or the branch doesn't exist on GitHub yet.

### Installation Uses Wrong Branch
```bash
# Check what was actually installed
cd ~/vast-asbuilt-reporter
git remote -v
git branch -a
```

---

## 📊 Comparison Matrix

| Feature | Main Branch | Develop Branch |
|---------|-------------|----------------|
| Stability | ✅ Stable | ⚠️ Testing |
| Latest Features | ❌ Not yet | ✅ Yes |
| Bug Fixes | ✅ Tested | ✅ Latest |
| Production Ready | ✅ Yes | ❌ No |
| Installation Size | Same | Same |
| Update Frequency | Monthly | Daily |
| Documentation | Complete | May be incomplete |
| Support | Full | Community |

---

## 🎓 Best Practices

### For Production Use
```bash
# Always use main branch
./install-mac.sh  # Defaults to main
# OR explicitly set
VAST_INSTALL_BRANCH=main ./install-mac.sh
```

### For Testing New Features
```bash
# Use develop branch with Full installation
VAST_INSTALL_BRANCH=develop ./install-mac.sh
# Select option 1 (Full Installation)
# This allows easy switching between branches
```

### For Development
```bash
# Clone the repo directly
git clone -b develop https://github.com/rstamps01/ps-deploy-report.git
cd ps-deploy-report
# Make your changes...
```

---

## 📝 Summary

**To install from `develop` branch:**

**Mac:**
```bash
curl -o install-mac.sh https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-mac.sh
chmod +x install-mac.sh
VAST_INSTALL_BRANCH=develop ./install-mac.sh
```

**Windows:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
$env:VAST_INSTALL_BRANCH = "develop"
.\install-windows.ps1
```

**Default (main branch):**
```bash
# Just run without setting VAST_INSTALL_BRANCH
./install-mac.sh  # Mac/Linux
.\install-windows.ps1  # Windows
```

---

## 🔗 Related Documentation

- **Installation Guide**: `docs/deployment/INSTALLATION-GUIDE.md`
- **Update Guide**: `docs/deployment/UPDATE-GUIDE.md`
- **Uninstall Guide**: `docs/deployment/UNINSTALL-GUIDE.md`
- **Main README**: `README.md`

---

**Feature Available**: `develop` branch (commit `780f578`)  
**Coming to `main`**: Next release (v1.0.1+)

