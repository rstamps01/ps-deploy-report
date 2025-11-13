# Quick fix for install-windows.ps1 PowerShell parsing errors
# This script replaces unescaped % characters with escaped versions

$filePath = "C:\Users\rstam\Documents\ps-report\install-windows.ps1"

Write-Host "Fixing PowerShell parsing errors in install-windows.ps1..." -ForegroundColor Cyan

# Read the file content
$content = Get-Content $filePath -Raw

# Replace all instances of "% " with "`% " (escaped percent)
$content = $content -replace '(\d+)% ', '$1`% '

# Write back to file
$content | Set-Content $filePath -NoNewline

Write-Host "✓ File fixed successfully!" -ForegroundColor Green
Write-Host "You can now run: .\install-windows.ps1" -ForegroundColor Yellow
