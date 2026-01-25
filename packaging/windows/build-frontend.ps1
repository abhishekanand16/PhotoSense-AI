#Requires -Version 5.1
<#
.SYNOPSIS
    Build PhotoSense-AI Frontend (Tauri) for Windows.

.DESCRIPTION
    This script:
    1. Verifies Node.js and Rust are installed
    2. Copies the desktop app source to a build directory
    3. Copies the backend bundle to resources
    4. Builds the Tauri app with NSIS installer
    
    Output: dist\PhotoSense-AI-1.0.0-Setup.exe

.EXAMPLE
    .\build-frontend.ps1

.NOTES
    Run build-backend.ps1 first to create the backend bundle.
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================
# Configuration
# ============================================================
$ScriptDir = $PSScriptRoot
$ProjectRoot = (Get-Item (Join-Path $ScriptDir ".." "..")).FullName
$DesktopSrc = Join-Path $ProjectRoot "apps" "desktop"
$BackendBundle = Join-Path $ScriptDir "dist" "backend" "photosense-backend"
$BuildDir = Join-Path $ScriptDir ".build"
$OutputDir = Join-Path $ScriptDir "dist"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  PhotoSense-AI Frontend Build for Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Project Root:   $ProjectRoot"
Write-Host "  Desktop Source: $DesktopSrc"
Write-Host "  Backend Bundle: $BackendBundle"
Write-Host ""

# ============================================================
# Step 1: Check Prerequisites
# ============================================================
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

