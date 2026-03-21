# Build VAST As-Built Reporter for Windows.
#
# Prerequisites:
#   pip install pyinstaller
#
# Usage:
#   cd <project-root>
#   powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$DistDir = Join-Path $ProjectRoot "dist"

Write-Host "=== VAST Reporter Windows Build ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"

# 1. Clean previous build
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
$BuildDir = Join-Path $ProjectRoot "build"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

# 2. Ensure required config files exist (gitignored files that may not be present in CI)
$ClusterProfiles = Join-Path $ProjectRoot "config\cluster_profiles.json"
if (-not (Test-Path $ClusterProfiles)) {
    "{}" | Out-File -FilePath $ClusterProfiles -Encoding utf8
    Write-Host "Created empty cluster_profiles.json"
}

# 3. Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    pyinstaller packaging/vast-reporter.spec --noconfirm
} finally {
    Pop-Location
}

# 4. Verify output
$AppDir = Join-Path $DistDir "VAST Reporter"
if (-not (Test-Path $AppDir)) {
    Write-Host "ERROR: Build output not found at $AppDir" -ForegroundColor Red
    exit 1
}
Write-Host "App folder created: $AppDir" -ForegroundColor Green

# 5. Create ZIP archive (version from src/app.py APP_VERSION)
$AppPy = Join-Path (Join-Path $ProjectRoot "src") "app.py"
$Version = "1.4.0"
if (Test-Path $AppPy) {
    $m = [regex]::Match((Get-Content $AppPy -Raw), 'APP_VERSION\s*=\s*["'']([0-9]+\.[0-9]+\.[0-9]+)["'']')
    if ($m.Success) { $Version = $m.Groups[1].Value }
}
$ZipName = "VAST-Reporter-v$Version-win.zip"
$ZipPath = Join-Path $DistDir $ZipName
Write-Host "Creating ZIP: $ZipName" -ForegroundColor Yellow
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -Force
Write-Host "ZIP created: $ZipPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: $DistDir\"
Get-ChildItem $DistDir | Format-Table Name, Length, LastWriteTime -AutoSize
