# VAST As-Built Report Generator - Update & Upgrade Guide

## Table of Contents

1. [Overview](#overview)
2. [Update Strategies](#update-strategies)
3. [Recommended Approach: Git Pull Update](#recommended-approach-git-pull-update)
4. [Alternative: Clean Reinstall](#alternative-clean-reinstall)
5. [Alternative: In-Place Upgrade](#alternative-in-place-upgrade)
6. [Automated Update Script](#automated-update-script)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Version Compatibility](#version-compatibility)

---

## Overview

This guide provides comprehensive instructions for updating the VAST As-Built Report Generator to the latest version while preserving your data, configuration, and generated reports.

### What Gets Updated

During an update:
- ✓ Application source code
- ✓ Python dependencies
- ✓ Templates and assets
- ✓ Documentation

### What Gets Preserved

Your data is preserved:
- ✓ Generated reports
- ✓ Configuration files (config.yaml)
- ✓ Log files
- ✓ Output data

---

## Update Strategies

### Strategy Comparison

| Method | Complexity | Downtime | Risk | Best For |
|--------|------------|----------|------|----------|
| **Git Pull** | Low | Minimal | Low | Regular updates |
| **Clean Reinstall** | Medium | Moderate | Low | Major version upgrades |
| **In-Place Upgrade** | Low | Minimal | Medium | Quick updates |

### Recommended Update Frequency

- **Production**: Monthly or when critical fixes are released
- **Development**: Weekly or as needed
- **Testing**: Before each production update

---

## Recommended Approach: Git Pull Update

This is the **recommended method** for most updates. It preserves your installation while updating code.

### Prerequisites

- Git installed
- Installation was done via `git clone`
- Internet connectivity

### Update Procedure

#### macOS/Linux

**Step 1: Navigate to installation directory**
```bash
cd ~/vast-asbuilt-reporter
# Or your custom installation path
```

**Step 2: Backup current installation (optional but recommended)**
```bash
# Create a backup tag
git tag backup-$(date +%Y%m%d_%H%M%S)

# Or create a full backup
cp -r ~/vast-asbuilt-reporter ~/vast-asbuilt-reporter-backup-$(date +%Y%m%d)
```

**Step 3: Backup your configuration and data**
```bash
# Backup config
cp config/config.yaml ~/config-backup.yaml

# Backup reports (if not in default location)
tar -czf ~/reports-backup-$(date +%Y%m%d).tar.gz reports/ output/ logs/
```

**Step 4: Check for local changes**
```bash
git status
```

If you have uncommitted changes:
```bash
# Stash changes
git stash save "Pre-update backup $(date +%Y%m%d)"

# Or commit them
git add config/config.yaml
git commit -m "Save local configuration"
```

**Step 5: Fetch latest updates**
```bash
# Fetch updates from remote
git fetch origin

# Check what will change
git log HEAD..origin/develop --oneline
```

**Step 6: Apply updates**
```bash
# Pull latest from develop branch
git pull origin develop
```

**Step 7: Update dependencies**
```bash
# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt
```

**Step 8: Restore configuration if needed**
```bash
# If config.yaml was overwritten
cp ~/config-backup.yaml config/config.yaml

# Or merge changes manually
diff ~/config-backup.yaml config/config.yaml
```

**Step 9: Verify update**
```bash
# Check version
python3 -m src.main --version

# Run a test report
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
```

**Step 10: Restore stashed changes (if any)**
```bash
git stash pop
```

#### Windows

**Step 1: Navigate to installation directory**
```powershell
cd $env:USERPROFILE\vast-asbuilt-reporter
```

**Step 2: Backup current installation**
```powershell
# Create backup tag
git tag "backup-$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Or full backup
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter" -Destination "$env:USERPROFILE\vast-asbuilt-reporter-backup-$(Get-Date -Format 'yyyyMMdd')" -Recurse
```

**Step 3: Backup configuration and data**
```powershell
# Backup config
Copy-Item -Path "config\config.yaml" -Destination "$env:USERPROFILE\config-backup.yaml"

# Backup reports
Compress-Archive -Path "reports\*","output\*","logs\*" -DestinationPath "$env:USERPROFILE\reports-backup-$(Get-Date -Format 'yyyyMMdd').zip"
```

**Step 4: Check for local changes**
```powershell
git status
```

If you have uncommitted changes:
```powershell
# Stash changes
git stash save "Pre-update backup $(Get-Date -Format 'yyyyMMdd')"
```

**Step 5: Fetch and apply updates**
```powershell
# Fetch updates
git fetch origin

# Check what will change
git log HEAD..origin/develop --oneline

# Pull latest
git pull origin develop
```

**Step 6: Update dependencies**
```powershell
# Activate virtual environment
.\venv\Scripts\Activate

# Update dependencies
pip install --upgrade -r requirements.txt
```

**Step 7: Restore configuration**
```powershell
# If config.yaml was overwritten
Copy-Item -Path "$env:USERPROFILE\config-backup.yaml" -Destination "config\config.yaml"
```

**Step 8: Verify update**
```powershell
# Check version
python -m src.main --version

# Run test report
python -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
```

### Automated Git Pull Update Script

**Create update script (Mac/Linux):**
```bash
#!/bin/bash
# save as: update-vast-asbuilt-reporter.sh

INSTALL_DIR="$HOME/vast-asbuilt-reporter"
BACKUP_DIR="$HOME/vast-asbuilt-reporter-backups"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)

cd "$INSTALL_DIR" || exit 1

echo "Creating backup..."
mkdir -p "$BACKUP_DIR"
cp config/config.yaml "$BACKUP_DIR/config-$DATE_STAMP.yaml"

echo "Stashing local changes..."
git stash save "Auto-backup $DATE_STAMP"

echo "Updating from repository..."
git pull origin develop

echo "Updating dependencies..."
source venv/bin/activate
pip install --upgrade -r requirements.txt

echo "Restoring configuration..."
cp "$BACKUP_DIR/config-$DATE_STAMP.yaml" config/config.yaml

echo "Update complete! Version:"
python3 -m src.main --version
```

**Make it executable:**
```bash
chmod +x update-vast-asbuilt-reporter.sh
```

**Run it:**
```bash
./update-vast-asbuilt-reporter.sh
```

---

## Alternative: Clean Reinstall

Recommended for **major version upgrades** or when git history is corrupted.

### Procedure

**Step 1: Backup everything**
```bash
# Mac/Linux
cp -r ~/vast-asbuilt-reporter ~/vast-asbuilt-reporter-old
tar -czf ~/vast-asbuilt-reporter-complete-backup-$(date +%Y%m%d).tar.gz ~/vast-asbuilt-reporter

# Windows
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter" -Destination "$env:USERPROFILE\vast-asbuilt-reporter-old" -Recurse
Compress-Archive -Path "$env:USERPROFILE\vast-asbuilt-reporter" -DestinationPath "$env:USERPROFILE\vast-asbuilt-reporter-backup-$(Get-Date -Format 'yyyyMMdd').zip"
```

**Step 2: Extract important data**
```bash
# Mac/Linux
mkdir -p ~/vast-data-backup
cp -r ~/vast-asbuilt-reporter/reports ~/vast-data-backup/
cp -r ~/vast-asbuilt-reporter/output ~/vast-data-backup/
cp ~/vast-asbuilt-reporter/config/config.yaml ~/vast-data-backup/

# Windows
New-Item -ItemType Directory -Path "$env:USERPROFILE\vast-data-backup" -Force
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter\reports" -Destination "$env:USERPROFILE\vast-data-backup\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter\output" -Destination "$env:USERPROFILE\vast-data-backup\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter\config\config.yaml" -Destination "$env:USERPROFILE\vast-data-backup\"
```

**Step 3: Uninstall old version**

Follow the [Uninstall Guide](UNINSTALL-GUIDE.md)

**Step 4: Install new version**

Follow the [Installation Guide](INSTALLATION-GUIDE.md)

**Step 5: Restore data**
```bash
# Mac/Linux
cp -r ~/vast-data-backup/reports ~/vast-asbuilt-reporter/
cp -r ~/vast-data-backup/output ~/vast-asbuilt-reporter/
cp ~/vast-data-backup/config.yaml ~/vast-asbuilt-reporter/config/

# Windows
Copy-Item -Path "$env:USERPROFILE\vast-data-backup\reports" -Destination "$env:USERPROFILE\vast-asbuilt-reporter\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-data-backup\output" -Destination "$env:USERPROFILE\vast-asbuilt-reporter\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-data-backup\config.yaml" -Destination "$env:USERPROFILE\vast-asbuilt-reporter\config\"
```

**Step 6: Verify**
```bash
python3 -m src.main --version
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
```

---

## Alternative: In-Place Upgrade

Quick update without git. **Use only for minor updates.**

### Procedure

**Step 1: Download latest release**
```bash
# Mac/Linux
cd /tmp
curl -L https://github.com/rstamps01/ps-deploy-report/archive/refs/heads/develop.zip -o vast-latest.zip
unzip vast-latest.zip

# Windows
Invoke-WebRequest -Uri "https://github.com/rstamps01/ps-deploy-report/archive/refs/heads/develop.zip" -OutFile "$env:TEMP\vast-latest.zip"
Expand-Archive -Path "$env:TEMP\vast-latest.zip" -DestinationPath "$env:TEMP"
```

**Step 2: Backup current installation**
```bash
# Mac/Linux
cp config/config.yaml ~/config-backup.yaml

# Windows
Copy-Item -Path "config\config.yaml" -Destination "$env:USERPROFILE\config-backup.yaml"
```

**Step 3: Copy new files (skip data directories)**
```bash
# Mac/Linux
cd ~/vast-asbuilt-reporter
rsync -av --exclude='reports' --exclude='output' --exclude='logs' --exclude='venv' --exclude='.git' --exclude='config/config.yaml' /tmp/ps-deploy-report-develop/ ./

# Windows (manual copy)
# Copy src/, docs/, templates/, requirements.txt, README.md
# DO NOT copy: reports/, output/, logs/, venv/, config/config.yaml
```

**Step 4: Update dependencies**
```bash
# Mac/Linux
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Windows
.\venv\Scripts\Activate
pip install --upgrade -r requirements.txt
```

**Step 5: Verify**
```bash
python3 -m src.main --version
```

---

## Automated Update Script

Create a comprehensive update script:

### update-vast.sh (Mac/Linux)

```bash
#!/bin/bash

set -e

INSTALL_DIR="${VAST_INSTALL_DIR:-$HOME/vast-asbuilt-reporter}"
BACKUP_DIR="$HOME/vast-asbuilt-reporter-backups"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)

echo "═══════════════════════════════════════════════════════════════"
echo "  VAST Reporter Updater"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Installation not found at $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "▶ Creating backup..."
cp config/config.yaml "$BACKUP_DIR/config-$DATE_STAMP.yaml" 2>/dev/null || true
git tag "pre-update-$DATE_STAMP" 2>/dev/null || true
echo "✓ Backup created"

echo "▶ Checking for local changes..."
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo "  Local changes detected, stashing..."
    git stash save "Auto-stash before update $DATE_STAMP"
fi

echo "▶ Fetching updates..."
git fetch origin

echo "▶ Current version:"
python3 -m src.main --version 2>/dev/null || echo "  Unable to determine"

echo "▶ Applying updates..."
git pull origin develop

echo "▶ Updating dependencies..."
source venv/bin/activate
pip install --upgrade -r requirements.txt --quiet

echo "▶ Restoring configuration..."
if [ -f "$BACKUP_DIR/config-$DATE_STAMP.yaml" ]; then
    cp "$BACKUP_DIR/config-$DATE_STAMP.yaml" config/config.yaml
fi

echo "▶ New version:"
python3 -m src.main --version

echo ""
echo "✓ Update complete!"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "To rollback: git checkout pre-update-$DATE_STAMP"
echo ""
```

### update-vast.ps1 (Windows)

```powershell
#Requires -Version 5.1

$INSTALL_DIR = if ($env:VAST_INSTALL_DIR) { $env:VAST_INSTALL_DIR } else { "$env:USERPROFILE\vast-asbuilt-reporter" }
$BACKUP_DIR = "$env:USERPROFILE\vast-asbuilt-reporter-backups"
$DATE_STAMP = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  VAST Reporter Updater" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $INSTALL_DIR)) {
    Write-Host "Error: Installation not found at $INSTALL_DIR" -ForegroundColor Red
    exit 1
}

Set-Location $INSTALL_DIR

# Create backup directory
New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null

Write-Host "▶ Creating backup..." -ForegroundColor Cyan
Copy-Item -Path "config\config.yaml" -Destination "$BACKUP_DIR\config-$DATE_STAMP.yaml" -ErrorAction SilentlyContinue
git tag "pre-update-$DATE_STAMP" 2>$null
Write-Host "✓ Backup created" -ForegroundColor Green

Write-Host "▶ Checking for local changes..." -ForegroundColor Cyan
$changes = git status --porcelain
if ($changes) {
    Write-Host "  Local changes detected, stashing..." -ForegroundColor Yellow
    git stash save "Auto-stash before update $DATE_STAMP"
}

Write-Host "▶ Fetching updates..." -ForegroundColor Cyan
git fetch origin

Write-Host "▶ Current version:" -ForegroundColor Cyan
python -m src.main --version 2>$null

Write-Host "▶ Applying updates..." -ForegroundColor Cyan
git pull origin develop

Write-Host "▶ Updating dependencies..." -ForegroundColor Cyan
.\venv\Scripts\Activate
pip install --upgrade -r requirements.txt --quiet

Write-Host "▶ Restoring configuration..." -ForegroundColor Cyan
if (Test-Path "$BACKUP_DIR\config-$DATE_STAMP.yaml") {
    Copy-Item -Path "$BACKUP_DIR\config-$DATE_STAMP.yaml" -Destination "config\config.yaml" -Force
}

Write-Host "▶ New version:" -ForegroundColor Cyan
python -m src.main --version

Write-Host ""
Write-Host "✓ Update complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Backup location: $BACKUP_DIR" -ForegroundColor Gray
Write-Host "To rollback: git checkout pre-update-$DATE_STAMP" -ForegroundColor Gray
Write-Host ""
```

---

## Rollback Procedures

If an update causes issues, you can rollback to the previous version.

### Using Git Tags

```bash
# Mac/Linux
cd ~/vast-asbuilt-reporter

# List available backups
git tag | grep pre-update

# Rollback to specific tag
git checkout pre-update-20251017_143022

# Restore dependencies
source venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows
cd $env:USERPROFILE\vast-asbuilt-reporter

# List available backups
git tag | Select-String "pre-update"

# Rollback to specific tag
git checkout pre-update-20251017_143022

# Restore dependencies
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### Using Full Backup

```bash
# Mac/Linux
rm -rf ~/vast-asbuilt-reporter
cp -r ~/vast-asbuilt-reporter-backup-20251017 ~/vast-asbuilt-reporter
cd ~/vast-asbuilt-reporter
source venv/bin/activate
```

```powershell
# Windows
Remove-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter" -Recurse -Force
Copy-Item -Path "$env:USERPROFILE\vast-asbuilt-reporter-backup-20251017" -Destination "$env:USERPROFILE\vast-asbuilt-reporter" -Recurse
cd $env:USERPROFILE\vast-asbuilt-reporter
.\venv\Scripts\Activate
```

---

## Troubleshooting

### Merge Conflicts

If you encounter merge conflicts during `git pull`:

```bash
# View conflicts
git status

# Option 1: Keep your version
git checkout --ours config/config.yaml
git add config/config.yaml

# Option 2: Keep incoming version
git checkout --theirs config/config.yaml
git add config/config.yaml

# Option 3: Manually resolve
nano config/config.yaml  # Edit to resolve conflicts
git add config/config.yaml

# Complete merge
git commit
```

### Dependency Issues

If dependencies fail to install:

```bash
# Clear pip cache
pip cache purge

# Reinstall all dependencies
pip uninstall -y -r requirements.txt
pip install -r requirements.txt

# Or recreate virtual environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration Lost

If your configuration was overwritten:

```bash
# Restore from backup
cp ~/vast-asbuilt-reporter-backups/config-YYYYMMDD_HHMMSS.yaml config/config.yaml

# Or restore from git stash
git stash list
git show stash@{0}:config/config.yaml > config/config.yaml
```

---

## Version Compatibility

### Breaking Changes

Check the changelog for breaking changes before updating:

```bash
git log --oneline | grep -i "breaking\|BREAKING"
```

### Configuration Migration

Some updates may require configuration migration. Check for:

```bash
# Compare old and new config templates
diff ~/config-backup.yaml config/config.yaml.template
```

---

## Best Practices

1. **Always backup before updating**
2. **Test updates in development environment first**
3. **Read release notes and changelog**
4. **Update during maintenance windows**
5. **Verify after update**
6. **Keep backup for at least 30 days**

---

**Last Updated**: October 17, 2025
**Version**: 1.0.0
