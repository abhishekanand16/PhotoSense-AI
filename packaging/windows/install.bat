@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: PhotoSense-AI Windows Installer
:: Complete automated build system
:: ============================================================

title PhotoSense-AI Installer

echo.
echo   ============================================================
echo   PhotoSense-AI Windows Installer
echo   ============================================================
echo.
echo   This will build a complete Windows installer for PhotoSense-AI.
echo   Estimated time: 30-60 minutes on first run.
echo.
echo   The installer will automatically:
echo   - Install Python, Node.js, Rust, and VS Build Tools if needed
echo   - Build the Python backend
echo   - Build the Tauri frontend
echo   - Create PhotoSense-AI-1.0.0-Setup.exe
echo.
pause

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: ============================================================
:: STEP 1: Check and Install Prerequisites
:: ============================================================
echo.
echo   ============================================================
echo   STEP 1: CHECKING PREREQUISITES
echo   ============================================================
echo.

:: ------------------------------------------------------------
:: Python Check
:: ------------------------------------------------------------
echo   [1/4] Checking Python...

set "PYTHON_EXE="

:: Check known locations first
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
    if exist "%%~P" (
        set "PYTHON_EXE=%%~P"
        for /f "tokens=*" %%V in ('"%%~P" --version 2^>^&1') do echo          %%V found
        goto :python_ok
    )
)

:: Check PATH
python --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
    for /f "tokens=*" %%V in ('python --version 2^>^&1') do echo          %%V found
    goto :python_ok
)

:: Install Python
echo          Not found. Installing Python 3.12...
where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    timeout /t 5 >nul
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
) else (
    echo          ERROR: winget not found. Please install Python manually from python.org
    pause
    exit /b 1
)

:python_ok

:: ------------------------------------------------------------
:: Node.js Check
:: ------------------------------------------------------------
echo   [2/4] Checking Node.js...

set "NODE_EXE="

if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    for /f "tokens=*" %%V in ('"%ProgramFiles%\nodejs\node.exe" --version 2^>^&1') do echo          %%V found
    goto :node_ok
)

node --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NODE_EXE=node"
    for /f "tokens=*" %%V in ('node --version 2^>^&1') do echo          %%V found
    goto :node_ok
)

:: Install Node.js
echo          Not found. Installing Node.js LTS...
where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
    timeout /t 5 >nul
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    set "PATH=%ProgramFiles%\nodejs;%PATH%"
) else (
    echo          ERROR: winget not found. Please install Node.js manually from nodejs.org
    pause
    exit /b 1
)

:node_ok

:: ------------------------------------------------------------
:: Rust Check
:: ------------------------------------------------------------
echo   [3/4] Checking Rust...

set "CARGO_EXE="

if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    for /f "tokens=*" %%V in ('"%USERPROFILE%\.cargo\bin\cargo.exe" --version 2^>^&1') do echo          %%V found
    
    :: Ensure default toolchain is set
    "%USERPROFILE%\.cargo\bin\rustup.exe" default stable >nul 2>nul
    goto :rust_ok
)

cargo --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "CARGO_EXE=cargo"
    for /f "tokens=*" %%V in ('cargo --version 2^>^&1') do echo          %%V found
    
    :: Ensure default toolchain is set
    rustup default stable >nul 2>nul
    goto :rust_ok
)

:: Install Rust
echo          Not found. Installing Rust...
echo          This may take 5-10 minutes...

set "RUSTUP_INIT=%TEMP%\rustup-init.exe"
curl -sSf -o "%RUSTUP_INIT%" https://win.rustup.rs/x86_64

if exist "%RUSTUP_INIT%" (
    echo          Running Rust installer...
    "%RUSTUP_INIT%" -y --default-toolchain stable --profile minimal
    del "%RUSTUP_INIT%"
    
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
    
    timeout /t 3 >nul
    
    if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo          Rust installed successfully
    ) else (
        echo          ERROR: Rust installation failed
        pause
        exit /b 1
    )
) else (
    echo          ERROR: Could not download Rust installer
    pause
    exit /b 1
)

:rust_ok

:: ------------------------------------------------------------
:: Visual Studio Build Tools Check
:: ------------------------------------------------------------
echo   [4/4] Checking Visual Studio Build Tools...

set "VS_FOUND=0"

for %%V in (2022 2019 2017) do (
    if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\%%V\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
        set "VS_FOUND=1"
        echo          Visual Studio %%V Build Tools found
        goto :vs_ok
    )
    if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\%%V\Community\VC\Auxiliary\Build\vcvars64.bat" (
        set "VS_FOUND=1"
        echo          Visual Studio %%V Community found
        goto :vs_ok
    )
)

:vs_ok
if "%VS_FOUND%"=="0" (
    echo          Not found. Installing VS Build Tools...
    echo          This may take 15-30 minutes and requires ~6GB download...
    echo.
    
    where winget >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        winget install Microsoft.VisualStudio.2022.BuildTools --silent --accept-package-agreements --accept-source-agreements --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
        echo          Build Tools installed
    ) else (
        echo          WARNING: Could not install Build Tools automatically
        echo          InsightFace may fail to install
        echo          You can install manually from: https://aka.ms/vs/17/release/vs_BuildTools.exe
        echo.
        timeout /t 5
    )
)

echo.
echo   All prerequisites ready!
echo.

:: ============================================================
:: STEP 2: Build Backend
:: ============================================================
echo.
echo   ============================================================
echo   STEP 2: BUILDING BACKEND
echo   ============================================================
echo.

cd /d "%SCRIPT_DIR%"
call build-backend.bat

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Backend build failed!
    pause
    exit /b 1
)

:: ============================================================
:: STEP 3: Build Frontend
:: ============================================================
echo.
echo   ============================================================
echo   STEP 3: BUILDING FRONTEND
echo   ============================================================
echo.

cd /d "%SCRIPT_DIR%"
call build-frontend.bat

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Frontend build failed!
    pause
    exit /b 1
)

:: ============================================================
:: Done!
:: ============================================================
echo.
echo   ============================================================
echo   BUILD COMPLETE!
echo   ============================================================
echo.
echo   Installer created: %SCRIPT_DIR%\dist\PhotoSense-AI-1.0.0-Setup.exe
echo.
echo   You can now distribute this installer to Windows users.
echo.
pause
exit /b 0
