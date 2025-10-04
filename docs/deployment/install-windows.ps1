# VAST As-Built Report Generator - Windows Installation Script
# For VAST Professional Services Engineers
# Version: 1.0.0-dev
# Date: September 27, 2025

# Enable strict error handling
$ErrorActionPreference = "Stop"

# Set up logging
$LogFile = "install-windows.log"
$LogPath = Join-Path $PSScriptRoot $LogFile

# Function to write to both console and log file
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Level] [$Timestamp] $Message"

    # Write to console with color
    Write-Host $LogMessage -ForegroundColor $Color

    # Write to log file
    Add-Content -Path $LogPath -Value $LogMessage -Encoding UTF8
}

# Function to handle errors gracefully
function Handle-Error {
    param(
        [string]$ErrorMessage,
        [string]$Command = "",
        [int]$LineNumber = 0
    )

    Write-Log "Installation failed" "ERROR" "Red"
    if ($Command) { Write-Log "Command that failed: $Command" "ERROR" "Red" }
    if ($LineNumber -gt 0) { Write-Log "Line number: $LineNumber" "ERROR" "Red" }
    Write-Log "Error details: $ErrorMessage" "ERROR" "Red"

    Write-Log "" "ERROR" "Red"
    Write-Log "TROUBLESHOOTING:" "ERROR" "Red"
    Write-Log "1. Check the log file: $LogPath" "ERROR" "Red"
    Write-Log "2. Ensure you have internet connectivity" "ERROR" "Red"
    Write-Log "3. Run PowerShell as Administrator" "ERROR" "Red"
    Write-Log "4. Check available disk space (requires ~1GB)" "ERROR" "Red"
    Write-Log "5. Try running: choco --version (if Chocolatey is installed)" "ERROR" "Red"

    # Cleanup on error
    Cleanup-OnError

    exit 1
}

# Function to cleanup on error
function Cleanup-OnError {
    Write-Log "Cleaning up after error..." "DEBUG" "Yellow"

    # Remove partial installations
    if (Test-Path "venv" -PathType Container) {
        if (-not (Test-Path "venv\pyvenv.cfg")) {
            Write-Log "Removing incomplete virtual environment..." "DEBUG" "Yellow"
            try {
                Remove-Item -Recurse -Force "venv" -ErrorAction SilentlyContinue
            } catch {
                Write-Log "Could not remove incomplete virtual environment" "WARNING" "Yellow"
            }
        }
    }

    # Remove partial downloads
    if (Test-Path "requirements.txt") {
        if ((Get-Item "requirements.txt").Length -eq 0) {
            Write-Log "Removing incomplete requirements file..." "DEBUG" "Yellow"
            try {
                Remove-Item "requirements.txt" -ErrorAction SilentlyContinue
            } catch {
                Write-Log "Could not remove incomplete requirements file" "WARNING" "Yellow"
            }
        }
    }
}

# Set up error handling
trap {
    Handle-Error -ErrorMessage $_.Exception.Message -Command $_.InvocationInfo.Line -LineNumber $_.InvocationInfo.ScriptLineNumber
}

# Set execution policy to allow script execution
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    Write-Log "Execution policy set successfully" "DEBUG" "Green"
} catch {
    Write-Log "Failed to set execution policy: $($_.Exception.Message)" "WARNING" "Yellow"
    Write-Log "You may need to run PowerShell as Administrator" "WARNING" "Yellow"
}

# Legacy function wrappers for backward compatibility
function Write-Status {
    param([string]$Message)
    Write-Log $Message "INFO" "Cyan"
}

function Write-Success {
    param([string]$Message)
    Write-Log $Message "SUCCESS" "Green"
}

function Write-Warning {
    param([string]$Message)
    Write-Log $Message "WARNING" "Yellow"
}

function Write-Error {
    param([string]$Message)
    Write-Log $Message "ERROR" "Red"
}

function Write-Debug {
    param([string]$Message)
    Write-Log $Message "DEBUG" "Gray"
}

