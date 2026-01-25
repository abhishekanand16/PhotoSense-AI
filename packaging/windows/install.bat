@echo off
:: ============================================================
:: PhotoSense-AI Windows Installer Builder
:: ============================================================
:: This batch file launches the PowerShell installer script.
:: Double-click this file to build the Windows installer.
:: ============================================================

title PhotoSense-AI Installer Builder

echo.
echo   ============================================================
echo   PhotoSense-AI Windows Installer Builder
echo   ============================================================
echo.

:: Check if PowerShell is available
where powershell >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   ERROR: PowerShell is not installed or not in PATH.
    echo   Please install PowerShell or run install.ps1 directly.
    echo.
    pause
    exit /b 1
)

:: Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

:: Run the PowerShell script with execution policy bypass
echo   Starting PowerShell installer...
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%install.ps1"

:: Capture exit code
set "EXIT_CODE=%ERRORLEVEL%"

:: If PowerShell script failed, show message
if %EXIT_CODE% neq 0 (
    echo.
    echo   Build failed with error code: %EXIT_CODE%
    echo.
)

:: Keep window open
echo.
pause
exit /b %EXIT_CODE%
