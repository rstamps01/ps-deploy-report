# VAST As-Built Report Generator - Uninstallation Guide

## Table of Contents

1. [Overview](#overview)
2. [Before You Uninstall](#before-you-uninstall)
3. [Automated Uninstallation](#automated-uninstallation)
4. [Manual Uninstallation](#manual-uninstallation)
5. [Partial Uninstallation](#partial-uninstallation)
6. [Troubleshooting](#troubleshooting)
7. [Complete Removal Verification](#complete-removal-verification)

---

## Overview

This guide provides comprehensive instructions for uninstalling the VAST As-Built Report Generator from your system. You can choose between automated scripts or manual procedures based on your preference.

### What Gets Removed

A complete uninstallation removes:
- ✓ Application source code
- ✓ Python virtual environment
- ✓ Installed dependencies
- ✓ Shell configurations (optional)
- ✓ Symlinks and shortcuts (optional)
- ✓ Environment variables (optional)

### What Can Be Preserved

You can optionally preserve:
- Reports and output files
- Log files
- Configuration files
- User data backups

---

## Before You Uninstall

### 1. Backup Important Data

**Reports and Output**:
```bash
# Mac/Linux
cp -r ~/vast-reporter/reports ~/vast-reporter-backup/
cp -r ~/vast-reporter/output ~/vast-reporter-backup/

# Windows PowerShell
Copy-Item -Path "$env:USERPROFILE\vast-reporter\reports" -Destination "$env:USERPROFILE\vast-reporter-backup\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-reporter\output" -Destination "$env:USERPROFILE\vast-reporter-backup\" -Recurse
```

**Configuration Files**:
```bash
# Mac/Linux
cp ~/vast-reporter/config/config.yaml ~/vast-reporter-backup/

# Windows PowerShell
Copy-Item -Path "$env:USERPROFILE\vast-reporter\config\config.yaml" -Destination "$env:USERPROFILE\vast-reporter-backup\"
```

### 2. Stop Running Processes

```bash
# Mac/Linux
pkill -f "src.main"

# Windows PowerShell
Get-Process -Name "python*" | Where-Object { $_.CommandLine -like "*src.main*" } | Stop-Process -Force
```

### 3. Deactivate Virtual Environment

If you have an active virtual environment:

```bash
# Mac/Linux
deactivate

# Windows
deactivate
```

---

## Automated Uninstallation

### macOS Automated Uninstall

**1. Download the uninstall script:**
```bash
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/uninstall-mac.sh
chmod +x uninstall-mac.sh
```

**2. Run the script:**
```bash
./uninstall-mac.sh
```

**3. Follow the prompts:**
- Confirm uninstallation location
- Choose whether to backup data
- Select optional cleanup items

**Features:**
- ✓ Automatic installation detection
- ✓ Optional data backup
- ✓ Safe removal of all components
- ✓ Interactive confirmation prompts
- ✓ Detailed progress reporting

### Windows Automated Uninstall

**1. Download the uninstall script:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/uninstall-windows.ps1" -OutFile "uninstall-windows.ps1"
```

**2. Set execution policy (if needed):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

**3. Run the script:**
```powershell
.\uninstall-windows.ps1
```

**4. Follow the prompts:**
- Confirm uninstallation location
- Choose whether to backup data
- Select optional cleanup items

**Features:**
- ✓ Automatic installation detection
- ✓ Optional data backup
- ✓ Environment variable cleanup
- ✓ Shortcut removal
- ✓ Scheduled task removal

---

## Manual Uninstallation

### macOS/Linux Manual Uninstall

**Step 1: Stop running processes**
```bash
pkill -f "src.main"
```

**Step 2: Deactivate virtual environment**
```bash
# If currently active
deactivate
```

**Step 3: Remove installation directory**
```bash
# Default location
rm -rf ~/vast-reporter

# Or custom location
rm -rf /path/to/custom/installation
```

**Step 4: Clean shell configurations (optional)**

Edit your shell configuration file:
```bash
# For bash
nano ~/.bashrc
nano ~/.bash_profile

# For zsh
nano ~/.zshrc
```

Remove any lines containing `vast-reporter` such as:
- Aliases
- PATH modifications
- Environment variables

**Step 5: Remove symlinks (optional)**
```bash
# Check common locations
rm -f ~/bin/vast-reporter
rm -f ~/.local/bin/vast-reporter
sudo rm -f /usr/local/bin/vast-reporter  # Requires sudo
```

**Step 6: Clean system logs (optional)**
```bash
sudo rm -rf /var/log/vast-reporter  # Requires sudo
```

**Step 7: Reload shell configuration**
```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc
```

### Windows Manual Uninstall

**Step 1: Stop running processes**
```powershell
Get-Process -Name "python*" | Where-Object { $_.CommandLine -like "*src.main*" } | Stop-Process -Force
```

**Step 2: Deactivate virtual environment**
```powershell
deactivate
```

**Step 3: Remove installation directory**
```powershell
# Default location
Remove-Item -Path "$env:USERPROFILE\vast-reporter" -Recurse -Force

# Or custom location
Remove-Item -Path "C:\path\to\custom\installation" -Recurse -Force
```

**Step 4: Clean environment variables (optional)**

```powershell
# Remove from PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = ($userPath -split ';' | Where-Object { $_ -notlike "*vast-reporter*" }) -join ';'
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")

# Remove VAST_* variables
[Environment]::GetEnvironmentVariables("User").Keys |
    Where-Object { $_ -like "VAST_*" } |
    ForEach-Object { [Environment]::SetEnvironmentVariable($_, $null, "User") }
```

**Step 5: Remove shortcuts (optional)**

```powershell
# Start Menu
Remove-Item -Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\VAST Reporter" -Recurse -Force -ErrorAction SilentlyContinue

# Desktop
$desktopPath = [Environment]::GetFolderPath("Desktop")
Get-ChildItem -Path $desktopPath -Filter "*vast*reporter*.lnk" | Remove-Item -Force
```

**Step 6: Remove scheduled tasks (optional)**

```powershell
Get-ScheduledTask -TaskPath "\*" |
    Where-Object { $_.TaskName -like "*vast*reporter*" } |
    Unregister-ScheduledTask -Confirm:$false
```

**Step 7: Restart terminal**

Close and reopen PowerShell or terminal to apply environment changes.

---

## Partial Uninstallation

### Keep Reports and Data

If you want to remove the application but keep your reports:

**macOS/Linux:**
```bash
# Backup reports and data
cp -r ~/vast-reporter/reports ~/vast-reports-archive/
cp -r ~/vast-reporter/output ~/vast-reports-archive/
cp ~/vast-reporter/config/config.yaml ~/vast-reports-archive/

# Remove application
rm -rf ~/vast-reporter/venv
rm -rf ~/vast-reporter/src
rm -rf ~/vast-reporter/.git
```

**Windows:**
```powershell
# Backup reports and data
Copy-Item -Path "$env:USERPROFILE\vast-reporter\reports" -Destination "$env:USERPROFILE\vast-reports-archive\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-reporter\output" -Destination "$env:USERPROFILE\vast-reports-archive\" -Recurse
Copy-Item -Path "$env:USERPROFILE\vast-reporter\config\config.yaml" -Destination "$env:USERPROFILE\vast-reports-archive\"

# Remove application
Remove-Item -Path "$env:USERPROFILE\vast-reporter\venv" -Recurse -Force
Remove-Item -Path "$env:USERPROFILE\vast-reporter\src" -Recurse -Force
Remove-Item -Path "$env:USERPROFILE\vast-reporter\.git" -Recurse -Force
```

### Remove Only Virtual Environment

To reinstall with a clean Python environment:

```bash
# Mac/Linux
deactivate  # If active
rm -rf ~/vast-reporter/venv

# Windows
deactivate  # If active
Remove-Item -Path "$env:USERPROFILE\vast-reporter\venv" -Recurse -Force
```

Then recreate:
```bash
# Mac/Linux
cd ~/vast-reporter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Windows
cd $env:USERPROFILE\vast-reporter
python -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

---

## Troubleshooting

### Permission Denied Errors

**Issue**: Cannot remove files due to permission errors

**Solution (Mac/Linux)**:
```bash
# Check file permissions
ls -la ~/vast-reporter

# Change ownership if needed
sudo chown -R $USER:$USER ~/vast-reporter

# Try removal again
rm -rf ~/vast-reporter
```

**Solution (Windows)**:
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → "Run as Administrator"

# Take ownership
takeown /f "$env:USERPROFILE\vast-reporter" /r /d y
icacls "$env:USERPROFILE\vast-reporter" /grant "$env:USERNAME:F" /t

# Try removal again
Remove-Item -Path "$env:USERPROFILE\vast-reporter" -Recurse -Force
```

### Directory Not Empty Errors

**Issue**: Cannot remove directory because it's not empty

**Solution**:
```bash
# Mac/Linux - Force removal
rm -rf ~/vast-reporter

# Windows - Force removal
Remove-Item -Path "$env:USERPROFILE\vast-reporter" -Recurse -Force -ErrorAction SilentlyContinue
```

### Process Still Running

**Issue**: Files in use by running process

**Solution (Mac/Linux)**:
```bash
# Find processes
ps aux | grep "src.main"

# Kill specific process
kill -9 <PID>

# Or kill all python processes (use caution!)
pkill -9 python3
```

**Solution (Windows)**:
```powershell
# Find processes
Get-Process | Where-Object { $_.ProcessName -like "*python*" }

# Kill processes
Get-Process -Name "python*" | Stop-Process -Force
```

### Virtual Environment Active

**Issue**: Cannot remove while venv is active

**Solution**:
```bash
# Deactivate first
deactivate

# Then proceed with uninstallation
```

### Symlink Removal Requires Sudo

**Issue**: Cannot remove system-wide symlinks

**Solution (Mac/Linux)**:
```bash
# Use sudo for system directories
sudo rm -f /usr/local/bin/vast-reporter

# Or change to user-local location
rm -f ~/.local/bin/vast-reporter
```

---

## Complete Removal Verification

### Verify Uninstallation

**Check installation directory:**
```bash
# Mac/Linux
ls -la ~/vast-reporter  # Should not exist

# Windows
Test-Path "$env:USERPROFILE\vast-reporter"  # Should return False
```

**Check running processes:**
```bash
# Mac/Linux
ps aux | grep "src.main"  # Should return nothing

# Windows
Get-Process -Name "python*" | Where-Object { $_.CommandLine -like "*src.main*" }  # Should return nothing
```

**Check PATH:**
```bash
# Mac/Linux
echo $PATH | grep vast-reporter  # Should return nothing

# Windows
[Environment]::GetEnvironmentVariable("Path", "User") -split ';' | Where-Object { $_ -like "*vast-reporter*" }  # Should return nothing
```

**Check command availability:**
```bash
# Should return "command not found" or similar
python3 -m src.main --version
vast-reporter --version
```

---

## Post-Uninstallation Cleanup

### Optional: Remove Python (if installed only for VAST)

**macOS (if installed via Homebrew):**
```bash
brew uninstall python@3.12
```

**Windows:**
- Go to "Settings" → "Apps" → "Apps & features"
- Find "Python 3.x"
- Click "Uninstall"

### Optional: Remove Git (if installed only for VAST)

**macOS (if installed via Homebrew):**
```bash
brew uninstall git
```

**Windows:**
- Go to "Settings" → "Apps" → "Apps & features"
- Find "Git"
- Click "Uninstall"

---

## Backup Recovery

If you need to restore from backup after uninstallation:

**Restore reports:**
```bash
# Mac/Linux
cp -r ~/vast-reporter-backup/reports ~/new-location/

# Windows
Copy-Item -Path "$env:USERPROFILE\vast-reporter-backup\reports" -Destination "$env:USERPROFILE\new-location\" -Recurse
```

**Restore configuration:**
```bash
# Mac/Linux
cp ~/vast-reporter-backup/config.yaml ~/new-location/config/

# Windows
Copy-Item -Path "$env:USERPROFILE\vast-reporter-backup\config.yaml" -Destination "$env:USERPROFILE\new-location\config\"
```

---

## Support

If you encounter issues during uninstallation:

1. **Check the logs** for error messages
2. **Review this guide** for troubleshooting steps
3. **Try manual uninstallation** if automated fails
4. **Use force flags** for stubborn files/directories
5. **Contact support** if problems persist

---

## Re-installation

To re-install after uninstallation, follow the [Installation Guide](INSTALLATION-GUIDE.md).

---

**Last Updated**: October 17, 2025
**Version**: 1.0.0
