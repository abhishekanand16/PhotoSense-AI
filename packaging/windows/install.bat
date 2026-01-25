@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: PhotoSense-AI Windows Installer Builder
:: ============================================================
:: Double-click this file to build the Windows installer.
:: Automatically installs missing prerequisites.
:: ============================================================

title PhotoSense-AI Installer Builder
color 0B

echo.
echo   ================================================================
echo   ^|                                                              ^|
echo   ^|           PhotoSense-AI Windows Installer                    ^|
echo   ^|                    Version 1.0.0                             ^|
echo   ^|                                                              ^|
echo   ================================================================
echo.

:: Get script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Get project root (two levels up)
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"

echo   Project: %PROJECT_ROOT%
echo.

:: ============================================================
:: Check and Install Prerequisites
:: ============================================================
echo   ================================================================
echo   CHECKING PREREQUISITES
echo   ================================================================
echo.

:: ============================================================
:: Check/Install Python (check known paths FIRST to avoid Windows Store alias)
:: ============================================================
echo   [1/3] Python 3.10+...
set "PYTHON_EXE="

:: Check common installation locations FIRST
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
) do (
    if exist "%%~P" (
        set "PYTHON_EXE=%%~P"
        for /f "tokens=*" %%V in ('"%%~P" --version 2^>^&1') do echo          Found: %%V
        goto :python_found
    )
)

:: Check if python in PATH actually works (test it, don't trust "where")
python -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_EXE=python"
    for /f "tokens=*" %%V in ('python --version 2^>^&1') do echo          Found: %%V
    goto :python_found
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
        timeout /t 3 >nul
        goto :python_found
    )
)

:: Try downloading installer
echo          Downloading Python installer...
set "PY_INSTALLER=%TEMP%\python_installer.exe"
curl -L -o "%PY_INSTALLER%" "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" 2>nul
if exist "%PY_INSTALLER%" (
    echo          Running Python installer...
    "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    timeout /t 15 >nul
    del "%PY_INSTALLER%" 2>nul
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    if exist "!PYTHON_EXE!" (
        echo          Python installed successfully!
        goto :python_found
    )
)

echo          ERROR: Could not install Python automatically.
echo          Please install from https://www.python.org/downloads/
pause
exit /b 1

:python_found

:: ============================================================
:: Check/Install Node.js
:: ============================================================
echo   [2/3] Node.js 18+...
set "NODE_EXE="

:: Check common locations first
if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    for /f "tokens=*" %%V in ('"%ProgramFiles%\nodejs\node.exe" --version 2^>^&1') do echo          Found: Node.js %%V
    goto :node_found
)

:: Check if node in PATH works
node --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NODE_EXE=node"
    for /f "tokens=*" %%V in ('node --version 2^>^&1') do echo          Found: Node.js %%V
    goto :node_found
)

:: Node.js not found - install it
echo          Node.js not found. Installing automatically...
echo.

where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo          Installing Node.js via winget...
    winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% equ 0 (
        echo          Node.js installed successfully!
        set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
        set "PATH=%ProgramFiles%\nodejs;%PATH%"
        timeout /t 3 >nul
        goto :node_found
    )
)

:: Try downloading installer
echo          Downloading Node.js installer...
set "NODE_INSTALLER=%TEMP%\node_installer.msi"
curl -L -o "%NODE_INSTALLER%" "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi" 2>nul
if exist "%NODE_INSTALLER%" (
    echo          Running Node.js installer...
    msiexec /i "%NODE_INSTALLER%" /quiet /norestart
    timeout /t 10 >nul
    del "%NODE_INSTALLER%" 2>nul
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    set "PATH=%ProgramFiles%\nodejs;%PATH%"
    if exist "!NODE_EXE!" (
        echo          Node.js installed successfully!
        goto :node_found
    )
)

echo          ERROR: Could not install Node.js automatically.
echo          Please install from https://nodejs.org/
pause
exit /b 1

:node_found

:: ============================================================
:: Check/Install Rust
:: ============================================================
echo   [3/3] Rust (cargo)...
set "CARGO_EXE="

:: Check user profile location first
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    for /f "tokens=2" %%V in ('"%USERPROFILE%\.cargo\bin\cargo.exe" --version 2^>^&1') do echo          Found: Rust %%V
    goto :rust_found
)

:: Check if cargo in PATH works
cargo --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "CARGO_EXE=cargo"
    for /f "tokens=2" %%V in ('cargo --version 2^>^&1') do echo          Found: Rust %%V
    goto :rust_found
)

:: Rust not found - install it
echo          Rust not found. Installing automatically...
echo.

where winget >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo          Installing Rust via winget...
    winget install Rustlang.Rustup --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% equ 0 (
        echo          Initializing Rust...
        "%USERPROFILE%\.cargo\bin\rustup.exe" default stable 2>nul
        set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
        set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
        timeout /t 3 >nul
        echo          Rust installed successfully!
        goto :rust_found
    )
)

:: Try downloading rustup-init directly
echo          Downloading Rust installer...
set "RUSTUP_INIT=%TEMP%\rustup-init.exe"
curl -L -o "%RUSTUP_INIT%" "https://win.rustup.rs/x86_64" 2>nul
if exist "%RUSTUP_INIT%" (
    echo          Running Rust installer...
    "%RUSTUP_INIT%" -y --default-toolchain stable 2>nul
    timeout /t 5 >nul
    del "%RUSTUP_INIT%" 2>nul
    set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    if exist "!CARGO_EXE!" (
        echo          Rust installed successfully!
        goto :rust_found
    )
)

echo          ERROR: Could not install Rust automatically.
echo          Please install from https://rustup.rs/
pause
exit /b 1

:rust_found

echo.
echo   All prerequisites OK!
echo.

:: ============================================================
:: Step 1: Build Backend
:: ============================================================
echo   ================================================================
echo   STEP 1: BUILD PYTHON BACKEND
echo   ================================================================
echo.

call "%SCRIPT_DIR%\build-backend.bat"
if %ERRORLEVEL% neq 0 (
    echo.
    echo   Backend build failed!
    pause
    exit /b 1
)

:: ============================================================
:: Step 2: Build Frontend
:: ============================================================
echo.
echo   ================================================================
echo   STEP 2: BUILD TAURI FRONTEND
echo   ================================================================
echo.

call "%SCRIPT_DIR%\build-frontend.bat"
if %ERRORLEVEL% neq 0 (
    echo.
    echo   Frontend build failed!
    pause
    exit /b 1
)

:: ============================================================
:: Done
:: ============================================================
set "INSTALLER=%SCRIPT_DIR%\dist\PhotoSense-AI-1.0.0-Setup.exe"

if exist "%INSTALLER%" (
    echo.
    echo   ================================================================
    echo   ^|                    BUILD SUCCESSFUL!                         ^|
    echo   ================================================================
    echo.
    echo   Installer: %INSTALLER%
    echo.
    echo   To install PhotoSense-AI:
    echo   1. Double-click PhotoSense-AI-1.0.0-Setup.exe
    echo   2. Follow the installation wizard
    echo   3. Launch from Start Menu or Desktop
    echo.
    
    set /p "OPEN_FOLDER=  Open dist folder? [Y/N]: "
    if /i "!OPEN_FOLDER!"=="Y" (
        explorer "%SCRIPT_DIR%\dist"
    )
) else (
    echo.
    echo   ================================================================
    echo   BUILD COMPLETED - Check dist folder for outputs
    echo   ================================================================
    echo.
)

pause
exit /b 0
