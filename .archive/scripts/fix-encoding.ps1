# Fix encoding and syntax issues in install-windows.ps1
$ErrorActionPreference = 'Stop'

Write-Host "Fixing install-windows.ps1 encoding and syntax issues..." -ForegroundColor Cyan

$sourceUrl = "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/docs/deployment/install-windows.ps1"
$targetPath = "C:\Users\rstam\Documents\ps-report\install-windows.ps1"

try {
    # Download with proper encoding handling
    $webClient = New-Object System.Net.WebClient
    $webClient.Encoding = [System.Text.Encoding]::UTF8
    $content = $webClient.DownloadString($sourceUrl)
    
    # Fix percent signs
    $content = $content -replace '(\d+)%\s', '$1`% '
    
    # Save with UTF-8 BOM (PowerShell-friendly encoding)
    $utf8BOM = New-Object System.Text.UTF8Encoding($true)
    [System.IO.File]::WriteAllText($targetPath, $content, $utf8BOM)
    
    Write-Host "✓ File fixed and saved with correct encoding!" -ForegroundColor Green
    Write-Host "You can now run: .\install-windows.ps1" -ForegroundColor Yellow
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
