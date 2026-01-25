@echo off
setlocal enabledelayedexpansion

title Backend Build

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"
set "VENV_DIR=%SCRIPT_DIR%\.venv"

echo   Building Python backend...
echo.

:: ============================================================
:: Find Python
:: ============================================================
set "PYTHON_EXE="

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if exist "%%~P" (
        set "PYTHON_EXE=%%~P"
        goto :python_found
    )
)

python --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
    goto :python_found
)

echo   ERROR: Python not found
exit /b 1

:python_found

:: ============================================================
:: Create Virtual Environment
:: ============================================================
echo   [1/5] Creating virtual environment...

if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" 2>nul

"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if %ERRORLEVEL% neq 0 (
    echo   ERROR: Failed to create venv
    exit /b 1
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ============================================================
:: Upgrade pip
:: ============================================================
echo   [2/5] Upgrading pip...

"%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel --quiet

:: ============================================================
:: Install Dependencies
:: ============================================================
echo   [3/5] Installing dependencies (10-30 minutes)...

:: Core dependencies first
"%VENV_PIP%" install "numpy>=1.26.4,<2" --quiet
"%VENV_PIP%" install Cython --quiet

:: PyTorch
echo          Installing PyTorch...
"%VENV_PIP%" install torch torchvision --index-url https://download.pytorch.org/whl/cpu --quiet

:: Computer vision
"%VENV_PIP%" install opencv-python pillow --quiet

:: ONNX
"%VENV_PIP%" install onnxruntime "onnx>=1.16.0,<1.18" --quiet

:: InsightFace (critical - may take time to compile)
echo          Installing InsightFace...
"%VENV_PIP%" install insightface --no-build-isolation
if %ERRORLEVEL% neq 0 (
    echo          Retrying InsightFace installation...
    "%VENV_PIP%" install insightface
    if !ERRORLEVEL! neq 0 (
        echo.
        echo   ERROR: InsightFace installation failed
        echo   Install Visual Studio Build Tools from:
        echo   https://aka.ms/vs/17/release/vs_BuildTools.exe
        echo   Select "Desktop development with C++"
        exit /b 1
    )
)

:: Remaining packages
"%VENV_PIP%" install -r "%PROJECT_ROOT%\requirements.txt" --quiet

:: PyInstaller
"%VENV_PIP%" install pyinstaller --quiet

echo          Dependencies installed!

:: ============================================================
:: Clean Previous Build
:: ============================================================
echo   [4/5] Cleaning previous build...

if exist "%SCRIPT_DIR%\build" rmdir /s /q "%SCRIPT_DIR%\build" 2>nul
if exist "%SCRIPT_DIR%\dist" rmdir /s /q "%SCRIPT_DIR%\dist" 2>nul

:: ============================================================
:: Run PyInstaller
:: ============================================================
echo   [5/5] Building with PyInstaller (5-15 minutes)...

cd /d "%SCRIPT_DIR%"
"%VENV_PYTHON%" -m PyInstaller backend.spec --noconfirm --clean --log-level WARN

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: PyInstaller build failed
    exit /b 1
)

:: Verify output
if not exist "%SCRIPT_DIR%\dist\photosense-backend\photosense-backend.exe" (
    echo.
    echo   ERROR: Build output not found
    exit /b 1
)

echo.
echo   ============================================================
echo   BACKEND BUILD COMPLETE
echo   ============================================================
echo.
echo   Output: %SCRIPT_DIR%\dist\photosense-backend\
echo.

exit /b 0
