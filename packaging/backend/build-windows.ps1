#
# Build PhotoSense-AI Backend for Windows
# Creates a standalone executable that can run without Python installed
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$OutputDir = "$ScriptDir\..\dist\backend"
$PortableDir = "$ScriptDir\.python-portable"
$VenvDir = "$ScriptDir\.build-venv"

Write-Host "============================================================"
Write-Host "Building PhotoSense-AI Backend for Windows"
Write-Host "============================================================"
Write-Host "Project root: $ProjectRoot"
Write-Host "Output dir: $OutputDir"
Write-Host ""

# Function to test if Python actually works (not Windows Store stub)
function Test-PythonWorks {
    param([string]$PythonPath)
    try {
        $output = & $PythonPath -c "import sys; print(sys.version)" 2>&1
        if ($LASTEXITCODE -eq 0 -and $output -match "3\.\d+\.\d+") {
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Function to find a working Python
function Find-WorkingPython {
    Write-Host "Searching for Python..."
    
    # Check portable first
    if (Test-Path "$PortableDir\python.exe") {
        if (Test-PythonWorks "$PortableDir\python.exe") {
            return "$PortableDir\python.exe"
        }
    }
    
    # Check common install locations
    $locations = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    
    foreach ($loc in $locations) {
        if (Test-Path $loc) {
            Write-Host "  Found: $loc"
            if (Test-PythonWorks $loc) {
                return $loc
            }
        }
    }
    
    # Try PATH (but verify it works - skip Windows Store stub)
    try {
        $pathPython = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($pathPython -and (Test-PythonWorks $pathPython)) {
            return $pathPython
        }
    } catch {}
    
    return $null
}

# Function to download and setup portable Python
function Install-PortablePython {
    Write-Host ""
    Write-Host "Downloading portable Python 3.11.9..."
    Write-Host "This is a one-time download (~25MB)"
    Write-Host ""
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    $zipFile = "$ScriptDir\python-embed.zip"
    
    try {
        # Download
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Write-Host "Downloading..."
        Invoke-WebRequest -Uri $pythonUrl -OutFile $zipFile -UseBasicParsing
        
        # Extract
        Write-Host "Extracting..."
        if (Test-Path $PortableDir) { Remove-Item -Recurse -Force $PortableDir }
        Expand-Archive -Path $zipFile -DestinationPath $PortableDir -Force
        Remove-Item $zipFile -Force
        
        # Enable pip - modify python311._pth
        $pthFile = "$PortableDir\python311._pth"
        if (Test-Path $pthFile) {
            $content = Get-Content $pthFile
            $content = $content -replace '#import site', 'import site'
            $content | Set-Content $pthFile
        }
        
        # Create site-packages
        New-Item -ItemType Directory -Force -Path "$PortableDir\Lib\site-packages" | Out-Null
        
        # Install pip
        Write-Host "Installing pip..."
        $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
        $getPipFile = "$PortableDir\get-pip.py"
        Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipFile -UseBasicParsing
        & "$PortableDir\python.exe" $getPipFile --no-warn-script-location 2>&1 | Out-Null
        Remove-Item $getPipFile -Force -ErrorAction SilentlyContinue
        
        Write-Host "Python installed successfully!" -ForegroundColor Green
        return "$PortableDir\python.exe"
    } catch {
        Write-Host "ERROR: Failed to install Python: $_" -ForegroundColor Red
        return $null
    }
}

# ============================================================
# MAIN
# ============================================================

$pythonExe = Find-WorkingPython

if (-not $pythonExe) {
    Write-Host ""
    Write-Host "Python not found!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Would you like to download portable Python? (Y/N)"
    $response = Read-Host
    
    if ($response -match "^[Yy]") {
        $pythonExe = Install-PortablePython
    }
    
    if (-not $pythonExe) {
        Write-Host ""
        Write-Host "Please install Python from https://python.org/downloads"
        Write-Host "IMPORTANT: Check 'Add Python to PATH' during installation"
        exit 1
    }
}

Write-Host ""
Write-Host "Using Python: $pythonExe"
$verOut = & $pythonExe --version 2>&1
Write-Host "Version: $verOut"

# Install dependencies directly (no venv - simpler and works with portable Python)
Write-Host ""
Write-Host "============================================================"
Write-Host "Installing dependencies (this takes 10-20 minutes first time)..."
Write-Host "============================================================"
Write-Host ""

& $pythonExe -m pip install --upgrade pip 2>&1 | Out-Host
& $pythonExe -m pip install pyinstaller 2>&1 | Out-Host

Write-Host ""
Write-Host "Installing project requirements..."
& $pythonExe -m pip install -r "$ProjectRoot\requirements.txt" 2>&1 | Out-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Clean previous build
Write-Host ""
Write-Host "Cleaning previous build..."
if (Test-Path "$ScriptDir\build") { Remove-Item -Recurse -Force "$ScriptDir\build" }
if (Test-Path "$ScriptDir\dist") { Remove-Item -Recurse -Force "$ScriptDir\dist" }
if (Test-Path $OutputDir) { Remove-Item -Recurse -Force $OutputDir }

# Run PyInstaller
Write-Host ""
Write-Host "============================================================"
Write-Host "Running PyInstaller..."
Write-Host "============================================================"
Write-Host ""
Set-Location $ScriptDir
& $pythonExe -m PyInstaller photosense_backend.spec --noconfirm 2>&1 | Out-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller failed" -ForegroundColor Red
    exit 1
}

# Move to output directory
Write-Host ""
Write-Host "Moving build artifacts..."
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Move-Item "$ScriptDir\dist\photosense-backend" "$OutputDir\"

# Create version info
Write-Host "Creating version info..."
@"
PhotoSense-AI Backend
Version: 1.0.0
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")
Platform: Windows
"@ | Out-File -FilePath "$OutputDir\photosense-backend\version.txt" -Encoding UTF8

# Cleanup
Write-Host "Cleaning up..."
if (Test-Path "$ScriptDir\build") { Remove-Item -Recurse -Force "$ScriptDir\build" }
if (Test-Path "$ScriptDir\dist") { Remove-Item -Recurse -Force "$ScriptDir\dist" }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Backend build complete!" -ForegroundColor Green
Write-Host "Output: $OutputDir\photosense-backend\" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