# Function to check if command exists
function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check Windows version
function Test-WindowsVersion {
    Write-Status "Checking Windows version..."

    try {
        $osVersion = [System.Environment]::OSVersion.Version
        Write-Debug "Detected Windows version: $($osVersion.ToString())"

        $majorVersion = $osVersion.Major
        $minorVersion = $osVersion.Minor

        if ($majorVersion -lt 10) {
            Write-Error "Windows 10 or later is required. Current version: $($osVersion.ToString())"
            Write-Error "Please upgrade your Windows version and try again."
            exit 1
        }

        Write-Success "Windows version check passed: $($osVersion.ToString())"
    } catch {
        Write-Error "Failed to determine Windows version: $($_.Exception.Message)"
        exit 1
    }
}

# Function to install Chocolatey
function Install-Chocolatey {
    Write-Status "Checking Chocolatey installation..."

    if (Test-Command choco) {
        try {
            $chocoVersion = choco --version 2>$null
            Write-Success "Chocolatey is already installed: $chocoVersion"
            return
        } catch {
            Write-Warning "Chocolatey command exists but version check failed. Reinstalling..."
        }
    }

    Write-Status "Installing Chocolatey..."
    Write-Debug "Downloading Chocolatey installation script..."

    # Check internet connectivity
    try {
        $testConnection = Test-NetConnection -ComputerName "community.chocolatey.org" -Port 443 -InformationLevel Quiet
        if (-not $testConnection) {
            Write-Error "No internet connectivity. Please check your network connection."
            exit 1
        }
    } catch {
        Write-Warning "Could not test internet connectivity, proceeding with installation..."
    }

    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072

        Write-Debug "Executing Chocolatey installation script..."
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        # Verify Chocolatey installation
        if (-not (Test-Command choco)) {
            Write-Error "Chocolatey installation completed but 'choco' command not found in PATH"
            Write-Error "Please restart PowerShell and try again"
            exit 1
        }

        Write-Success "Chocolatey installed successfully"
    } catch {
        Write-Error "Chocolatey installation failed: $($_.Exception.Message)"
        Write-Error "Please check the log file for details: $LogPath"
        exit 1
    }
}

# Function to install Python
function Install-Python {
    if (Test-Command python) {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python 3\.(\d+)" -and [int]$matches[1] -ge 8) {
            Write-Success "Python is already installed: $pythonVersion"
            return
        }
    }

    Write-Status "Installing Python 3.12..."
    choco install python312 -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Success "Python 3.12 installed successfully"
}

# Function to install Git
function Install-Git {
    if (Test-Command git) {
        Write-Success "Git is already installed"
        return
    }

    Write-Status "Installing Git..."
    choco install git -y

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Success "Git installed successfully"
}

# Function to install system dependencies
function Install-SystemDependencies {
    Write-Status "Installing system dependencies for PDF generation..."

    # Install Visual C++ Redistributable
    choco install vcredist-all -y

    # Install additional dependencies
    choco install 7zip -y

    Write-Success "System dependencies installed successfully"
}

# Function to setup project
function Setup-Project {
    $projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"

    if (Test-Path $projectDir) {
        Write-Warning "Project directory already exists: $projectDir"
        $response = Read-Host "Do you want to update the existing installation? (y/N)"
        if ($response -notmatch "^[Yy]$") {
            Write-Status "Installation cancelled"
            exit 0
        }
        Write-Status "Updating existing installation..."
    } else {
        Write-Status "Creating project directory: $projectDir"
        New-Item -ItemType Directory -Path $projectDir -Force | Out-Null
    }

    Set-Location $projectDir

    # Clone or update repository
    if (Test-Path ".git") {
        Write-Status "Updating repository..."
        git pull origin develop
    } else {
        Write-Status "Cloning repository..."
        git clone -b develop https://github.com/rstamps01/ps-deploy-report.git .
    }

    Write-Success "Project setup completed"
}

