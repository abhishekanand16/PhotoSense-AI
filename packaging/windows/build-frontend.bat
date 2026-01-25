@echo off
:: Build PhotoSense-AI Frontend only
:: This batch file launches the frontend build PowerShell script.
:: Note: Run build-backend.bat first!

title PhotoSense-AI Frontend Build

set "SCRIPT_DIR=%~dp0"

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%build-frontend.ps1"

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% neq 0 (
    echo.
    echo   Frontend build failed with error code: %EXIT_CODE%
)

pause
exit /b %EXIT_CODE%
