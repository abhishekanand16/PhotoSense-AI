#
# Build PhotoSense-AI Backend for Windows
#

$ScriptDir = $PSScriptRoot
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$OutputDir = "$ScriptDir\..\dist\backend"
$PortableDir = "$ScriptDir\.python-portable"

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
    
    # Configure for pip
    Write-Host "  Configuring..."
    $pthFile = Get-ChildItem "$PortableDir\python*._pth" | Select-Object -First 1
    if ($pthFile) {
        (Get-Content $pthFile.FullName) -replace '#import site', 'import site' | Set-Content $pthFile.FullName
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

# Step 2: Install Dependencies
Write-Host ""
Write-Host "[2/5] Installing dependencies (this takes 15-30 minutes first time)..."
Write-Host ""

Write-Host "  Installing pip and pyinstaller..."
& $pythonExe -m pip install --upgrade pip --no-warn-script-location --quiet 2>$null
& $pythonExe -m pip install pyinstaller --no-warn-script-location --quiet 2>$null

Write-Host "  Installing project requirements..."
Write-Host "  (torch, transformers, ultralytics, insightface, etc.)"
Write-Host "  Please wait..."
Write-Host ""

& $pythonExe -m pip install -r "$ProjectRoot\requirements.txt" --no-warn-script-location 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Write-Host "Trying again with verbose output..."
    & $pythonExe -m pip install -r "$ProjectRoot\requirements.txt" --no-warn-script-location
    if ($LASTEXITCODE -ne 0) {
        Read-Host "Press Enter to exit"
        exit 1
    }
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
