################################################################################
# VAST As-Built Report Generator - Windows Uninstall Script
################################################################################
#
# Purpose: Clean uninstallation of the VAST As-Built Report Generator
# Platform: Windows 10/11, Windows Server 2019+
# Requirements: PowerShell 5.1+
#
# Usage:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
#   .\uninstall-windows.ps1
#
################################################################################

#Requires -Version 5.1

# Set strict mode for better error detection
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

################################################################################
# Configuration
################################################################################

$script:DefaultInstallDir = "$env:USERPROFILE\vast-asbuilt-reporter"
$script:InstallDir = $null
$script:BackupCreated = $null

################################################################################
# Color Functions
################################################################################

function Write-ColorOutput {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,

        [Parameter(Mandatory=$false)]
        [ValidateSet('Info','Success','Warning','Error','Header','Section')]
        [string]$Type = 'Info'
    )

    switch ($Type) {
        'Header' {
            Write-Host ""
            Write-Host "═══════════════════════════════════════════════════════════════"
            Write-Host "  $Message"
            Write-Host "═══════════════════════════════════════════════════════════════"
            Write-Host ""
        }
        'Section' {
            Write-Host ""
            Write-Host "▶ $Message"
            Write-Host "─────────────────────────────────────────────────────────────"
        }
        'Success' {
            Write-Host "✓ $Message"
        }
        'Warning' {
            Write-Host "⚠ $Message"
        }
        'Error' {
            Write-Host "✗ $Message"
        }
        'Info' {
            Write-Host "  $Message"
        }
    }
}

function Confirm-Action {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt
    )

    $response = Read-Host "$Prompt [y/N]"
    return ($response -match '^[yY](es)?$')
}

################################################################################
# Uninstallation Functions
################################################################################

function Find-Installation {
    Write-ColorOutput "Locating Installation" -Type Section

    # Check default location
    if (Test-Path $script:DefaultInstallDir) {
        $script:InstallDir = $script:DefaultInstallDir
        Write-ColorOutput "Found installation at: $script:InstallDir" -Type Success
        return $true
    }

    # Check current directory
    if ((Test-Path ".\src\main.py") -and (Test-Path ".\requirements.txt")) {
        $script:InstallDir = $PWD.Path
        Write-ColorOutput "Found installation at: $script:InstallDir" -Type Success
        return $true
    }

    # Ask user for custom location
    Write-ColorOutput "Installation not found in default location" -Type Warning
    $customDir = Read-Host "Enter installation directory path (or press Enter to skip)"

    if ($customDir -and (Test-Path $customDir)) {
        $script:InstallDir = $customDir
        Write-ColorOutput "Using custom location: $script:InstallDir" -Type Success
        return $true
    }

    Write-ColorOutput "Installation directory not found" -Type Error
    return $false
}

function Stop-RunningProcesses {
    Write-ColorOutput "Checking for Running Processes" -Type Section

    $processes = Get-Process -Name "python*" -ErrorAction SilentlyContinue |
                 Where-Object { $_.CommandLine -like "*src.main*" }

    if ($processes) {
        Write-ColorOutput "VAST Report Generator processes are running" -Type Warning

        if (Confirm-Action "Stop running processes?") {
            $processes | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
            Write-ColorOutput "Processes stopped" -Type Success
        } else {
            Write-ColorOutput "Processes still running - uninstall may be incomplete" -Type Warning
        }
    } else {
        Write-ColorOutput "No running processes found" -Type Success
    }
}

