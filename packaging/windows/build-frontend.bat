@echo off
setlocal enabledelayedexpansion

title Frontend Build

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..\.." ) do set "PROJECT_ROOT=%%~fI"
set "DESKTOP_SRC=%PROJECT_ROOT%\apps\desktop"
set "BACKEND_BUNDLE=%SCRIPT_DIR%\dist\photosense-backend"
set "BUILD_DIR=%SCRIPT_DIR%\.build"

echo   Building Tauri frontend...
echo.

:: ============================================================
:: Check Backend
:: ============================================================
if not exist "%BACKEND_BUNDLE%\photosense-backend.exe" (
    echo   ERROR: Backend not built. Run build-backend.bat first.
    exit /b 1
)

:: ============================================================
:: Find Node.js
:: ============================================================
set "NODE_EXE="
set "NPM_EXE="

if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
    set "NPM_EXE=%ProgramFiles%\nodejs\npm.cmd"
    goto :node_found
)

node --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "NODE_EXE=node"
    set "NPM_EXE=npm"
    goto :node_found
)

echo   ERROR: Node.js not found
exit /b 1

:node_found

:: ============================================================
:: Find Rust/Cargo
:: ============================================================
set "CARGO_EXE="

if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    set "CARGO_EXE=%USERPROFILE%\.cargo\bin\cargo.exe"
    
    :: Critical: Ensure default toolchain is set
    "%USERPROFILE%\.cargo\bin\rustup.exe" default stable >nul 2>nul
    goto :rust_found
)

cargo --version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "CARGO_EXE=cargo"
    
    :: Critical: Ensure default toolchain is set
    rustup default stable >nul 2>nul
    goto :rust_found
)

echo   ERROR: Rust not found
exit /b 1

:rust_found

:: ============================================================
:: Setup Build Directory
:: ============================================================
echo   [1/4] Setting up build directory...

if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%" 2>nul
mkdir "%BUILD_DIR%"

xcopy /E /I /Q /Y "%DESKTOP_SRC%\*" "%BUILD_DIR%\" >nul
copy /Y "%SCRIPT_DIR%\tauri.conf.json" "%BUILD_DIR%\src-tauri\" >nul

:: ============================================================
:: Copy Backend
:: ============================================================
echo   [2/4] Copying backend bundle...

set "RESOURCES_DIR=%BUILD_DIR%\src-tauri\resources\backend"
if exist "%RESOURCES_DIR%" rmdir /s /q "%RESOURCES_DIR%" 2>nul
mkdir "%RESOURCES_DIR%"

xcopy /E /I /Q /Y "%BACKEND_BUNDLE%\*" "%RESOURCES_DIR%\" >nul

:: ============================================================
:: Install npm Dependencies
:: ============================================================
echo   [3/4] Installing npm dependencies...

cd /d "%BUILD_DIR%"
call "%NPM_EXE%" install --loglevel=error

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: npm install failed
    exit /b 1
)

:: ============================================================
:: Build Tauri
:: ============================================================
echo   [4/4] Building Tauri (5-15 minutes)...

call "%NPM_EXE%" run tauri build -- --verbose

if %ERRORLEVEL% neq 0 (
    echo.
    echo   ERROR: Tauri build failed
    cd /d "%SCRIPT_DIR%"
    exit /b 1
)

cd /d "%SCRIPT_DIR%"

:: ============================================================
:: Move Output
:: ============================================================
echo   Moving installer...

set "NSIS_DIR=%BUILD_DIR%\src-tauri\target\release\bundle\nsis"
set "OUTPUT_DIR=%SCRIPT_DIR%\dist"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

for %%F in ("%NSIS_DIR%\*.exe") do (
    copy /Y "%%F" "%OUTPUT_DIR%\PhotoSense-AI-1.0.0-Setup.exe" >nul
    echo   Created: %OUTPUT_DIR%\PhotoSense-AI-1.0.0-Setup.exe
    goto :done
)

echo   WARNING: Installer not found in expected location

:done
echo.
echo   ============================================================
echo   FRONTEND BUILD COMPLETE
echo   ============================================================
echo.

exit /b 0
