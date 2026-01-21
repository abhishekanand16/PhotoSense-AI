#
# PhotoSense-AI Complete Windows Build Script
# 
# This script builds everything needed for a distributable Windows application:
# 1. Python backend (bundled with PyInstaller)
# 2. Tauri frontend (with backend as sidecar)
# 3. NSIS installer for standard Windows installation
#
# Output: dist\PhotoSense-AI-1.0.0-windows-setup.exe
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName
$Version = "1.0.0"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "                                                                " -ForegroundColor Cyan
Write-Host "           PhotoSense-AI Windows Build                          " -ForegroundColor Cyan
Write-Host "           Version: $Version                                    " -ForegroundColor Cyan
Write-Host "                                                                " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Create dist directory
$DistDir = "$ScriptDir\dist"
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

# Step 1: Build Backend
Write-Host ""
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "  Step 1/2: Building Python Backend                             " -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""

& "$ScriptDir\backend\build-windows.ps1"

# Step 2: Build Frontend
Write-Host ""
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host "  Step 2/2: Building Tauri Frontend                             " -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""

& "$ScriptDir\frontend\build-windows.ps1"

# Find the installer
$AppName = "PhotoSense-AI"
$InstallerExe = Get-ChildItem "$DistDir\frontend\*setup*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$FinalInstaller = "$DistDir\$AppName-$Version-windows-setup.exe"

if ($InstallerExe) {
    # Rename to standard name
    Copy-Item $InstallerExe.FullName $FinalInstaller -Force
    $InstallerSize = [math]::Round((Get-Item $FinalInstaller).Length / 1MB, 2)
    
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "                     BUILD COMPLETE                             " -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Installer: dist\$(Split-Path -Leaf $FinalInstaller)" -ForegroundColor White
    Write-Host "  Size: ${InstallerSize} MB" -ForegroundColor White
    Write-Host ""
    Write-Host "  To install:" -ForegroundColor Cyan
    Write-Host "  1. Double-click the installer" -ForegroundColor White
    Write-Host "  2. Follow the installation wizard" -ForegroundColor White
    Write-Host "  3. Launch from Start Menu or Desktop" -ForegroundColor White
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Yellow
    Write-Host "                     BUILD COMPLETE                             " -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Note: NSIS installer not found." -ForegroundColor Yellow
    Write-Host "  The standalone exe should be in dist\frontend\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Yellow
}

Write-Host ""