# Function to create virtual environment
function New-VirtualEnvironment {
    Write-Status "Creating Python virtual environment..."

    # Remove existing virtual environment if it exists
    if (Test-Path "venv") {
        Write-Status "Removing existing virtual environment..."
        Remove-Item -Recurse -Force "venv"
    }

    # Create new virtual environment
    python -m venv venv

    # Activate virtual environment
    & ".\venv\Scripts\Activate.ps1"

    # Upgrade pip
    python -m pip install --upgrade pip

    Write-Success "Virtual environment created successfully"
}

# Function to install Python dependencies
function Install-PythonDependencies {
    Write-Status "Installing Python dependencies..."

    # Activate virtual environment
    & ".\venv\Scripts\Activate.ps1"

    # Install dependencies
    pip install -r requirements.txt

    Write-Success "Python dependencies installed successfully"
}

# Function to setup configuration
function Setup-Configuration {
    Write-Status "Setting up configuration..."

    # Copy configuration template
    if (-not (Test-Path "config\config.yaml")) {
        Copy-Item "config\config.yaml.template" "config\config.yaml"
        Write-Success "Configuration file created: config\config.yaml"
    } else {
        Write-Success "Configuration file already exists: config\config.yaml"
    }

    # Create output directory
    New-Item -ItemType Directory -Path "output" -Force | Out-Null
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null

    Write-Success "Configuration setup completed"
}

# Function to create launch script
function New-LaunchScript {
    Write-Status "Creating launch script..."

    $launchScript = @"
@echo off
REM VAST As-Built Report Generator Launch Script for Windows

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to the script directory
cd /d "%SCRIPT_DIR%"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application with provided arguments
python src\main.py %*

REM Pause to see output
pause
"@

    $launchScript | Out-File -FilePath "run-vast-reporter.bat" -Encoding ASCII

    Write-Success "Launch script created: run-vast-reporter.bat"
}

# Function to create PowerShell launch script
function New-PowerShellLaunchScript {
    Write-Status "Creating PowerShell launch script..."

    $psLaunchScript = @"
# VAST As-Built Report Generator PowerShell Launch Script

# Get the directory where this script is located
`$ScriptDir = Split-Path -Parent `$MyInvocation.MyCommand.Definition

# Change to the script directory
Set-Location `$ScriptDir

# Activate virtual environment
& ".\venv\Scripts\Activate.ps1"

# Run the application with provided arguments
python src\main.py `$args
"@

    $psLaunchScript | Out-File -FilePath "run-vast-reporter.ps1" -Encoding UTF8

    Write-Success "PowerShell launch script created: run-vast-reporter.ps1"
}

# Function to create desktop shortcut
function New-DesktopShortcut {
    Write-Status "Creating desktop shortcut..."

    $projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"
    $desktopPath = "$env:USERPROFILE\Desktop"
    $shortcutPath = "$desktopPath\VAST As-Built Reporter.lnk"
    $targetPath = "$projectDir\run-vast-reporter.bat"

    # Create WScript.Shell object
    $WshShell = New-Object -comObject WScript.Shell

    # Create shortcut
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $targetPath
    $Shortcut.WorkingDirectory = $projectDir
    $Shortcut.Description = "VAST As-Built Report Generator"
    $Shortcut.Save()

    Write-Success "Desktop shortcut created: VAST As-Built Reporter.lnk"
}

# Function to create Start Menu shortcut
function New-StartMenuShortcut {
    Write-Status "Creating Start Menu shortcut..."

    $projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"
    $startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    $shortcutPath = "$startMenuPath\VAST As-Built Reporter.lnk"
    $targetPath = "$projectDir\run-vast-reporter.bat"

    # Create WScript.Shell object
    $WshShell = New-Object -comObject WScript.Shell

    # Create shortcut
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $targetPath
    $Shortcut.WorkingDirectory = $projectDir
    $Shortcut.Description = "VAST As-Built Report Generator"
    $Shortcut.Save()

    Write-Success "Start Menu shortcut created"
}

