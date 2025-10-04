# VAST As-Built Report Generator - Installation Guide

**For VAST Professional Services Engineers**

This guide provides step-by-step installation instructions for Mac and Windows laptops used by PS engineers.

## Table of Contents

1. [Quick Start](#quick-start)
2. [macOS Installation](#macos-installation)
3. [Windows Installation](#windows-installation)
4. [Post-Installation Setup](#post-installation-setup)
5. [Troubleshooting](#troubleshooting)
6. [Uninstallation](#uninstallation)

## Quick Start

### For Mac Users
```bash
# Download and run the installation script
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

### For Windows Users
```powershell
# Download and run the installation script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/install-windows.ps1" -OutFile "install-windows.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\install-windows.ps1
```

## macOS Installation

### Prerequisites

- **macOS Version**: 10.15 (Catalina) or later
- **Architecture**: Intel or Apple Silicon (M1/M2)
- **Internet Connection**: Required for downloading dependencies
- **Administrator Access**: Required for installing system packages

### Automated Installation (Recommended)

1. **Download the installation script:**
   ```bash
   curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/install-mac.sh
   ```

2. **Make the script executable:**
   ```bash
   chmod +x install-mac.sh
   ```

3. **Run the installation script:**
   ```bash
   ./install-mac.sh
   ```

4. **Follow the prompts** and wait for installation to complete.

### Manual Installation

If you prefer to install manually or the automated script fails:

#### Step 1: Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Step 2: Install Python
```bash
brew install python@3.12
```

#### Step 3: Install System Dependencies
```bash
brew install pango harfbuzz libffi libxml2 libxslt cairo gobject-introspection
```

#### Step 4: Clone Repository
```bash
git clone https://github.com/rstamps01/ps-deploy-report.git ~/vast-asbuilt-reporter
cd ~/vast-asbuilt-reporter
```

#### Step 5: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

#### Step 6: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 7: Setup Configuration
```bash
cp config/config.yaml.template config/config.yaml
mkdir -p output logs
```

### What Gets Installed

- **Python 3.12**: Latest stable Python version
- **Homebrew**: Package manager for macOS
- **System Dependencies**: Libraries required for PDF generation
- **Python Dependencies**: All required Python packages
- **Project Files**: Complete VAST As-Built Report Generator
- **Desktop Shortcut**: Easy access from desktop
- **Launch Script**: `run-vast-reporter.sh` for easy execution

### Installation Location

- **Project Directory**: `~/vast-asbuilt-reporter/`
- **Virtual Environment**: `~/vast-asbuilt-reporter/venv/`
- **Configuration**: `~/vast-asbuilt-reporter/config/config.yaml`
- **Logs**: `~/vast-asbuilt-reporter/logs/`
- **Output**: `~/vast-asbuilt-reporter/output/`

## Windows Installation

### Prerequisites

- **Windows Version**: Windows 10 or later
- **Architecture**: x64 or ARM64
- **Internet Connection**: Required for downloading dependencies
- **Administrator Access**: Required for installing system packages
- **PowerShell**: Version 5.1 or later

### Automated Installation (Recommended)

1. **Open PowerShell as Administrator:**
   - Right-click Start button → "Windows PowerShell (Admin)"
   - Or search "PowerShell" → Right-click → "Run as administrator"

2. **Set Execution Policy:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
   ```

3. **Download and run the installation script:**
   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/install-windows.ps1" -OutFile "install-windows.ps1"
   .\install-windows.ps1
   ```

4. **Follow the prompts** and wait for installation to complete.

### Manual Installation

If you prefer to install manually or the automated script fails:

#### Step 1: Install Chocolatey
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

#### Step 2: Install Python and Git
```powershell
choco install python312 git -y
```

#### Step 3: Install System Dependencies
```powershell
choco install vcredist-all 7zip -y
```

#### Step 4: Clone Repository
```powershell
git clone https://github.com/rstamps01/ps-deploy-report.git $env:USERPROFILE\vast-asbuilt-reporter
cd $env:USERPROFILE\vast-asbuilt-reporter
```

#### Step 5: Create Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

#### Step 6: Install Dependencies
```powershell
pip install -r requirements.txt
```

#### Step 7: Setup Configuration
```powershell
Copy-Item "config\config.yaml.template" "config\config.yaml"
New-Item -ItemType Directory -Path "output" -Force
New-Item -ItemType Directory -Path "logs" -Force
```

### What Gets Installed

- **Python 3.12**: Latest stable Python version
- **Chocolatey**: Package manager for Windows
- **Git**: Version control system
- **Visual C++ Redistributable**: Required for some Python packages
- **Python Dependencies**: All required Python packages
- **Project Files**: Complete VAST As-Built Report Generator
- **Desktop Shortcut**: Easy access from desktop
- **Start Menu Shortcut**: Available in Start Menu
- **Launch Scripts**: Both `.bat` and `.ps1` versions

### Installation Location

- **Project Directory**: `%USERPROFILE%\vast-asbuilt-reporter\`
- **Virtual Environment**: `%USERPROFILE%\vast-asbuilt-reporter\venv\`
- **Configuration**: `%USERPROFILE%\vast-asbuilt-reporter\config\config.yaml`
- **Logs**: `%USERPROFILE%\vast-asbuilt-reporter\logs\`
- **Output**: `%USERPROFILE%\vast-asbuilt-reporter\output\`

## Post-Installation Setup

### First Run

1. **Test the installation:**
   ```bash
   # macOS
   cd ~/vast-asbuilt-reporter
   ./run-vast-reporter.sh --version

   # Windows
   cd %USERPROFILE%\vast-asbuilt-reporter
   run-vast-reporter.bat --version
   ```

2. **Generate your first report:**
   ```bash
   # macOS
   ./run-vast-reporter.sh --cluster 192.168.1.100 --output ./output

   # Windows
   run-vast-reporter.bat --cluster 192.168.1.100 --output .\output
   ```

### Configuration

Edit the configuration file to customize settings:

**macOS:**
```bash
nano ~/vast-asbuilt-reporter/config/config.yaml
```

**Windows:**
```powershell
notepad $env:USERPROFILE\vast-asbuilt-reporter\config\config.yaml
```

### Environment Variables

Set up environment variables for easier credential management:

**macOS:**
```bash
# Add to ~/.zshrc or ~/.bash_profile
export VAST_USERNAME=admin
export VAST_PASSWORD=your_password
```

**Windows:**
```powershell
# Set user environment variables
[Environment]::SetEnvironmentVariable("VAST_USERNAME", "admin", "User")
[Environment]::SetEnvironmentVariable("VAST_PASSWORD", "your_password", "User")
```

### Desktop Shortcuts

After installation, you'll find shortcuts on your desktop:

- **macOS**: `VAST As-Built Reporter.command`
- **Windows**: `VAST As-Built Reporter.lnk`

Double-click these shortcuts to run the application with a graphical interface.

## Troubleshooting

### Common Issues

#### macOS Issues

**Problem**: `python3: command not found`
```bash
# Solution: Add Python to PATH
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Problem**: WeasyPrint installation fails
```bash
# Solution: Install system dependencies
brew install pango harfbuzz libffi libxml2 libxslt cairo gobject-introspection
```

**Problem**: Permission denied errors
```bash
# Solution: Fix permissions
chmod +x ~/vast-asbuilt-reporter/run-vast-reporter.sh
chmod +x ~/vast-asbuilt-reporter/venv/bin/python3
```

#### Windows Issues

**Problem**: PowerShell execution policy error
```powershell
# Solution: Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

**Problem**: Python not found in PATH
```powershell
# Solution: Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

**Problem**: Virtual environment activation fails
```powershell
# Solution: Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Getting Help

1. **Check the logs:**
   ```bash
   # macOS
   tail -f ~/vast-asbuilt-reporter/logs/vast_report_generator.log

   # Windows
   Get-Content $env:USERPROFILE\vast-asbuilt-reporter\logs\vast_report_generator.log -Tail 20
   ```

2. **Run diagnostics:**
   ```bash
   # macOS
   cd ~/vast-asbuilt-reporter
   ./run-vast-reporter.sh --help

   # Windows
   cd %USERPROFILE%\vast-asbuilt-reporter
   run-vast-reporter.bat --help
   ```

3. **Check system requirements:**
   ```bash
   # macOS
   python3 --version
   brew --version

   # Windows
   python --version
   choco --version
   ```

## Uninstallation

### macOS Uninstallation

1. **Remove the project directory:**
   ```bash
   rm -rf ~/vast-asbuilt-reporter
   ```

2. **Remove desktop shortcut:**
   ```bash
   rm ~/Desktop/VAST\ As-Built\ Reporter.command
   ```

3. **Remove Homebrew packages (optional):**
   ```bash
   brew uninstall python@3.12 pango harfbuzz libffi libxml2 libxslt cairo gobject-introspection
   ```

### Windows Uninstallation

1. **Remove the project directory:**
   ```powershell
   Remove-Item -Recurse -Force $env:USERPROFILE\vast-asbuilt-reporter
   ```

2. **Remove shortcuts:**
   ```powershell
   Remove-Item $env:USERPROFILE\Desktop\VAST\ As-Built\ Reporter.lnk
   Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\VAST As-Built Reporter.lnk"
   ```

3. **Remove Chocolatey packages (optional):**
   ```powershell
   choco uninstall python312 git vcredist-all 7zip
   ```

## Support

### Getting Help

- **GitHub Issues**: [https://github.com/rstamps01/ps-deploy-report/issues](https://github.com/rstamps01/ps-deploy-report/issues)
- **Documentation**: [README.md](README.md)
- **Troubleshooting Guide**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Reporting Issues

When reporting issues, please include:

1. **Operating System**: macOS version or Windows version
2. **Installation Method**: Automated script or manual installation
3. **Error Messages**: Complete error output
4. **Log Files**: Relevant log entries
5. **Steps to Reproduce**: What you were doing when the error occurred

---

**Version**: 1.0.0-dev
**Last Updated**: September 27, 2025
**Compatibility**: macOS 10.15+, Windows 10+, Python 3.8+
