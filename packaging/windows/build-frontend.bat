@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Build PhotoSense-AI Frontend (Tauri) for Windows
:: Creates the NSIS installer with backend sidecar
:: Automatically installs Node.js and Rust if missing.
:: ============================================================

title PhotoSense-AI Frontend Build

:: Get directories
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"
set "DESKTOP_SRC=%PROJECT_ROOT%\apps\desktop"
set "BACKEND_BUNDLE=%SCRIPT_DIR%\dist\photosense-backend"
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
    pause
    exit /b 1
)
echo          Backend bundle: OK

:: ============================================================
:: Check and Install Node.js
:: ============================================================
set "NODE_EXE="
set "NPM_EXE="

:: Check common location first
if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    set "NPM_EXE=%ProgramFiles%\nodejs\npm.cmd"
    for /f "tokens=*" %%V in ('"%ProgramFiles%\nodejs\node.exe" --version 2^>^&1') do echo          Node.js: %%V
    goto :node_found
)

:: Check if node in PATH works
node --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NODE_EXE=node"
    set "NPM_EXE=npm"
    for /f "tokens=*" %%V in ('node --version 2^>^&1') do echo          Node.js: %%V
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
        set "NPM_EXE=%ProgramFiles%\nodejs\npm.cmd"
        set "PATH=%ProgramFiles%\nodejs;%PATH%"
        timeout /t 3 >nul
        goto :node_found
    )
)

:: Try downloading directly
echo          Downloading Node.js installer...
set "NODE_INSTALLER=%TEMP%\node_installer.msi"
curl -L -o "%NODE_INSTALLER%" "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi" 2>nul
if exist "%NODE_INSTALLER%" (
    echo          Running Node.js installer...
    msiexec /i "%NODE_INSTALLER%" /quiet /norestart
    timeout /t 10 >nul
    del "%NODE_INSTALLER%" 2>nul
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    set "NPM_EXE=%ProgramFiles%\nodejs\npm.cmd"
    set "PATH=%ProgramFiles%\nodejs;%PATH%"
    if exist "!NODE_EXE!" (
        echo          Node.js installed successfully!
        goto :node_found
    )
)

echo          ERROR: Could not install Node.js automatically.
echo          Please install manually from https://nodejs.org/
pause
exit /b 1

:node_found

:: ============================================================
:: Check and Install Rust
:: ============================================================

:: Check user profile location first
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    for /f "tokens=*" %%V in ('"%USERPROFILE%\.cargo\bin\cargo.exe" --version 2^>^&1') do echo          Rust: %%V
    goto :rust_found
)

:: Check if cargo in PATH works
cargo --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%V in ('cargo --version 2^>^&1') do echo          Rust: %%V
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
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo          Rust installed successfully!
        goto :rust_found
    )
)

echo          ERROR: Could not install Rust automatically.
echo          Please install manually from https://rustup.rs/
pause
exit /b 1

:rust_found

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

:: Run npm install with output visible for debugging
echo          Running npm install (this may take a few minutes)...
call "%NPM_EXE%" install

if %ERRORLEVEL% neq 0 (
    echo.
    echo          ERROR: npm install failed!
    echo          Check the error messages above.
    echo.
    echo          Common fixes:
    echo          - Make sure you have internet connection
    echo          - Try running as Administrator
    echo          - Delete node_modules and try again
    echo.
    cd /d "%SCRIPT_DIR%"
    pause
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

call "%NPM_EXE%" run tauri build

if %ERRORLEVEL% neq 0 (
    echo.
    echo          ERROR: Tauri build failed!
    cd /d "%SCRIPT_DIR%"
    pause
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
