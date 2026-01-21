@echo off
title PhotoSense-AI Backend Build

echo.
echo ============================================================
echo   PhotoSense-AI Backend Build
echo ============================================================
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed!
    pause
    exit /b 1
)

exit /b 0
