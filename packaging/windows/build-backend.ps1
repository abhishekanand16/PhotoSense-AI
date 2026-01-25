#Requires -Version 5.1
<#
.SYNOPSIS
    Build PhotoSense-AI Backend for Windows using PyInstaller.

.DESCRIPTION
    This script:
    1. Finds or downloads Python 3.11+
    2. Creates an isolated virtual environment
    3. Installs dependencies in the correct order
    4. Runs PyInstaller to create the backend executable
    
    Output: dist\photosense-backend\photosense-backend.exe

.EXAMPLE
    .\build-backend.ps1
    
.NOTES
    Run this script from the packaging\windows directory.
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Speed up web requests

# ============================================================
# Configuration
# ============================================================
$ScriptDir = $PSScriptRoot
$ProjectRoot = (Get-Item (Join-Path $ScriptDir ".." "..")).FullName
$OutputDir = Join-Path $ScriptDir "dist" "backend"
$VenvDir = Join-Path $ScriptDir ".venv"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PhotoSense-AI Backend Build for Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project Root: $ProjectRoot"
Write-Host "  Output Dir:   $OutputDir"
Write-Host ""

# ============================================================
# Step 1: Find Python
# ============================================================
Write-Host "[1/6] Finding Python 3.10+..." -ForegroundColor Yellow

$PythonExe = $null

# Check if python is in PATH
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCmd) {
    $Version = & $PythonCmd.Source --version 2>&1
    if ($Version -match "Python 3\.(1[0-9]|[2-9][0-9])") {
        $PythonExe = $PythonCmd.Source
        Write-Host "  Found in PATH: $PythonExe ($Version)" -ForegroundColor Green
    }
}

# Check common installation locations
if (-not $PythonExe) {
    $PythonLocations = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "$env:ProgramFiles\Python313\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    
    foreach ($Location in $PythonLocations) {
        if (Test-Path $Location) {
            $Version = & $Location --version 2>&1
            $PythonExe = $Location
            Write-Host "  Found: $PythonExe ($Version)" -ForegroundColor Green
            break
        }
    }
}

if (-not $PythonExe) {
    Write-Host ""
    Write-Host "  ERROR: Python 3.10+ not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ============================================================
# Step 2: Create Virtual Environment
# ============================================================
Write-Host ""
Write-Host "[2/6] Setting up virtual environment..." -ForegroundColor Yellow

if (Test-Path $VenvDir) {
    Write-Host "  Removing existing venv..."
    Remove-Item -Recurse -Force $VenvDir
}

Write-Host "  Creating new venv at: $VenvDir"
& $PythonExe -m venv $VenvDir

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Activate venv
$VenvPython = Join-Path $VenvDir "Scripts" "python.exe"
$VenvPip = Join-Path $VenvDir "Scripts" "pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "  ERROR: Virtual environment Python not found" -ForegroundColor Red
    exit 1
}

Write-Host "  Virtual environment created!" -ForegroundColor Green

# ============================================================
# Step 3: Upgrade pip
# ============================================================
Write-Host ""
Write-Host "[3/6] Upgrading pip..." -ForegroundColor Yellow

& $VenvPython -m pip install --upgrade pip --quiet 2>$null
Write-Host "  pip upgraded!" -ForegroundColor Green

# ============================================================
# Step 4: Install Dependencies (CORRECT ORDER)
# ============================================================
Write-Host ""
Write-Host "[4/6] Installing dependencies..." -ForegroundColor Yellow
Write-Host "  This may take 10-30 minutes on first run." -ForegroundColor Cyan
Write-Host ""

# Helper function to install and verify
function Install-Package {
    param(
        [string]$PackageSpec,
        [string]$DisplayName,
        [switch]$Quiet
    )
    
    Write-Host "  Installing $DisplayName..." -NoNewline
    
    if ($Quiet) {
        & $VenvPip install $PackageSpec --quiet 2>$null
    } else {
        & $VenvPip install $PackageSpec 2>&1 | Out-Null
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
        return $true
    } else {
        Write-Host " FAILED" -ForegroundColor Red
        return $false
    }
}

# Install in correct order to avoid dependency conflicts

# 1. NumPy first (many ML libs depend on specific numpy version)
Install-Package "numpy>=1.26.4,<2" "numpy" -Quiet

# 2. Core ML frameworks
Install-Package "torch" "PyTorch"
Install-Package "torchvision" "torchvision" -Quiet

# 3. Image processing
Install-Package "opencv-python" "OpenCV" -Quiet
Install-Package "pillow" "Pillow" -Quiet

# 4. ONNX Runtime (must be before insightface)
Install-Package "onnxruntime" "ONNX Runtime" -Quiet
Install-Package "onnx>=1.16.0,<1.18" "ONNX" -Quiet

# 5. InsightFace (face detection)
Install-Package "insightface" "InsightFace"

# 6. Remaining dependencies from requirements.txt
Write-Host "  Installing remaining packages from requirements.txt..."
& $VenvPip install -r $RequirementsFile --quiet 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Some packages may have had issues" -ForegroundColor Yellow
}

# 7. PyInstaller
Install-Package "pyinstaller" "PyInstaller" -Quiet

Write-Host ""
Write-Host "  Dependencies installed!" -ForegroundColor Green

# ============================================================
# Step 5: Clean Previous Build
# ============================================================
Write-Host ""
Write-Host "[5/6] Cleaning previous build artifacts..." -ForegroundColor Yellow

$BuildDir = Join-Path $ScriptDir "build"
$DistDir = Join-Path $ScriptDir "dist"

if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
}
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir -ErrorAction SilentlyContinue
}

Write-Host "  Cleaned!" -ForegroundColor Green

# ============================================================
# Step 6: Run PyInstaller
# ============================================================
Write-Host ""
Write-Host "[6/6] Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host "  This takes 5-15 minutes..." -ForegroundColor Cyan
Write-Host ""

$SpecFile = Join-Path $ScriptDir "backend.spec"

Push-Location $ScriptDir
& $VenvPython -m PyInstaller $SpecFile --noconfirm --clean
$BuildResult = $LASTEXITCODE
Pop-Location

if ($BuildResult -ne 0) {
    Write-Host ""
    Write-Host "  ERROR: PyInstaller build failed!" -ForegroundColor Red
    Write-Host "  Check the output above for details." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify output
$BackendExe = Join-Path $ScriptDir "dist" "photosense-backend" "photosense-backend.exe"

if (-not (Test-Path $BackendExe)) {
    Write-Host ""
    Write-Host "  ERROR: Build output not found!" -ForegroundColor Red
    Write-Host "  Expected: $BackendExe" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Get size
$ExeSize = [math]::Round((Get-Item $BackendExe).Length / 1MB, 1)
$BundleSize = [math]::Round((Get-ChildItem -Recurse (Join-Path $ScriptDir "dist" "photosense-backend") | Measure-Object -Property Length -Sum).Sum / 1MB, 1)

# Create version info file
$VersionFile = Join-Path $ScriptDir "dist" "photosense-backend" "version.txt"
@"
PhotoSense-AI Backend
Version: 1.0.0
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Platform: Windows x64
Python: $((& $VenvPython --version 2>&1) -replace 'Python ', '')
"@ | Out-File -FilePath $VersionFile -Encoding UTF8

# ============================================================
# Done!
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  BACKEND BUILD COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Output:     dist\photosense-backend\"
Write-Host "  Executable: photosense-backend.exe ($ExeSize MB)"
Write-Host "  Bundle:     $BundleSize MB total"
Write-Host ""
Write-Host "  Next step: Run build-frontend.ps1" -ForegroundColor Cyan
Write-Host ""
