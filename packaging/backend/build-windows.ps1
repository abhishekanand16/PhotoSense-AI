#
# Build PhotoSense-AI Backend for Windows
# Creates a standalone executable that can run without Python installed
#

# Stop on terminating errors, but continue on non-terminating (pip warnings)
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$OutputDir = "$ScriptDir\..\dist\backend"
$PortableDir = "$ScriptDir\.python-portable"

# Enable Windows long paths when possible
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
try {
    $longPaths = (Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
    if ($longPaths -ne 1) {
        if ($isAdmin) {
            Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -Force
            Write-Host "  ✓ Enabled Windows long paths" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Long paths are disabled. Run as Admin to enable." -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  WARNING: Could not read/set LongPathsEnabled." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================"
Write-Host "  PhotoSense-AI Backend Build for Windows"
Write-Host "============================================================"
Write-Host ""

# Step 1: Find or Download Python
Write-Host "[1/5] Finding Python..."

$pythonExe = $null

# Check if portable Python already exists
if (Test-Path "$PortableDir\python.exe") {
    $pythonExe = "$PortableDir\python.exe"
    Write-Host "  Using portable Python: $pythonExe"
}

# Check standard locations
if (-not $pythonExe) {
    $locations = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", 
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    
    foreach ($loc in $locations) {
        if (Test-Path $loc) {
            $pythonExe = $loc
            Write-Host "  Found Python: $pythonExe"
            break
        }
    }
}

# If still not found, download portable Python
if (-not $pythonExe) {
    Write-Host "  Python not found. Downloading portable version..."
    Write-Host ""
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    $zipFile = "$ScriptDir\python.zip"
    
    # Download
    Write-Host "  Downloading Python 3.11.9..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $zipFile -UseBasicParsing
    } catch {
        Write-Host "ERROR: Failed to download Python. Check internet connection." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Extract
    Write-Host "  Extracting..."
    if (Test-Path $PortableDir) { Remove-Item -Recurse -Force $PortableDir }
    Expand-Archive -Path $zipFile -DestinationPath $PortableDir -Force
    Remove-Item $zipFile -Force
    
    # Configure for pip - IMPORTANT: must enable site-packages
    Write-Host "  Configuring..."
    $pthFile = Get-ChildItem "$PortableDir\python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName -Raw
        # Uncomment import site AND add Lib\site-packages
        $content = $content -replace '#import site', 'import site'
        if ($content -notmatch 'Lib\\site-packages') {
            $content = $content.TrimEnd() + "`r`nLib\site-packages`r`n"
        }
        Set-Content -Path $pthFile.FullName -Value $content -NoNewline
    }
    New-Item -ItemType Directory -Force -Path "$PortableDir\Lib\site-packages" | Out-Null
    
    # Install pip
    Write-Host "  Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$PortableDir\get-pip.py" -UseBasicParsing
    & "$PortableDir\python.exe" "$PortableDir\get-pip.py" --no-warn-script-location 2>$null
    Remove-Item "$PortableDir\get-pip.py" -Force -ErrorAction SilentlyContinue
    
    $pythonExe = "$PortableDir\python.exe"
    Write-Host "  Python installed successfully!" -ForegroundColor Green
}

# Verify Python works
Write-Host ""
$version = & $pythonExe --version 2>&1
Write-Host "  Python version: $version"

# Step 2: Install Dependencies IN CORRECT ORDER
Write-Host ""
Write-Host "[2/5] Installing dependencies..."
Write-Host "  This takes 15-30 minutes on first run."
Write-Host ""

# Upgrade pip first
Write-Host "  Upgrading pip..."
& $pythonExe -m pip install --upgrade pip --no-warn-script-location -q 2>$null

# Install numpy FIRST (required by many packages)
Write-Host "  Installing numpy..."
& $pythonExe -m pip install "numpy>=1.26.4,<2" --no-warn-script-location -q 2>$null

# Install core dependencies that others need
Write-Host "  Installing core packages (torch, opencv, pillow)..."
& $pythonExe -m pip install torch torchvision --no-warn-script-location
& $pythonExe -m pip install opencv-python pillow --no-warn-script-location -q 2>$null

# Install onnxruntime before insightface
Write-Host "  Installing onnxruntime..."
& $pythonExe -m pip install onnxruntime --no-warn-script-location -q 2>$null

# Install insightface (needs numpy and onnxruntime)
Write-Host "  Installing insightface..."
& $pythonExe -m pip install insightface --no-warn-script-location 2>$null

# Install remaining requirements
Write-Host "  Installing remaining packages..."
& $pythonExe -m pip install -r "$ProjectRoot\requirements.txt" --no-warn-script-location 2>$null

# Install pyinstaller
Write-Host "  Installing pyinstaller..."
& $pythonExe -m pip install pyinstaller --no-warn-script-location -q 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: Some packages may have had issues. Continuing anyway..." -ForegroundColor Yellow
}

Write-Host "  Dependencies installed!" -ForegroundColor Green

# Step 3: Clean previous build
Write-Host ""
Write-Host "[3/5] Cleaning previous build..."

Remove-Item -Recurse -Force "$ScriptDir\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ScriptDir\dist" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $OutputDir -ErrorAction SilentlyContinue

# Step 4: Run PyInstaller
Write-Host ""
Write-Host "[4/5] Building executable with PyInstaller..."
Write-Host "  This takes 5-10 minutes..."
Write-Host ""

Push-Location $ScriptDir
& $pythonExe -m PyInstaller photosense_backend.spec --noconfirm
$buildResult = $LASTEXITCODE
Pop-Location

if ($buildResult -ne 0) {
    Write-Host ""
    Write-Host "ERROR: PyInstaller build failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "$ScriptDir\dist\photosense-backend\photosense-backend.exe")) {
    Write-Host ""
    Write-Host "ERROR: Build output not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Build successful!" -ForegroundColor Green

# Step 5: Move to output directory
Write-Host ""
Write-Host "[5/5] Finalizing..."

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Move-Item "$ScriptDir\dist\photosense-backend" "$OutputDir\" -Force

# Create version file
@"
PhotoSense-AI Backend
Version: 1.0.0
Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Platform: Windows
"@ | Out-File -FilePath "$OutputDir\photosense-backend\version.txt" -Encoding UTF8

# Cleanup
Remove-Item -Recurse -Force "$ScriptDir\build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ScriptDir\dist" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  BUILD COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Output: $OutputDir\photosense-backend\"
Write-Host ""
Write-Host "  Next: Run the frontend build script."
Write-Host ""
Read-Host "Press Enter to exit"
