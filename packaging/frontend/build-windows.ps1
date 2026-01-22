#
# Build PhotoSense-AI Frontend (Tauri) for Windows
# Creates the .exe installer with the backend sidecar
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackagingDir = (Get-Item "$ScriptDir\..").FullName
$ProjectRoot = (Get-Item "$PackagingDir\..").FullName
$DesktopSrc = "$ProjectRoot\apps\desktop"
$OutputDir = "$PackagingDir\dist\frontend"
$FinalInstaller = "$PackagingDir\dist\PhotoSense-AI-Setup.exe"
$BackendDir = "$PackagingDir\dist\backend\photosense-backend"

Write-Host "============================================================"
Write-Host "Building PhotoSense-AI Frontend for Windows"
Write-Host "============================================================"
Write-Host "Project root: $ProjectRoot"
Write-Host "Desktop source: $DesktopSrc"
Write-Host "Output dir: $OutputDir"
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..."

# Find Node.js
$nodeExe = $null

# First try Get-Command (checks PATH)
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    $nodeExe = $nodeCmd.Source
}

# If not in PATH, check common installation locations
if (-not $nodeExe) {
    $nodeLocations = @(
        "$env:ProgramFiles\nodejs\node.exe",
        "${env:ProgramFiles(x86)}\nodejs\node.exe",
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe",
        "$env:APPDATA\npm\node.exe",
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe"
    )
    
    foreach ($loc in $nodeLocations) {
        if (Test-Path $loc) {
            $nodeExe = $loc
            Write-Host "  Found Node.js: $nodeExe"
            break
        }
    }
}

if (-not $nodeExe) {
    Write-Host "ERROR: Node.js is required but not installed." -ForegroundColor Red
    Write-Host "Download from: https://nodejs.org" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing Node.js:"
    Write-Host "  1. Restart your terminal/PowerShell"
    Write-Host "  2. Run this script again"
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify Node.js works
try {
    $nodeVersion = & $nodeExe --version 2>&1
    Write-Host "  Using Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Node.js found but cannot execute: $nodeExe" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Find npm (should be in same directory as node.exe)
$nodeDir = Split-Path $nodeExe
$npmExe = Join-Path $nodeDir "npm.cmd"
if (-not (Test-Path $npmExe)) {
    $npmExe = Join-Path $nodeDir "npm.exe"
}

if (-not (Test-Path $npmExe)) {
    Write-Host "ERROR: npm not found. Node.js installation may be incomplete." -ForegroundColor Red
    Write-Host "Expected at: $npmExe" -ForegroundColor Yellow
    Write-Host "Please reinstall Node.js from https://nodejs.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  Using npm: $npmExe" -ForegroundColor Green

# Find Rust/Cargo
$cargoExe = $null
$cargoCmd = Get-Command cargo -ErrorAction SilentlyContinue
if ($cargoCmd) {
    $cargoExe = $cargoCmd.Source
}

# Check common Rust installation locations
if (-not $cargoExe) {
    $cargoLocations = @(
        "$env:USERPROFILE\.cargo\bin\cargo.exe",
        "$env:LOCALAPPDATA\.cargo\bin\cargo.exe"
    )
    
    foreach ($loc in $cargoLocations) {
        if (Test-Path $loc) {
            $cargoExe = $loc
            Write-Host "  Found Rust: $cargoExe"
            break
        }
    }
}

if (-not $cargoExe) {
    Write-Host "ERROR: Rust is required but not installed." -ForegroundColor Red
    Write-Host "Download from: https://rustup.rs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing Rust:"
    Write-Host "  1. Restart your terminal/PowerShell"
    Write-Host "  2. Run this script again"
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify Rust works
try {
    $rustVersion = & $cargoExe --version 2>&1
    Write-Host "  Using Rust: $rustVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Rust found but cannot execute: $cargoExe" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if backend was built
if (-not (Test-Path "$BackendDir\photosense-backend.exe")) {
    Write-Host ""
    Write-Host "ERROR: Backend not found at $BackendDir" -ForegroundColor Red
    Write-Host "Run .\backend\build-windows.ps1 first" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Setup frontend build directory
Write-Host ""
Write-Host "Setting up build directory..."
$BuildDir = "$ScriptDir\.build"
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

# Copy desktop source
Copy-Item -Recurse "$DesktopSrc\*" $BuildDir

# Copy our Tauri config
Copy-Item "$ScriptDir\tauri.conf.json" "$BuildDir\src-tauri\" -Force
Copy-Item "$ScriptDir\Cargo.toml" "$BuildDir\src-tauri\" -Force
Copy-Item "$ScriptDir\build.rs" "$BuildDir\src-tauri\" -Force
New-Item -ItemType Directory -Force -Path "$BuildDir\src-tauri\src" | Out-Null
Copy-Item "$ScriptDir\src\main.rs" "$BuildDir\src-tauri\src\" -Force

# Copy backend bundle to resources
Write-Host ""
Write-Host "Copying backend resources..."
$ResourcesDir = "$BuildDir\src-tauri\resources\backend"
if (Test-Path $ResourcesDir) { Remove-Item -Recurse -Force $ResourcesDir }
New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

# Copy entire PyInstaller bundle
Copy-Item -Recurse "$BackendDir\*" $ResourcesDir

Write-Host "Backend resources: $ResourcesDir"
Write-Host "Files copied: $(Get-ChildItem $ResourcesDir | Measure-Object).Count"

# Install npm dependencies
Write-Host ""
Write-Host "Installing npm dependencies..."
Set-Location $BuildDir

# Use the found npm explicitly
& $npmExe install
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: npm install failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Build Tauri app
Write-Host ""
Write-Host "Building Tauri application..."
& $npmExe run tauri build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tauri build failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Move output
Write-Host ""
Write-Host "Moving build artifacts..."
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Find and copy the .exe installer (NSIS)
$ExeFile = Get-ChildItem "$BuildDir\src-tauri\target\release\bundle\nsis\*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ExeFile) {
    Copy-Item $ExeFile.FullName "$OutputDir\" -Force
    Copy-Item $ExeFile.FullName $FinalInstaller -Force
    Write-Host "NSIS installer: $OutputDir\$($ExeFile.Name)"
    Write-Host "Final installer: $FinalInstaller"
}

# Also copy the standalone exe
$StandaloneExe = Get-ChildItem "$BuildDir\src-tauri\target\release\*.exe" -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike "*uninstall*" } | Select-Object -First 1
if ($StandaloneExe) {
    Copy-Item $StandaloneExe.FullName "$OutputDir\"
    Write-Host "Standalone exe: $OutputDir\$($StandaloneExe.Name)"
}

# Cleanup
Write-Host ""
Write-Host "Cleaning up..."
Set-Location $ScriptDir
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

Write-Host ""
Write-Host "============================================================"
Write-Host "Frontend build complete!"
Write-Host "Output: $OutputDir\"
Write-Host "============================================================"
