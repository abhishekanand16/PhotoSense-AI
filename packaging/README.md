# PhotoSense-AI Windows Installer

> Part of [PhotoSense-AI](https://github.com/abhishekanand16/PhotoSense-AI) - Copyright (c) 2026 Abhishek Anand

Build a complete Windows installer for PhotoSense-AI.

## Quick Start

1. Open File Explorer
2. Navigate to `packaging\windows\`
3. **Double-click `install.bat`**
4. Wait 30-60 minutes

That's it. The installer handles everything automatically.

## What It Does

The installer will:
1. Check for Python, Node.js, Rust, and Visual Studio Build Tools
2. Install any missing prerequisites automatically
3. Build the Python backend (~15-30 minutes)
4. Build the Tauri frontend (~10-15 minutes)
5. Create `PhotoSense-AI-1.0.0-Setup.exe`

## Output

```
packaging\windows\dist\PhotoSense-AI-1.0.0-Setup.exe
```

This is your distributable installer. Users just double-click it to install PhotoSense-AI.

## Requirements

- **Windows 10/11** with winget (comes pre-installed)
- **20GB free disk space**
- **Internet connection** (for downloading dependencies)
- **Administrator privileges** (for installing build tools)

## What Gets Installed Automatically

| Tool | Size | Why |
|------|------|-----|
| Python 3.12 | ~100MB | Backend runtime |
| Node.js LTS | ~50MB | Frontend build |
| Rust | ~400MB | Tauri framework |
| Visual Studio Build Tools | ~6GB | C++ compiler for InsightFace |

## Troubleshooting

### "InsightFace installation failed"

Visual Studio Build Tools installation may have failed. Manually install:
1. Download: https://aka.ms/vs/17/release/vs_BuildTools.exe
2. Run installer
3. Select "Desktop development with C++"
4. Wait for installation (~15 minutes)
5. Run `install.bat` again

### "Rust couldn't choose a version"

1. Open a NEW terminal/command prompt
2. Run: `rustup default stable`
3. Close terminal
4. Run `install.bat` again

### "Build failed" or other errors

1. Close all terminals
2. Delete `packaging\windows\.venv` folder
3. Delete `packaging\windows\.build` folder
4. Delete `packaging\windows\dist` folder
5. Run `install.bat` again

### Still having issues?

Run each step manually to see detailed errors:

```cmd
cd packaging\windows
build-backend.bat
build-frontend.bat
```

## Build Time Breakdown

First build:
- Prerequisites installation: 20-40 minutes
- Backend build: 15-30 minutes
- Frontend build: 10-15 minutes
- **Total: 45-85 minutes**

Subsequent builds:
- Backend rebuild: 5-10 minutes
- Frontend rebuild: 5-10 minutes
- **Total: 10-20 minutes**

## Manual Prerequisites Installation

If automatic installation fails, install manually:

### Python 3.12
```cmd
winget install Python.Python.3.12
```
Or download from: https://www.python.org/downloads/

### Node.js LTS
```cmd
winget install OpenJS.NodeJS.LTS
```
Or download from: https://nodejs.org/

### Rust
```cmd
winget install Rustlang.Rustup
rustup default stable
```
Or download from: https://rustup.rs/

### Visual Studio Build Tools
```cmd
winget install Microsoft.VisualStudio.2022.BuildTools
```
Or download from: https://aka.ms/vs/17/release/vs_BuildTools.exe

After manual installation, restart your terminal and run `install.bat`.