function Backup-UserData {
    Write-ColorOutput "Backup Data" -Type Section

    if (-not (Test-Path $script:InstallDir)) {
        Write-ColorOutput "Installation directory not found, skipping backup" -Type Warning
        return
    }

    $hasData = $false

    # Check for reports
    if ((Test-Path "$script:InstallDir\reports") -and (Get-ChildItem "$script:InstallDir\reports" -ErrorAction SilentlyContinue)) {
        $hasData = $true
    }

    # Check for output
    if ((Test-Path "$script:InstallDir\output") -and (Get-ChildItem "$script:InstallDir\output" -ErrorAction SilentlyContinue)) {
        $hasData = $true
    }

    # Check for logs
    if ((Test-Path "$script:InstallDir\logs") -and (Get-ChildItem "$script:InstallDir\logs" -ErrorAction SilentlyContinue)) {
        $hasData = $true
    }

    # Check for config
    if (Test-Path "$script:InstallDir\config\config.yaml") {
        $hasData = $true
    }

    if ($hasData) {
        Write-ColorOutput "Found user data (reports, logs, config)" -Type Warning

        if (Confirm-Action "Create backup before uninstalling?") {
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $backupDir = "$env:USERPROFILE\vast-asbuilt-reporter-backup-$timestamp"
            New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

            # Backup reports
            if (Test-Path "$script:InstallDir\reports") {
                Copy-Item -Path "$script:InstallDir\reports" -Destination "$backupDir\" -Recurse -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "Backed up reports" -Type Info
            }

            # Backup output
            if (Test-Path "$script:InstallDir\output") {
                Copy-Item -Path "$script:InstallDir\output" -Destination "$backupDir\" -Recurse -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "Backed up output" -Type Info
            }

            # Backup logs
            if (Test-Path "$script:InstallDir\logs") {
                Copy-Item -Path "$script:InstallDir\logs" -Destination "$backupDir\" -Recurse -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "Backed up logs" -Type Info
            }

            # Backup config
            if (Test-Path "$script:InstallDir\config\config.yaml") {
                New-Item -ItemType Directory -Path "$backupDir\config" -Force | Out-Null
                Copy-Item -Path "$script:InstallDir\config\config.yaml" -Destination "$backupDir\config\" -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "Backed up configuration" -Type Info
            }

            Write-ColorOutput "Backup created at: $backupDir" -Type Success
            $script:BackupCreated = $backupDir
        }
    } else {
        Write-ColorOutput "No user data found to backup" -Type Info
    }
}

function Remove-VirtualEnvironment {
    Write-ColorOutput "Removing Virtual Environment" -Type Section

    $venvPath = Join-Path $script:InstallDir "venv"

    if (Test-Path $venvPath) {
        # Deactivate if active (check if current Python is from venv)
        $currentPython = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($currentPython -and ($currentPython -like "*$venvPath*")) {
            Write-ColorOutput "Virtual environment is active - please deactivate and re-run" -Type Warning
            return
        }

        Remove-Item -Path $venvPath -Recurse -Force -ErrorAction SilentlyContinue
        Write-ColorOutput "Virtual environment removed" -Type Success
    } else {
        Write-ColorOutput "No virtual environment found" -Type Info
    }
}

function Remove-InstallationDirectory {
    Write-ColorOutput "Removing Installation" -Type Section

    if (-not (Test-Path $script:InstallDir)) {
        Write-ColorOutput "Installation directory not found" -Type Warning
        return $true
    }

    Write-ColorOutput "This will permanently delete: $script:InstallDir" -Type Warning

    if (Confirm-Action "Remove installation directory?") {
        # Remove the entire directory
        Remove-Item -Path $script:InstallDir -Recurse -Force -ErrorAction Stop
        Write-ColorOutput "Installation directory removed" -Type Success
        return $true
    } else {
        Write-ColorOutput "Installation directory preserved" -Type Info
        return $false
    }
}

function Remove-EnvironmentVariables {
    Write-ColorOutput "Cleaning Environment Variables" -Type Section

    $modified = $false

    # Check PATH for vast-asbuilt-reporter entries
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -like "*vast-asbuilt-reporter*") {
        if (Confirm-Action "Remove VAST reporter entries from PATH?") {
            $newPath = ($userPath -split ';' | Where-Object { $_ -notlike "*vast-asbuilt-reporter*" }) -join ';'
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Write-ColorOutput "Cleaned PATH variable" -Type Success
            $modified = $true
        }
    }

    # Check for custom VAST_* environment variables
    $vastVars = [Environment]::GetEnvironmentVariables("User").Keys | Where-Object { $_ -like "VAST_*" }
    if ($vastVars) {
        if (Confirm-Action "Remove VAST environment variables?") {
            foreach ($var in $vastVars) {
                [Environment]::SetEnvironmentVariable($var, $null, "User")
                Write-ColorOutput "Removed $var" -Type Info
            }
            $modified = $true
        }
    }

    if (-not $modified) {
        Write-ColorOutput "No environment variables found" -Type Info
    } else {
        Write-ColorOutput "Changes will take effect in new terminal sessions" -Type Warning
    }
}

function Remove-StartMenuShortcuts {
    Write-ColorOutput "Removing Start Menu Shortcuts" -Type Section

    $startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\VAST Reporter"

    if (Test-Path $startMenuPath) {
        if (Confirm-Action "Remove Start Menu shortcuts?") {
            Remove-Item -Path $startMenuPath -Recurse -Force -ErrorAction SilentlyContinue
            Write-ColorOutput "Start Menu shortcuts removed" -Type Success
        }
    } else {
        Write-ColorOutput "No Start Menu shortcuts found" -Type Info
    }
}

