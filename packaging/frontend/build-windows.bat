@echo off
REM ============================================================
REM PhotoSense-AI Frontend Build Script for Windows
REM 
REM Double-click this file to build the frontend.
REM This bypasses PowerShell execution policy restrictions.
REM ============================================================

echo.
echo ============================================================
echo   PhotoSense-AI Frontend Build
echo ============================================================
echo.

REM Run PowerShell with bypass policy
powershell -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed! See errors above.
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
pause
