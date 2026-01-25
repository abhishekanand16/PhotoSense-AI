@echo off
:: Build PhotoSense-AI Backend only
:: This batch file launches the backend build PowerShell script.

title PhotoSense-AI Backend Build

set "SCRIPT_DIR=%~dp0"

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%build-backend.ps1"

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% neq 0 (
    echo.
    echo   Backend build failed with error code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