# Function to test installation
function Test-Installation {
    Write-Status "Testing installation..."

    # Activate virtual environment
    & ".\venv\Scripts\Activate.ps1"

    # Test Python version
    $pythonVersion = python --version
    Write-Success "Python version: $pythonVersion"

    # Test application version
    try {
        $appVersion = python src\main.py --version 2>$null | Select-String -Pattern '\d+\.\d+\.\d+' | ForEach-Object { $_.Matches[0].Value }
        Write-Success "Application version: $appVersion"
    } catch {
        Write-Warning "Could not determine application version"
    }

    # Test help command
    try {
        python src\main.py --help | Out-Null
        Write-Success "Application help command working"
    } catch {
        Write-Error "Application help command failed"
        return $false
    }

    Write-Success "Installation test completed successfully"
    return $true
}

# Function to display usage instructions
function Show-UsageInstructions {
    $projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"

    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host "VAST AS-BUILT REPORT GENERATOR - INSTALLATION COMPLETE" -ForegroundColor $Blue
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Installation Location: $projectDir" -ForegroundColor $Green
    Write-Host ""
    Write-Host "USAGE INSTRUCTIONS:" -ForegroundColor $Yellow
    Write-Host "===================" -ForegroundColor $Yellow
    Write-Host ""
    Write-Host "1. Using the Desktop Shortcut:" -ForegroundColor $Green
    Write-Host "   - Double-click 'VAST As-Built Reporter.lnk' on your desktop" -ForegroundColor $Green
    Write-Host "   - Follow the prompts to enter cluster IP and credentials" -ForegroundColor $Green
    Write-Host ""
    Write-Host "2. Using Command Prompt:" -ForegroundColor $Green
    Write-Host "   cd $projectDir" -ForegroundColor $Green
    Write-Host "   run-vast-reporter.bat --cluster <CLUSTER_IP> --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "3. Using PowerShell:" -ForegroundColor $Green
    Write-Host "   cd $projectDir" -ForegroundColor $Green
    Write-Host "   .\run-vast-reporter.ps1 --cluster <CLUSTER_IP> --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "4. Direct Python execution:" -ForegroundColor $Green
    Write-Host "   cd $projectDir" -ForegroundColor $Green
    Write-Host "   .\venv\Scripts\activate.bat" -ForegroundColor $Green
    Write-Host "   python src\main.py --cluster <CLUSTER_IP> --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "EXAMPLE COMMANDS:" -ForegroundColor $Yellow
    Write-Host "=================" -ForegroundColor $Yellow
    Write-Host "   # Basic usage with interactive credentials" -ForegroundColor $Green
    Write-Host "   run-vast-reporter.bat --cluster 192.168.1.100 --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "   # Using environment variables" -ForegroundColor $Green
    Write-Host "   set VAST_USERNAME=admin" -ForegroundColor $Green
    Write-Host "   set VAST_PASSWORD=your_password" -ForegroundColor $Green
    Write-Host "   run-vast-reporter.bat --cluster 192.168.1.100 --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "   # Verbose output for debugging" -ForegroundColor $Green
    Write-Host "   run-vast-reporter.bat --cluster 192.168.1.100 --output .\output --verbose" -ForegroundColor $Green
    Write-Host ""
    Write-Host "CONFIGURATION:" -ForegroundColor $Yellow
    Write-Host "==============" -ForegroundColor $Yellow
    Write-Host "   Edit: $projectDir\config\config.yaml" -ForegroundColor $Green
    Write-Host "   Logs: $projectDir\logs\vast_report_generator.log" -ForegroundColor $Green
    Write-Host "   Output: $projectDir\output\" -ForegroundColor $Green
    Write-Host ""
    Write-Host "SUPPORT:" -ForegroundColor $Yellow
    Write-Host "========" -ForegroundColor $Yellow
    Write-Host "   - Check logs: Get-Content $projectDir\logs\vast_report_generator.log -Tail 20" -ForegroundColor $Green
    Write-Host "   - View help: run-vast-reporter.bat --help" -ForegroundColor $Green
    Write-Host "   - GitHub: https://github.com/rstamps01/ps-deploy-report" -ForegroundColor $Green
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor $Blue
}

