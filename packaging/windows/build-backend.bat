@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Build PhotoSense-AI Backend for Windows
:: Creates a standalone executable using PyInstaller
:: Automatically installs Python if missing.
:: ============================================================

title PhotoSense-AI Backend Build

:: Get directories
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"
set "OUTPUT_DIR=%SCRIPT_DIR%\dist\backend"
set "VENV_DIR=%SCRIPT_DIR%\.venv"

echo.
echo   ============================================================
echo   PhotoSense-AI Backend Build for Windows
echo   ============================================================
echo.
echo   Project Root: %PROJECT_ROOT%
echo   Output Dir:   %OUTPUT_DIR%
echo.

:: ============================================================
:: Step 1: Find or Install Python
:: ============================================================
echo   [1/6] Finding Python...

set "PYTHON_EXE="

:: Check PATH first
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
    for /f "tokens=*" %%V in ('python --version 2^>^&1') do echo          Using: %%V
    goto :found_python
)

:: Check common locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        set "PYTHON_EXE=%%~P"
        echo          Found: !PYTHON_EXE!
        goto :found_python
    )
)

:: Python not found - install it
echo          Python not found. Installing automatically...
echo.

where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo          Installing Python via winget...
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% equ 0 (
        echo          Python installed successfully!
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
        goto :found_python
    )
)

:: Try downloading installer
echo          Downloading Python installer...
set "PY_INSTALLER=%TEMP%\python_installer.exe"
curl -L -o "%PY_INSTALLER%" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" 2>nul
if exist "%PY_INSTALLER%" (
    echo          Running Python installer...
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    timeout /t 10 >nul
    del "%PY_INSTALLER%" 2>nul
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    if exist "!PYTHON_EXE!" (
        echo          Python installed successfully!
        goto :found_python
    )
)

echo          ERROR: Could not install Python automatically.
echo          Please install from https://www.python.org/downloads/
pause
exit /b 1

:found_python

:: ============================================================
:: Step 2: Create Virtual Environment
:: ============================================================
echo.
echo   [2/6] Setting up virtual environment...

if exist "%VENV_DIR%" (
    echo          Removing existing venv...
    rmdir /s /q "%VENV_DIR%" 2>nul
)

echo          Creating new venv...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if %ERRORLEVEL% neq 0 (
    echo          ERROR: Failed to create virtual environment
    exit /b 1
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

echo          Virtual environment created!

:: ============================================================
:: Step 3: Upgrade pip
:: ============================================================
echo.
echo   [3/6] Upgrading pip...

"%VENV_PYTHON%" -m pip install --upgrade pip --quiet 2>nul
echo          pip upgraded!

:: ============================================================
:: Step 4: Install Dependencies
:: ============================================================
echo.
echo   [4/6] Installing dependencies...
echo          This may take 10-30 minutes on first run.
echo.

:: Install in correct order to avoid conflicts
echo          Installing numpy...
"%VENV_PIP%" install "numpy>=1.26.4,<2" --quiet 2>nul

echo          Installing PyTorch...
"%VENV_PIP%" install torch torchvision 2>nul

echo          Installing OpenCV and Pillow...
"%VENV_PIP%" install opencv-python pillow --quiet 2>nul

echo          Installing ONNX Runtime...
"%VENV_PIP%" install onnxruntime --quiet 2>nul
"%VENV_PIP%" install "onnx>=1.16.0,<1.18" --quiet 2>nul

echo          Installing InsightFace...
"%VENV_PIP%" install insightface 2>nul

echo          Installing remaining packages...
"%VENV_PIP%" install -r "%PROJECT_ROOT%\requirements.txt" --quiet 2>nul

echo          Installing PyInstaller...
"%VENV_PIP%" install pyinstaller --quiet 2>nul

echo          Dependencies installed!

:: ============================================================
:: Step 5: Clean Previous Build
:: ============================================================
echo.
echo   [5/6] Cleaning previous build...

if exist "%SCRIPT_DIR%\build" rmdir /s /q "%SCRIPT_DIR%\build" 2>nul
if exist "%SCRIPT_DIR%\dist" rmdir /s /q "%SCRIPT_DIR%\dist" 2>nul

echo          Cleaned!

:: ============================================================
:: Step 6: Run PyInstaller
:: ============================================================
echo.
echo   [6/6] Building executable with PyInstaller...
echo          This takes 5-15 minutes...
echo.

cd /d "%SCRIPT_DIR%"
"%VENV_PYTHON%" -m PyInstaller backend.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo.
    echo          ERROR: PyInstaller build failed!
    exit /b 1
)

:: Verify output
set "BACKEND_EXE=%SCRIPT_DIR%\dist\photosense-backend\photosense-backend.exe"
if not exist "%BACKEND_EXE%" (
    echo.
    echo          ERROR: Build output not found!
    exit /b 1
)

:: Create version file
echo PhotoSense-AI Backend > "%SCRIPT_DIR%\dist\photosense-backend\version.txt"
echo Version: 1.0.0 >> "%SCRIPT_DIR%\dist\photosense-backend\version.txt"
echo Build Date: %DATE% %TIME% >> "%SCRIPT_DIR%\dist\photosense-backend\version.txt"
echo Platform: Windows x64 >> "%SCRIPT_DIR%\dist\photosense-backend\version.txt"

echo.
echo   ============================================================
echo   BACKEND BUILD COMPLETE!
echo   ============================================================
echo.
echo   Output: %SCRIPT_DIR%\dist\photosense-backend\
echo.

exit /b 0
