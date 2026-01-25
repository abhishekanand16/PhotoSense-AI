#Requires -Version 5.1
<#
.SYNOPSIS
    PhotoSense-AI Windows Installer Builder

.DESCRIPTION
    This is the main entry point for building the PhotoSense-AI Windows installer.
    
    It orchestrates the full build process:
    1. Checks all prerequisites (Python, Node.js, Rust)
    2. Offers to install missing tools
    3. Builds the Python backend with PyInstaller
    4. Builds the Tauri frontend with NSIS installer
    
    Output: dist\PhotoSense-AI-1.0.0-Setup.exe

.EXAMPLE
    # Right-click this file and select "Run with PowerShell"
    # Or from PowerShell:
    .\install.ps1

.EXAMPLE
    # Skip prerequisite checks (for CI/CD)
    .\install.ps1 -SkipChecks

.NOTES
    Requirements:
    - Windows 10/11 (64-bit)
    - Python 3.10 or higher
    - Node.js 18 or higher
    - Rust (via rustup)
    - ~20GB free disk space
    - Internet connection (for dependencies)
#>

param(
    [switch]$SkipChecks,
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================
# Banner
# ============================================================
Clear-Host
Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║                                                           ║" -ForegroundColor Cyan
Write-Host "  ║           PhotoSense-AI Windows Installer                 ║" -ForegroundColor Cyan
Write-Host "  ║                    Version 1.0.0                          ║" -ForegroundColor Cyan
Write-Host "  ║                                                           ║" -ForegroundColor Cyan
Write-Host "  ╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = $PSScriptRoot
$ProjectRoot = (Get-Item (Join-Path $ScriptDir ".." "..")).FullName

Write-Host "  Project: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# ============================================================
# Prerequisites Check
# ============================================================
if (-not $SkipChecks) {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host "  CHECKING PREREQUISITES" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host ""
    
    $AllOk = $true
    $MissingTools = @()
    
    # Check Python
    Write-Host "  [1/3] Python 3.10+..." -NoNewline
    $PythonOk = $false
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonVersion = & python --version 2>&1
        if ($PythonVersion -match "Python 3\.(1[0-9]|[2-9][0-9])") {
            Write-Host " $PythonVersion" -ForegroundColor Green
            $PythonOk = $true
        }
    }
    if (-not $PythonOk) {
        # Check common locations
        $PythonLocations = @(
            "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
        )
        foreach ($Location in $PythonLocations) {
            if (Test-Path $Location) {
                $PythonVersion = & $Location --version 2>&1
                Write-Host " $PythonVersion (found at $Location)" -ForegroundColor Green
                $PythonOk = $true
                break
            }
        }
    }
    if (-not $PythonOk) {
        Write-Host " NOT FOUND" -ForegroundColor Red
        $AllOk = $false
        $MissingTools += "Python"
    }
    
    # Check Node.js
    Write-Host "  [2/3] Node.js 18+..." -NoNewline
    $NodeOk = $false
    $NodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($NodeCmd) {
        $NodeVersion = & node --version 2>&1
        if ($NodeVersion -match "v(1[8-9]|[2-9][0-9])") {
            Write-Host " $NodeVersion" -ForegroundColor Green
            $NodeOk = $true
        } else {
            Write-Host " $NodeVersion (too old, need v18+)" -ForegroundColor Yellow
        }
    }
    if (-not $NodeOk) {
        Write-Host " NOT FOUND" -ForegroundColor Red
        $AllOk = $false
        $MissingTools += "Node.js"
    }
    
    # Check Rust
    Write-Host "  [3/3] Rust (cargo)..." -NoNewline
    $RustOk = $false
    $CargoCmd = Get-Command cargo -ErrorAction SilentlyContinue
    if ($CargoCmd) {
        $CargoVersion = & cargo --version 2>&1
        Write-Host " $CargoVersion" -ForegroundColor Green
        $RustOk = $true
    } else {
        # Check common location
        $CargoPath = "$env:USERPROFILE\.cargo\bin\cargo.exe"
        if (Test-Path $CargoPath) {
            $CargoVersion = & $CargoPath --version 2>&1
            Write-Host " $CargoVersion" -ForegroundColor Green
            Write-Host "       (Note: Add $env:USERPROFILE\.cargo\bin to PATH)" -ForegroundColor Yellow
            $RustOk = $true
        }
    }
    if (-not $RustOk) {
        Write-Host " NOT FOUND" -ForegroundColor Red
        $AllOk = $false
        $MissingTools += "Rust"
    }
    
    Write-Host ""
    
    # Handle missing prerequisites
    if (-not $AllOk) {
        Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
        Write-Host "  MISSING PREREQUISITES" -ForegroundColor Yellow
        Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  The following tools need to be installed:" -ForegroundColor White
        Write-Host ""
        
        foreach ($Tool in $MissingTools) {
            switch ($Tool) {
                "Python" {
                    Write-Host "  - Python 3.10+" -ForegroundColor Cyan
                    Write-Host "    Download: https://www.python.org/downloads/" -ForegroundColor DarkGray
                    Write-Host "    Or run:   winget install Python.Python.3.12" -ForegroundColor DarkGray
                }
                "Node.js" {
                    Write-Host "  - Node.js 18+" -ForegroundColor Cyan
                    Write-Host "    Download: https://nodejs.org/" -ForegroundColor DarkGray
                    Write-Host "    Or run:   winget install OpenJS.NodeJS.LTS" -ForegroundColor DarkGray
                }
                "Rust" {
                    Write-Host "  - Rust (via rustup)" -ForegroundColor Cyan
                    Write-Host "    Download: https://rustup.rs/" -ForegroundColor DarkGray
                    Write-Host "    Or run:   winget install Rustlang.Rustup" -ForegroundColor DarkGray
                }
            }
            Write-Host ""
        }
        
        # Offer to install via winget
        $WingetCmd = Get-Command winget -ErrorAction SilentlyContinue
        if ($WingetCmd) {
            Write-Host ""
            Write-Host "  Would you like to install missing tools using winget?" -ForegroundColor Cyan
            $Response = Read-Host "  Enter Y to install, N to exit [Y/N]"
            
            if ($Response -eq "Y" -or $Response -eq "y") {
                Write-Host ""
                
                foreach ($Tool in $MissingTools) {
                    switch ($Tool) {
                        "Python" {
                            Write-Host "  Installing Python..." -ForegroundColor Yellow
                            winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
                        }
                        "Node.js" {
                            Write-Host "  Installing Node.js..." -ForegroundColor Yellow
                            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
                        }
                        "Rust" {
                            Write-Host "  Installing Rust..." -ForegroundColor Yellow
                            winget install Rustlang.Rustup --accept-package-agreements --accept-source-agreements
                            Write-Host ""
                            Write-Host "  IMPORTANT: After Rust installation completes:" -ForegroundColor Yellow
                            Write-Host "  1. Close this window" -ForegroundColor White
                            Write-Host "  2. Open a NEW PowerShell window" -ForegroundColor White
                            Write-Host "  3. Run this script again" -ForegroundColor White
                        }
                    }
                }
                
                Write-Host ""
                Write-Host "  Installation complete!" -ForegroundColor Green
                Write-Host "  Please restart PowerShell and run this script again." -ForegroundColor Yellow
                Write-Host ""
                Read-Host "Press Enter to exit"
                exit 0
            }
        }
        
        Write-Host ""
        Write-Host "  Please install the missing tools and run this script again." -ForegroundColor Yellow
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "  All prerequisites OK!" -ForegroundColor Green
    Write-Host ""
}

# ============================================================
# Build Backend
# ============================================================
if (-not $FrontendOnly) {
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host "  STEP 1: BUILD PYTHON BACKEND" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host ""
    
    $BackendScript = Join-Path $ScriptDir "build-backend.ps1"
    
    if (-not (Test-Path $BackendScript)) {
        Write-Host "  ERROR: build-backend.ps1 not found!" -ForegroundColor Red
        exit 1
    }
    
    & $BackendScript
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  Backend build failed!" -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ============================================================
# Build Frontend
# ============================================================
if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host "  STEP 2: BUILD TAURI FRONTEND" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor White
    Write-Host ""
    
    $FrontendScript = Join-Path $ScriptDir "build-frontend.ps1"
    
    if (-not (Test-Path $FrontendScript)) {
        Write-Host "  ERROR: build-frontend.ps1 not found!" -ForegroundColor Red
        exit 1
    }
    
    & $FrontendScript
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  Frontend build failed!" -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ============================================================
# Final Summary
# ============================================================
$InstallerPath = Join-Path $ScriptDir "dist" "PhotoSense-AI-1.0.0-Setup.exe"

if (Test-Path $InstallerPath) {
    $InstallerSize = [math]::Round((Get-Item $InstallerPath).Length / 1MB, 1)
    
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "║                    BUILD SUCCESSFUL!                          ║" -ForegroundColor Green
    Write-Host "║                                                               ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Installer created:" -ForegroundColor White
    Write-Host "  $InstallerPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Size: $InstallerSize MB" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  ─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  To install PhotoSense-AI:" -ForegroundColor White
    Write-Host "  1. Navigate to: packaging\windows\dist\" -ForegroundColor DarkGray
    Write-Host "  2. Double-click PhotoSense-AI-1.0.0-Setup.exe" -ForegroundColor DarkGray
    Write-Host "  3. Follow the installation wizard" -ForegroundColor DarkGray
    Write-Host "  4. Launch from Start Menu or Desktop" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  ─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
    
    # Offer to open the dist folder
    $Response = Read-Host "  Open dist folder? [Y/N]"
    if ($Response -eq "Y" -or $Response -eq "y") {
        Start-Process "explorer.exe" -ArgumentList (Join-Path $ScriptDir "dist")
    }
} else {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║                                                               ║" -ForegroundColor Yellow
    Write-Host "║                 BUILD COMPLETED (with issues)                 ║" -ForegroundColor Yellow
    Write-Host "║                                                               ║" -ForegroundColor Yellow
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  The installer was not found at the expected location." -ForegroundColor Yellow
    Write-Host "  Check the dist\ folder for build outputs." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
