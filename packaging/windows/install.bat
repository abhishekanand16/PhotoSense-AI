@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: PhotoSense-AI Windows Installer Builder
:: ============================================================
:: Double-click this file to build the Windows installer.
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
:: Check Prerequisites
:: ============================================================
echo   ================================================================
echo   CHECKING PREREQUISITES
echo   ================================================================
echo.

set "ALL_OK=1"
set "PYTHON_EXE="
set "NODE_EXE="
set "CARGO_EXE="

:: Check Python
echo   [1/3] Python 3.10+...
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PY_VER=%%V"
    echo          Found: Python !PY_VER!
    set "PYTHON_EXE=python"
) else (
    :: Check common locations
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        echo          Found: !PYTHON_EXE!
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        echo          Found: !PYTHON_EXE!
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        echo          Found: !PYTHON_EXE!
    ) else if exist "C:\Python312\python.exe" (
        set "PYTHON_EXE=C:\Python312\python.exe"
        echo          Found: !PYTHON_EXE!
    ) else if exist "C:\Python311\python.exe" (
        set "PYTHON_EXE=C:\Python311\python.exe"
        echo          Found: !PYTHON_EXE!
    ) else (
        echo          NOT FOUND
        set "ALL_OK=0"
    )
)

:: Check Node.js
echo   [2/3] Node.js 18+...
where node >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1" %%V in ('node --version 2^>^&1') do set "NODE_VER=%%V"
    echo          Found: Node.js !NODE_VER!
    set "NODE_EXE=node"
) else (
    if exist "%ProgramFiles%\nodejs\node.exe" (
        set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
        echo          Found: !NODE_EXE!
    ) else (
        echo          NOT FOUND
        set "ALL_OK=0"
    )
)

:: Check Rust/Cargo
echo   [3/3] Rust (cargo)...
where cargo >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=1,2" %%A in ('cargo --version 2^>^&1') do set "CARGO_VER=%%A %%B"
    echo          Found: !CARGO_VER!
    set "CARGO_EXE=cargo"
) else (
    if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
        echo          Found: !CARGO_EXE!
    ) else (
        echo          NOT FOUND
        set "ALL_OK=0"
    )
)

echo.

:: Handle missing prerequisites
if "%ALL_OK%"=="0" (
    echo   ================================================================
    echo   MISSING PREREQUISITES
    echo   ================================================================
    echo.
    echo   Please install the missing tools:
    echo.
    if "%PYTHON_EXE%"=="" (
        echo   - Python 3.10+
        echo     Download: https://www.python.org/downloads/
        echo     Or run:   winget install Python.Python.3.12
        echo.
    )
    if "%NODE_EXE%"=="" (
        echo   - Node.js 18+
        echo     Download: https://nodejs.org/
        echo     Or run:   winget install OpenJS.NodeJS.LTS
        echo.
    )
    if "%CARGO_EXE%"=="" (
        echo   - Rust
        echo     Download: https://rustup.rs/
        echo     Or run:   winget install Rustlang.Rustup
        echo.
    )
    echo   After installing, restart this script.
    echo.
    pause
    exit /b 1
)

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
