#
# Build PhotoSense-AI Backend for Windows
# Creates a standalone executable that can run without Python installed
#
# USAGE (run in PowerShell as Administrator OR use the .bat file):
#   Option 1: .\build-windows.ps1
#   Option 2: Double-click build-windows.bat (recommended)
#
# If you get "execution policy" error, run:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName
$OutputDir = "$ScriptDir\..\dist\backend"
$PythonVersion = "3.11.9"
$PythonInstallerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$EmbeddablePythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

Write-Host "============================================================"
Write-Host "Building PhotoSense-AI Backend for Windows"
Write-Host "============================================================"
Write-Host "Project root: $ProjectRoot"
Write-Host "Output dir: $OutputDir"
Write-Host ""

# Function to find Python
function Find-Python {
    # Check common locations
    $pythonPaths = @(
        "python",
        "python3",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python312\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe",
        "$ScriptDir\.python-portable\python.exe"
    )
    
    foreach ($p in $pythonPaths) {
        try {
            $result = & $p --version 2>&1
            if ($LASTEXITCODE -eq 0 -or $result -match "Python 3") {
                return $p
            }
        } catch {
            continue
        }
    }
    return $null
}

# Function to download portable Python
function Install-PortablePython {
    $portableDir = "$ScriptDir\.python-portable"
    $zipFile = "$ScriptDir\python-embed.zip"
    
    Write-Host "Downloading portable Python $PythonVersion..."
    Write-Host "This may take a few minutes..."
    
    try {
        # Download embeddable Python
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($EmbeddablePythonUrl, $zipFile)
        
        # Extract
        Write-Host "Extracting Python..."
        if (Test-Path $portableDir) { Remove-Item -Recurse -Force $portableDir }
        Expand-Archive -Path $zipFile -DestinationPath $portableDir -Force
        Remove-Item $zipFile -Force
        
        # Enable pip by modifying python311._pth
        $pthFile = Get-ChildItem "$portableDir\python*._pth" | Select-Object -First 1
        if ($pthFile) {
            $content = Get-Content $pthFile.FullName
            $content = $content -replace '#import site', 'import site'
            $content | Set-Content $pthFile.FullName
        }
        
        # Download get-pip.py and install pip
        Write-Host "Installing pip..."
        $getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
        $getPipFile = "$portableDir\get-pip.py"
        $webClient.DownloadFile($getPipUrl, $getPipFile)
        
        & "$portableDir\python.exe" $getPipFile --no-warn-script-location 2>&1 | Out-Null
        Remove-Item $getPipFile -Force -ErrorAction SilentlyContinue
        
        Write-Host "Portable Python installed successfully!"
        return "$portableDir\python.exe"
    } catch {
        Write-Host "ERROR: Failed to download/install portable Python: $_"
        return $null
    }
}

# Find or install Python
$pythonExe = Find-Python

if (-not $pythonExe) {
    Write-Host ""
    Write-Host "Python not found on this system."
    Write-Host "Would you like to download a portable Python? (Y/N)"
    $response = Read-Host
    
    if ($response -eq "Y" -or $response -eq "y") {
        $pythonExe = Install-PortablePython
        if (-not $pythonExe) {
            Write-Host ""
            Write-Host "ERROR: Could not install portable Python."
            Write-Host ""
            Write-Host "Please install Python manually from: https://python.org/downloads"
            Write-Host "Make sure to check 'Add Python to PATH' during installation."
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "Please install Python 3.10+ from: https://python.org/downloads"
        Write-Host "Make sure to check 'Add Python to PATH' during installation."
        exit 1
    }
}

$pythonVersion = & $pythonExe --version
Write-Host "Using: $pythonVersion"
Write-Host "Python path: $pythonExe"

# Create virtual environment for clean build
$VenvDir = "$ScriptDir\.build-venv"
Write-Host ""
Write-Host "Creating build virtual environment..."

if (Test-Path $VenvDir) { 
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
}

& $pythonExe -m venv $VenvDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment"
    exit 1
}

# Activate virtual environment
$venvPython = "$VenvDir\Scripts\python.exe"
$venvPip = "$VenvDir\Scripts\pip.exe"

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies (this may take 10-15 minutes)..."
& $venvPip install --upgrade pip 2>&1 | Out-Null
& $venvPip install pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install PyInstaller"
    exit 1
}

Write-Host "Installing project dependencies..."
& $venvPip install -r "$ProjectRoot\requirements.txt" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install project dependencies"
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
Write-Host "Running PyInstaller (this may take 5-10 minutes)..."
Set-Location $ScriptDir
& "$VenvDir\Scripts\pyinstaller.exe" photosense_backend.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller failed"
    exit 1
}

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

Write-Host ""
Write-Host "============================================================"
Write-Host "Backend build complete!"
Write-Host "Output: $OutputDir\photosense-backend\"
Write-Host "============================================================"