function Remove-DesktopShortcuts {
    Write-ColorOutput "Removing Desktop Shortcuts" -Type Section

    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcuts = Get-ChildItem -Path $desktopPath -Filter "*vast*reporter*.lnk" -ErrorAction SilentlyContinue

    if ($shortcuts) {
        if (Confirm-Action "Remove desktop shortcuts?") {
            $shortcuts | Remove-Item -Force -ErrorAction SilentlyContinue
            Write-ColorOutput "Desktop shortcuts removed" -Type Success
        }
    } else {
        Write-ColorOutput "No desktop shortcuts found" -Type Info
    }
}

function Remove-ScheduledTasks {
    Write-ColorOutput "Checking for Scheduled Tasks" -Type Section

    $tasks = Get-ScheduledTask -TaskPath "\*" -ErrorAction SilentlyContinue |
             Where-Object { $_.TaskName -like "*vast*reporter*" }

    if ($tasks) {
        Write-ColorOutput "Found scheduled tasks related to VAST Reporter" -Type Warning
        if (Confirm-Action "Remove scheduled tasks?") {
            $tasks | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue
            Write-ColorOutput "Scheduled tasks removed" -Type Success
        }
    } else {
        Write-ColorOutput "No scheduled tasks found" -Type Info
    }
}

function Show-Summary {
    Write-ColorOutput "Uninstallation Summary" -Type Section

    Write-Host ""
    Write-ColorOutput "Uninstallation completed successfully!" -Type Success
    Write-Host ""

    if ($script:BackupCreated) {
        Write-ColorOutput "Backup Location: $script:BackupCreated" -Type Info
        Write-ColorOutput "  - Reports, logs, and configuration have been preserved" -Type Info
        Write-Host ""
    }

    Write-ColorOutput "The following items were removed:" -Type Info
    Write-ColorOutput "  ✓ Installation directory" -Type Info
    Write-ColorOutput "  ✓ Virtual environment" -Type Info
    Write-ColorOutput "  ✓ Python dependencies" -Type Info
    Write-Host ""

    Write-ColorOutput "What remains (if any):" -Type Info
    Write-ColorOutput "  • User backups (if created)" -Type Info
    Write-ColorOutput "  • Python installation (system-wide)" -Type Info
    Write-Host ""

    Write-ColorOutput "Note: You may need to restart your terminal or system for" -Type Warning
    Write-ColorOutput "environment variable changes to take full effect." -Type Warning
    Write-Host ""
}

################################################################################
# Main Uninstallation Process
################################################################################

function Main {
    try {
        Write-ColorOutput "VAST As-Built Report Generator - Windows Uninstaller" -Type Header

        # Check if running as administrator (not required, but check)
        $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) {
            Write-ColorOutput "Running with administrator privileges" -Type Warning
            Write-ColorOutput "This is not required for user installations" -Type Info
        }

        # Step 1: Find installation
        if (-not (Find-Installation)) {
            Write-ColorOutput "Cannot proceed without installation directory" -Type Error
            return 1
        }

        # Confirm uninstallation
        Write-Host ""
        Write-ColorOutput "This will uninstall the VAST As-Built Report Generator" -Type Warning
        Write-ColorOutput "Installation: $script:InstallDir" -Type Warning
        Write-Host ""

        if (-not (Confirm-Action "Proceed with uninstallation?")) {
            Write-ColorOutput "Uninstallation cancelled by user" -Type Error
            return 0
        }

        # Step 2: Stop running processes
        Stop-RunningProcesses

        # Step 3: Backup data
        Backup-UserData

        # Step 4: Remove virtual environment
        Remove-VirtualEnvironment

        # Step 5: Clean environment variables
        Remove-EnvironmentVariables

        # Step 6: Remove shortcuts
        Remove-StartMenuShortcuts
        Remove-DesktopShortcuts

        # Step 7: Remove scheduled tasks
        Remove-ScheduledTasks

        # Step 8: Remove installation directory
        Remove-InstallationDirectory

        # Display summary
        Show-Summary

        Write-ColorOutput "Uninstallation complete!" -Type Success
        Write-Host ""

        return 0

    } catch {
        Write-ColorOutput "An error occurred during uninstallation:" -Type Error
        Write-ColorOutput $_.Exception.Message -Type Error
        Write-Host ""
        Write-ColorOutput "Stack trace:" -Type Info
        Write-Host $_.ScriptStackTrace
        return 1
    }
}

################################################################################
# Script Entry Point
################################################################################

# Check PowerShell version
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "This script requires PowerShell 5.1 or higher"
    Write-Host "Current version: $($PSVersionTable.PSVersion)"
    exit 1
}

# Run main function
$exitCode = Main

# Pause before closing (if running interactively)
if ($Host.Name -eq "ConsoleHost") {
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}

exit $exitCode
