#
# Build PhotoSense-AI Frontend (Tauri) for Windows
# Creates the .exe installer with the backend sidecar
#
# PREREQUISITES:
#   1. Node.js 18+ (https://nodejs.org)
#   2. Rust (https://rustup.rs)
#   3. Backend must be built first (run build-windows.bat in backend folder)
#
# USAGE:
#   Option 1: .\build-windows.ps1
#   Option 2: Double-click build-windows.bat (recommended)
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackagingDir = (Get-Item "$ScriptDir\..").FullName
$ProjectRoot = (Get-Item "$PackagingDir\..").FullName
$DesktopSrc = "$ProjectRoot\apps\desktop"
$OutputDir = "$PackagingDir\dist\frontend"
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
Write-Host ""

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "============================================================"
    Write-Host "ERROR: Node.js is required but not installed."
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Please install Node.js:"
    Write-Host "  1. Go to https://nodejs.org"
    Write-Host "  2. Download the LTS version (18.x or 20.x)"
    Write-Host "  3. Run the installer"
    Write-Host "  4. Restart this script"
    Write-Host ""
    Write-Host "Or use winget (Windows 11):"
    Write-Host "  winget install OpenJS.NodeJS.LTS"
    Write-Host ""
    exit 1
}

$cargoCmd = Get-Command cargo -ErrorAction SilentlyContinue
if (-not $cargoCmd) {
    Write-Host "============================================================"
    Write-Host "ERROR: Rust is required but not installed."
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "Please install Rust:"
    Write-Host "  1. Go to https://rustup.rs"
    Write-Host "  2. Download and run rustup-init.exe"
    Write-Host "  3. Follow the prompts (default options are fine)"
    Write-Host "  4. Restart your terminal and this script"
    Write-Host ""
    Write-Host "Or use winget (Windows 11):"
    Write-Host "  winget install Rustlang.Rustup"
    Write-Host ""
    exit 1
}

# Check if backend was built
if (-not (Test-Path "$BackendDir\photosense-backend.exe")) {
    Write-Host "============================================================"
    Write-Host "ERROR: Backend not found!"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "The backend must be built before the frontend."
    Write-Host "Please run the backend build first:"
    Write-Host ""
    Write-Host "  cd $PackagingDir\backend"
    Write-Host "  .\build-windows.bat"
    Write-Host ""
    Write-Host "Then run this script again."
    Write-Host ""
    exit 1
}

Write-Host "Using Node.js: $(node --version)"
Write-Host "Using Rust: $(rustc --version)"

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

# Copy backend sidecar to binaries folder
Write-Host ""
Write-Host "Copying backend sidecar..."
$SidecarDir = "$BuildDir\src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $SidecarDir | Out-Null

# Target triple for Windows
$TargetTriple = "x86_64-pc-windows-msvc"

# For Tauri sidecar with PyInstaller folder bundles:
# Tauri expects: binaries/photosense-backend-{target-triple}.exe
# 
# Since PyInstaller creates a folder with the executable inside,
# we need to create a batch wrapper that Tauri can execute directly

# Copy entire PyInstaller bundle to a subfolder
$BackendBundleDir = "$SidecarDir\photosense-backend-bundle"
Copy-Item -Recurse $BackendDir $BackendBundleDir

# Create a batch wrapper that Tauri will execute as the sidecar
# This script launches the actual PyInstaller bundle
$wrapperContent = @'
@echo off
set SCRIPT_DIR=%~dp0
"%SCRIPT_DIR%photosense-backend-bundle\photosense-backend.exe" %*
'@
$wrapperContent | Out-File -FilePath "$SidecarDir\photosense-backend-$TargetTriple.exe.cmd" -Encoding ASCII

# Actually, Tauri needs a real .exe, not a .cmd
# Let's just rename the exe directly and keep deps alongside
# Alternative approach: copy the main exe and create a launch wrapper

# Remove the cmd approach - instead, copy everything flat
Remove-Item "$SidecarDir\photosense-backend-$TargetTriple.exe.cmd" -ErrorAction SilentlyContinue
Remove-Item $BackendBundleDir -Recurse -Force -ErrorAction SilentlyContinue

# Copy the entire bundle contents directly to binaries
Copy-Item -Recurse "$BackendDir\*" $SidecarDir

# Rename the main executable with the target triple
Rename-Item "$SidecarDir\photosense-backend.exe" "photosense-backend-$TargetTriple.exe"

Write-Host "Sidecar executable: $SidecarDir\photosense-backend-$TargetTriple.exe"
Write-Host "Dependencies in: $SidecarDir\"

# Install npm dependencies
Write-Host ""
Write-Host "Installing npm dependencies..."
Set-Location $BuildDir
npm install

# Build Tauri app
Write-Host ""
Write-Host "Building Tauri application..."
npm run tauri build

# Move output
Write-Host ""
Write-Host "Moving build artifacts..."
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Find and copy the .exe installer (NSIS)
$ExeFile = Get-ChildItem "$BuildDir\src-tauri\target\release\bundle\nsis\*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ExeFile) {
    Copy-Item $ExeFile.FullName "$OutputDir\"
    Write-Host "NSIS installer: $OutputDir\$($ExeFile.Name)"
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
