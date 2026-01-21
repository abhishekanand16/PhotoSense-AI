#
# Build PhotoSense-AI Backend for Windows
# Creates a standalone executable that can run without Python installed
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$OutputDir = "$ScriptDir\..\dist\backend"

Write-Host "============================================================"
Write-Host "Building PhotoSense-AI Backend for Windows"
Write-Host "============================================================"
Write-Host "Project root: $ProjectRoot"
Write-Host "Output dir: $OutputDir"
Write-Host ""

# Check for Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python is required but not installed."
    Write-Host "Download from: https://python.org"
    exit 1
}

$pythonVersion = python --version
Write-Host "Using: $pythonVersion"

# Create/activate virtual environment for clean build
$VenvDir = "$ScriptDir\.build-venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating build virtual environment..."
    python -m venv $VenvDir
}

& "$VenvDir\Scripts\Activate.ps1"

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller
pip install -r "$ProjectRoot\requirements.txt"

# Clean previous build
Write-Host ""
Write-Host "Cleaning previous build..."
if (Test-Path "$ScriptDir\build") { Remove-Item -Recurse -Force "$ScriptDir\build" }
if (Test-Path "$ScriptDir\dist") { Remove-Item -Recurse -Force "$ScriptDir\dist" }
if (Test-Path $OutputDir) { Remove-Item -Recurse -Force $OutputDir }

# Run PyInstaller
Write-Host ""
Write-Host "Running PyInstaller..."
Set-Location $ScriptDir
pyinstaller photosense_backend.spec --noconfirm

# Move to output directory
Write-Host ""
Write-Host "Moving build artifacts..."
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Move-Item "$ScriptDir\dist\photosense-backend" "$OutputDir\"

# Create version info
Write-Host ""
Write-Host "Creating version info..."
$versionContent = @"
PhotoSense-AI Backend
Version: 1.0.0
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")
Platform: Windows
"@
$versionContent | Out-File -FilePath "$OutputDir\photosense-backend\version.txt" -Encoding UTF8

# Cleanup
Write-Host ""
Write-Host "Cleaning up..."
if (Test-Path "$ScriptDir\build") { Remove-Item -Recurse -Force "$ScriptDir\build" }
if (Test-Path "$ScriptDir\dist") { Remove-Item -Recurse -Force "$ScriptDir\dist" }
deactivate

Write-Host ""
Write-Host "============================================================"
Write-Host "Backend build complete!"
Write-Host "Output: $OutputDir\photosense-backend\"
Write-Host "============================================================"
