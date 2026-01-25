@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Build PhotoSense-AI Frontend (Tauri) for Windows
:: Creates the NSIS installer with backend sidecar
:: ============================================================

title PhotoSense-AI Frontend Build

:: Get directories
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"
set "DESKTOP_SRC=%PROJECT_ROOT%\apps\desktop"
set "BACKEND_BUNDLE=%SCRIPT_DIR%\dist\backend\photosense-backend"
set "BUILD_DIR=%SCRIPT_DIR%\.build"
set "OUTPUT_DIR=%SCRIPT_DIR%\dist"

echo.
echo   ============================================================
echo   PhotoSense-AI Frontend Build for Windows
echo   ============================================================
echo.
echo   Project Root:   %PROJECT_ROOT%
echo   Desktop Source: %DESKTOP_SRC%
echo.

:: ============================================================
:: Step 1: Check Prerequisites
:: ============================================================
echo   [1/5] Checking prerequisites...

:: Check backend bundle
if not exist "%BACKEND_BUNDLE%\photosense-backend.exe" (
    echo.
    echo          ERROR: Backend bundle not found!
    echo          Run build-backend.bat first.
    echo.
    exit /b 1
)
echo          Backend bundle: OK

:: Check Node.js
set "NODE_EXE="
set "NPM_EXE="

where node >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NODE_EXE=node"
    for /f "tokens=*" %%V in ('node --version 2^>^&1') do echo          Node.js: %%V
) else (
    if exist "%ProgramFiles%\nodejs\node.exe" (
        set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
        echo          Node.js: Found at !NODE_EXE!
    ) else (
        echo          ERROR: Node.js not found!
        exit /b 1
    )
)

:: Find npm
where npm >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NPM_EXE=npm"
) else (
    if exist "%ProgramFiles%\nodejs\npm.cmd" (
        set "NPM_EXE=%ProgramFiles%\nodejs\npm.cmd"
    ) else (
        echo          ERROR: npm not found!
        exit /b 1
    )
)

:: Check Cargo
where cargo >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%V in ('cargo --version 2^>^&1') do echo          Rust: %%V
) else (
    if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
        echo          Rust: Found in user profile
    ) else (
        echo          ERROR: Rust/Cargo not found!
        exit /b 1
    )
)

echo          All prerequisites OK!

:: ============================================================
:: Step 2: Setup Build Directory
:: ============================================================
echo.
echo   [2/5] Setting up build directory...

if exist "%BUILD_DIR%" (
    echo          Removing previous build...
    rmdir /s /q "%BUILD_DIR%" 2>nul
)

echo          Copying desktop source...
mkdir "%BUILD_DIR%" 2>nul
xcopy /E /I /Q /Y "%DESKTOP_SRC%\*" "%BUILD_DIR%\" >nul

:: Copy Windows-specific Tauri config
echo          Applying Windows Tauri config...
copy /Y "%SCRIPT_DIR%\tauri.conf.json" "%BUILD_DIR%\src-tauri\" >nul

echo          Build directory ready!

:: ============================================================
:: Step 3: Copy Backend Resources
:: ============================================================
echo.
echo   [3/5] Copying backend resources...

set "RESOURCES_DIR=%BUILD_DIR%\src-tauri\resources\backend"

if exist "%RESOURCES_DIR%" rmdir /s /q "%RESOURCES_DIR%" 2>nul
mkdir "%RESOURCES_DIR%" 2>nul

echo          Copying backend bundle (this may take a moment)...
xcopy /E /I /Q /Y "%BACKEND_BUNDLE%\*" "%RESOURCES_DIR%\" >nul

echo          Backend resources copied!

:: ============================================================
:: Step 4: Install npm Dependencies
:: ============================================================
echo.
echo   [4/5] Installing npm dependencies...

cd /d "%BUILD_DIR%"

call %NPM_EXE% install 2>nul
if %ERRORLEVEL% neq 0 (
    echo          ERROR: npm install failed!
    exit /b 1
)

echo          npm dependencies installed!

:: ============================================================
:: Step 5: Build Tauri Application
:: ============================================================
echo.
echo   [5/5] Building Tauri application...
echo          This takes 5-15 minutes...
echo.

call %NPM_EXE% run tauri build

if %ERRORLEVEL% neq 0 (
    echo.
    echo          ERROR: Tauri build failed!
    cd /d "%SCRIPT_DIR%"
    exit /b 1
)

cd /d "%SCRIPT_DIR%"

:: ============================================================
:: Move Output
:: ============================================================
echo.
echo   Moving build artifacts...

:: Find and copy the NSIS installer
set "NSIS_DIR=%BUILD_DIR%\src-tauri\target\release\bundle\nsis"
set "INSTALLER_FOUND=0"

if exist "%NSIS_DIR%" (
    for %%F in ("%NSIS_DIR%\*.exe") do (
        if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
        copy /Y "%%F" "%OUTPUT_DIR%\PhotoSense-AI-1.0.0-Setup.exe" >nul
        set "INSTALLER_FOUND=1"
        echo          Installer: %OUTPUT_DIR%\PhotoSense-AI-1.0.0-Setup.exe
    )
)

if "%INSTALLER_FOUND%"=="0" (
    echo          WARNING: NSIS installer not found in expected location
    echo          Check: %BUILD_DIR%\src-tauri\target\release\bundle\
)

:: ============================================================
:: Done
:: ============================================================
echo.
echo   ============================================================
echo   FRONTEND BUILD COMPLETE!
echo   ============================================================
echo.
echo   Output: %OUTPUT_DIR%\
echo.

exit /b 0
