# PhotoSense-AI Packaging

This folder contains everything needed to build installable desktop applications for **macOS** and **Windows**.

## Quick Start

### macOS (creates .dmg installer)
```bash
cd packaging
./build-macos.sh
```
Output: `dist/PhotoSense-AI-1.0.0-macos.dmg`

### Windows (creates .exe installer)

**Option 1: Double-click (Recommended)**
1. Navigate to the `packaging` folder in File Explorer
2. Double-click `build-windows.bat`
3. Follow the prompts

**Option 2: PowerShell (if you get execution policy errors)**
```powershell
cd packaging
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

**Option 3: Enable scripts permanently (requires admin)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd packaging
.\build-windows.ps1
```

Output: `dist\PhotoSense-AI-1.0.0-windows-setup.exe`

> **Note:** If Python is not installed, the script will offer to download a portable version automatically.

## What Gets Built

The build process creates a **self-contained application** that includes:
- The React/Tauri desktop UI
- The Python ML backend (bundled as executable)
- All ML model download scripts
- No Python or Node.js installation required by end users

## Folder Structure

```
packaging/
├── README.md                 # This file
├── build-macos.sh           # One-click macOS build script
├── build-windows.ps1        # One-click Windows build script
├── backend/                  # Python backend bundling
│   ├── photosense_backend.py    # Entry point for bundled backend
│   ├── photosense_backend.spec  # PyInstaller spec file
│   └── build.sh / build.ps1     # Backend-only build scripts
├── frontend/                 # Tauri desktop app
│   ├── tauri.conf.json          # Tauri config for bundled app
│   ├── src/
│   │   └── main.rs              # Rust code to launch sidecar
│   └── build.sh / build.ps1     # Frontend-only build scripts
├── installer/                # Installer creation
│   ├── macos/
│   │   ├── create-dmg.sh        # DMG creation script
│   │   ├── dmg-background.png   # DMG background image
│   │   └── entitlements.plist   # macOS code signing
│   └── windows/
│       ├── installer.nsi        # NSIS installer script
│       └── installer-icon.ico   # Installer icon
└── dist/                     # Build outputs (git-ignored)
```

## Requirements

### macOS Build Machine
- macOS 12+ (for universal binary support)
- Xcode Command Line Tools: `xcode-select --install`
- Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- Node.js 18+: `brew install node`
- Python 3.10+: `brew install python@3.10`
- create-dmg: `brew install create-dmg`

### Windows Build Machine
- Windows 10/11
- **For backend only**: No prerequisites! Script auto-downloads portable Python if needed.
- **For full app build**:
  - Node.js 18+: https://nodejs.org (or `winget install OpenJS.NodeJS.LTS`)
  - Rust: https://rustup.rs (or `winget install Rustlang.Rustup`)
  - Visual Studio Build Tools: Installed automatically with Rust

> **Tip:** On Windows 11, you can install everything with:
> ```
> winget install OpenJS.NodeJS.LTS
> winget install Rustlang.Rustup
> ```

## Build Process Details

### 1. Backend Bundling (PyInstaller)
- Bundles entire Python environment + dependencies
- Creates single executable: `photosense-backend` (macOS) or `photosense-backend.exe` (Windows)
- Includes all ML pipeline code from `services/`

### 2. Frontend Build (Tauri)
- Builds React app with Vite
- Compiles Rust wrapper that:
  - Launches the bundled backend as a sidecar process
  - Manages backend lifecycle (start on app open, stop on close)
  - Provides native window chrome

### 3. Installer Creation
- **macOS**: Creates `.dmg` with drag-to-Applications interface
- **Windows**: Creates NSIS installer with Start Menu shortcuts

## Troubleshooting

### Windows: "Execution of scripts is disabled on this system"
This is a PowerShell security feature. Solutions:

**Solution 1 (Recommended):** Use the `.bat` files instead
- Double-click `build-windows.bat` - it bypasses the policy automatically

**Solution 2:** Run PowerShell with bypass flag
```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

**Solution 3:** Change execution policy permanently
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows: "Python not found"
The build script will automatically offer to download a portable Python. Just press `Y` when prompted.

If you prefer to install Python system-wide:
1. Download from https://python.org/downloads
2. **Important:** Check "Add Python to PATH" during installation
3. Restart your terminal and try again

### "Backend failed to start"
- Check if port 8000 is already in use
- Look at logs in: `~/Library/Application Support/PhotoSense-AI/logs/` (macOS) or `%APPDATA%/PhotoSense-AI/logs/` (Windows)

### "Models downloading slowly"
- First launch downloads ~2GB of ML models
- This is one-time; subsequent launches are fast

### macOS "App is damaged" error
- The app isn't code-signed for distribution
- Right-click → Open → Open anyway
- Or: `xattr -cr /Applications/PhotoSense-AI.app`

### Windows SmartScreen warning
- Click "More info" → "Run anyway"
- This is because the app isn't code-signed