# Function to display installation summary
function Show-InstallationSummary {
    $projectDir = "$env:USERPROFILE\vast-asbuilt-reporter"

    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host "INSTALLATION SUMMARY" -ForegroundColor $Blue
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host ""
    Write-Success "Installation completed successfully!"
    Write-Host ""
    Write-Host "📁 Installation Location: $projectDir" -ForegroundColor $Green
    Write-Host "📋 Log File: $LogPath" -ForegroundColor $Green
    Write-Host "🐍 Python Version: $(try { python --version 2>$null } catch { 'Not found' })" -ForegroundColor $Green
    Write-Host "🍫 Chocolatey Version: $(try { choco --version 2>$null } catch { 'Not found' })" -ForegroundColor $Green
    Write-Host "📦 Virtual Environment: $projectDir\venv" -ForegroundColor $Green
    Write-Host "⚙️  Configuration: $projectDir\config\config.yaml" -ForegroundColor $Green
    Write-Host "📊 Output Directory: $projectDir\output" -ForegroundColor $Green
    Write-Host "📝 Logs Directory: $projectDir\logs" -ForegroundColor $Green
    Write-Host ""
    Write-Host "🚀 Quick Start:" -ForegroundColor $Yellow
    Write-Host "   cd $projectDir" -ForegroundColor $Green
    Write-Host "   run-vast-reporter.bat --cluster <CLUSTER_IP> --output .\output" -ForegroundColor $Green
    Write-Host ""
    Write-Host "📖 Documentation:" -ForegroundColor $Yellow
    Write-Host "   - README.md: Complete usage guide" -ForegroundColor $Green
    Write-Host "   - INSTALLATION-GUIDE.md: Detailed installation instructions" -ForegroundColor $Green
    Write-Host "   - TROUBLESHOOTING.md: Common issues and solutions" -ForegroundColor $Green
    Write-Host ""
    Write-Host "🆘 Support:" -ForegroundColor $Yellow
    Write-Host "   - GitHub: https://github.com/rstamps01/ps-deploy-report" -ForegroundColor $Green
    Write-Host "   - Logs: Get-Content $LogPath -Tail 20" -ForegroundColor $Green
    Write-Host "   - Help: run-vast-reporter.bat --help" -ForegroundColor $Green
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor $Blue
}

# Main installation function
function Main {
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host "VAST AS-BUILT REPORT GENERATOR - WINDOWS INSTALLATION" -ForegroundColor $Blue
    Write-Host "==================================================================" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "This script will install the VAST As-Built Report Generator on your Windows PC." -ForegroundColor $Green
    Write-Host "The installation includes Python, dependencies, and creates shortcuts." -ForegroundColor $Green
    Write-Host ""
    Write-Host "📋 Installation will be logged to: $LogPath" -ForegroundColor $Yellow
    Write-Host ""
    $response = Read-Host "Do you want to continue? (Y/n)"
    if ($response -notmatch "^[Yy]$" -and $response -ne "") {
        Write-Status "Installation cancelled by user"
        exit 0
    }

    # Check Windows version
    Test-WindowsVersion

    # Install Chocolatey
    Install-Chocolatey

    # Install Git
    Install-Git

    # Install Python
    Install-Python

    # Install system dependencies
    Install-SystemDependencies

    # Setup project
    Setup-Project

    # Create virtual environment
    New-VirtualEnvironment

    # Install Python dependencies
    Install-PythonDependencies

    # Setup configuration
    Setup-Configuration

    # Create launch scripts
    New-LaunchScript
    New-PowerShellLaunchScript

    # Create shortcuts
    New-DesktopShortcut
    New-StartMenuShortcut

    # Test installation
    if (Test-Installation) {
        # Display installation summary
        Show-InstallationSummary
    } else {
        Write-Error "Installation test failed. Please check the logs and try again."
        exit 1
    }
}

# Run main function
Main