# Check if backend was built
if (-not (Test-Path (Join-Path $BackendBundle "photosense-backend.exe"))) {
    Write-Host ""
    Write-Host "  ERROR: Backend bundle not found!" -ForegroundColor Red
    Write-Host "  Expected: $BackendBundle\photosense-backend.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Run build-backend.ps1 first." -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Backend bundle: OK" -ForegroundColor Green

# Find Node.js
$NodeExe = $null
$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($NodeCmd) {
    $NodeExe = $NodeCmd.Source
}

if (-not $NodeExe) {
    $NodeLocations = @(
        "$env:ProgramFiles\nodejs\node.exe",
        "${env:ProgramFiles(x86)}\nodejs\node.exe",
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe"
    )
    foreach ($Location in $NodeLocations) {
        if (Test-Path $Location) {
            $NodeExe = $Location
            break
        }
    }
}

if (-not $NodeExe) {
    Write-Host ""
    Write-Host "  ERROR: Node.js not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Install Node.js from: https://nodejs.org" -ForegroundColor Yellow
    Write-Host "  Recommended: LTS version (v18 or v20)" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$NodeVersion = & $NodeExe --version 2>&1
Write-Host "  Node.js: $NodeVersion" -ForegroundColor Green

# Find npm
$NodeDir = Split-Path $NodeExe
$NpmExe = Join-Path $NodeDir "npm.cmd"
if (-not (Test-Path $NpmExe)) {
    $NpmExe = Join-Path $NodeDir "npm.exe"
}
if (-not (Test-Path $NpmExe)) {
    # Try npm from PATH
    $NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($NpmCmd) {
        $NpmExe = $NpmCmd.Source
    }
}

if (-not (Test-Path $NpmExe)) {
    Write-Host "  ERROR: npm not found!" -ForegroundColor Red
    exit 1
}

$NpmVersion = & $NpmExe --version 2>&1
Write-Host "  npm: v$NpmVersion" -ForegroundColor Green

# Find Rust/Cargo
$CargoExe = $null
$CargoCmd = Get-Command cargo -ErrorAction SilentlyContinue
if ($CargoCmd) {
    $CargoExe = $CargoCmd.Source
}

if (-not $CargoExe) {
    $CargoLocations = @(
        "$env:USERPROFILE\.cargo\bin\cargo.exe",
        "$env:LOCALAPPDATA\.cargo\bin\cargo.exe"
    )
    foreach ($Location in $CargoLocations) {
        if (Test-Path $Location) {
            $CargoExe = $Location
            break
        }
    }
}

if (-not $CargoExe) {
    Write-Host ""
    Write-Host "  ERROR: Rust not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Install Rust from: https://rustup.rs" -ForegroundColor Yellow
    Write-Host "  Run: winget install Rustlang.Rustup" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$CargoVersion = & $CargoExe --version 2>&1
Write-Host "  Rust: $CargoVersion" -ForegroundColor Green

Write-Host ""
Write-Host "  All prerequisites OK!" -ForegroundColor Green

# ============================================================
# Step 2: Setup Build Directory
# ============================================================
Write-Host ""
Write-Host "[2/5] Setting up build directory..." -ForegroundColor Yellow

if (Test-Path $BuildDir) {
    Write-Host "  Removing previous build..."
    Remove-Item -Recurse -Force $BuildDir
}

Write-Host "  Copying desktop source..."
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
Copy-Item -Recurse (Join-Path $DesktopSrc "*") $BuildDir

# Copy our Windows-specific Tauri config
Write-Host "  Applying Windows Tauri config..."
$TauriDir = Join-Path $BuildDir "src-tauri"
Copy-Item (Join-Path $ScriptDir "tauri.conf.json") $TauriDir -Force

Write-Host "  Build directory ready!" -ForegroundColor Green

# ============================================================
# Step 3: Copy Backend Resources
# ============================================================
Write-Host ""
Write-Host "[3/5] Copying backend resources..." -ForegroundColor Yellow

$ResourcesDir = Join-Path $TauriDir "resources" "backend"

if (Test-Path $ResourcesDir) {
    Remove-Item -Recurse -Force $ResourcesDir
}

New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

Write-Host "  Copying backend bundle (this may take a moment)..."
Copy-Item -Recurse (Join-Path $BackendBundle "*") $ResourcesDir

$FileCount = (Get-ChildItem -Recurse $ResourcesDir -File).Count
$TotalSize = [math]::Round((Get-ChildItem -Recurse $ResourcesDir | Measure-Object -Property Length -Sum).Sum / 1MB, 1)

Write-Host "  Copied $FileCount files ($TotalSize MB)" -ForegroundColor Green

# ============================================================
# Step 4: Install npm Dependencies
# ============================================================
Write-Host ""
Write-Host "[4/5] Installing npm dependencies..." -ForegroundColor Yellow

Push-Location $BuildDir

Write-Host "  Running npm install..."
& $NpmExe install 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: npm install failed!" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "  npm dependencies installed!" -ForegroundColor Green

# ============================================================
# Step 5: Build Tauri Application
# ============================================================
Write-Host ""
Write-Host "[5/5] Building Tauri application..." -ForegroundColor Yellow
Write-Host "  This takes 5-15 minutes..." -ForegroundColor Cyan
Write-Host ""

& $NpmExe run tauri build 2>&1 | ForEach-Object {
    # Filter out some noisy output but keep important messages
    if ($_ -match "Compiling|Finished|Bundling|Building") {
        Write-Host "  $_" -ForegroundColor DarkGray
    } elseif ($_ -match "error|Error|ERROR") {
        Write-Host "  $_" -ForegroundColor Red
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  ERROR: Tauri build failed!" -ForegroundColor Red
    Write-Host "  Check the output above for details." -ForegroundColor Yellow
    Pop-Location
    Read-Host "Press Enter to exit"
    exit 1
}

Pop-Location

# ============================================================
# Step 6: Move Output
# ============================================================
Write-Host ""
Write-Host "Moving build artifacts..." -ForegroundColor Yellow

# Find the NSIS installer
$NsisDir = Join-Path $BuildDir "src-tauri" "target" "release" "bundle" "nsis"
$InstallerExe = Get-ChildItem (Join-Path $NsisDir "*.exe") -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $InstallerExe) {
    Write-Host "  WARNING: NSIS installer not found in expected location" -ForegroundColor Yellow
    Write-Host "  Checking alternative locations..."
    
    # Try alternative location
    $AltNsisDir = Join-Path $BuildDir "src-tauri" "target" "release" "bundle"
    $InstallerExe = Get-ChildItem -Recurse (Join-Path $AltNsisDir "*setup*.exe") -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($InstallerExe) {
    # Ensure output directory exists
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    }
    
    $FinalInstaller = Join-Path $OutputDir "PhotoSense-AI-1.0.0-Setup.exe"
    Copy-Item $InstallerExe.FullName $FinalInstaller -Force
    
    $InstallerSize = [math]::Round((Get-Item $FinalInstaller).Length / 1MB, 1)
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "  FRONTEND BUILD COMPLETE!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Installer: dist\PhotoSense-AI-1.0.0-Setup.exe"
    Write-Host "  Size:      $InstallerSize MB"
    Write-Host ""
    Write-Host "  To install PhotoSense-AI:" -ForegroundColor Cyan
    Write-Host "  1. Double-click the Setup.exe installer"
    Write-Host "  2. Follow the installation wizard"
    Write-Host "  3. Launch from Start Menu or Desktop shortcut"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "  BUILD COMPLETE (with warnings)" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  NSIS installer not found in expected location." -ForegroundColor Yellow
    Write-Host "  Check: $BuildDir\src-tauri\target\release\bundle\" -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================
# Cleanup
# ============================================================
Write-Host "Cleaning up build directory..." -ForegroundColor DarkGray

# Keep the build directory for debugging if needed
# Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue

Write-Host ""
