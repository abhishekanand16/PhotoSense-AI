@echo off
REM ============================================================
REM PhotoSense-AI Complete Windows Build
REM 
REM Double-click this file to build everything:
REM   1. Python backend (standalone .exe)
REM   2. Tauri frontend with installer
REM 
REM Output: dist\PhotoSense-AI-1.0.0-windows-setup.exe
REM ============================================================

echo.
echo ================================================================
echo.
echo           PhotoSense-AI Windows Build
echo           Version: 1.0.0
echo.
echo ================================================================
echo.

set SCRIPT_DIR=%~dp0
set DIST_DIR=%SCRIPT_DIR%dist

REM Create dist directory
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

REM Step 1: Build Backend
echo.
echo ----------------------------------------------------------------
echo   Step 1/2: Building Python Backend
echo ----------------------------------------------------------------
echo.

powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%backend\build-windows.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Backend build failed!
    pause
    exit /b 1
)

REM Step 2: Build Frontend
echo.
echo ----------------------------------------------------------------
echo   Step 2/2: Building Tauri Frontend
echo ----------------------------------------------------------------
echo.

powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%frontend\build-windows.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Frontend build failed!
    pause
    exit /b 1
)

REM Find and rename installer
echo.
echo ----------------------------------------------------------------
echo   Finalizing...
echo ----------------------------------------------------------------
echo.

for %%f in ("%DIST_DIR%\frontend\*setup*.exe") do (
    copy "%%f" "%DIST_DIR%\PhotoSense-AI-1.0.0-windows-setup.exe" >nul 2>&1
)

if exist "%DIST_DIR%\PhotoSense-AI-1.0.0-windows-setup.exe" (
    echo.
    echo ================================================================
    echo                     BUILD COMPLETE
    echo ================================================================
    echo.
    echo   Installer: dist\PhotoSense-AI-1.0.0-windows-setup.exe
    echo.
    echo   To install:
    echo   1. Double-click the installer
    echo   2. Follow the installation wizard
    echo   3. Launch from Start Menu or Desktop
    echo.
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo                     BUILD COMPLETE
    echo ================================================================
    echo.
    echo   Note: Installer may be in dist\frontend\
    echo.
    echo ================================================================
)

echo.
pause
