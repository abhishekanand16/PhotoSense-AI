# PhotoSense-AI macOS Installer

> Part of [PhotoSense-AI](https://github.com/abhishekanand16/PhotoSense-AI) - Copyright (c) 2026 Abhishek Anand

Build a universal DMG installer for PhotoSense-AI on macOS.

## Quick Start

```bash
cd packaging/macos
./build.sh
```

Wait 30-45 minutes. The installer will be created at `packaging/macos/dist/PhotoSense-AI.dmg`.

## What It Does

The build script will:
1. Build the Python backend with PyInstaller (~15-20 minutes)
2. Bundle the backend into the Tauri app
3. Build a universal Tauri app for Intel + Apple Silicon (~15-20 minutes)
4. Create a DMG installer

## Output

```
packaging/macos/dist/PhotoSense-AI.dmg
```

This DMG contains:
- **Universal binary** - Works on Intel Macs and Apple Silicon (M1/M2/M3/M4)
- **Self-contained** - All dependencies bundled inside
- **Python backend** - Included as a resource in the app
- **ML models** - Downloaded on first run

## Requirements

- **macOS 11+** (Big Sur or later)
- **Xcode Command Line Tools** - `xcode-select --install`
- **Python 3.10+** - `python3 --version`
- **Node.js 18+** - `node --version`
- **Rust** - `rustup --version`
- **20GB free disk space**
- **Internet connection** (for downloading dependencies)

## Installation

Users simply:
1. Double-click `PhotoSense-AI.dmg`
2. Drag `PhotoSense-AI.app` to the Applications folder
3. Launch from Applications or Spotlight

## Build Time

First build:
- Backend build: 15-20 minutes
- Frontend build: 15-20 minutes
- **Total: 30-45 minutes**

Subsequent builds:
- Backend rebuild: 5-10 minutes
- Frontend rebuild: 10-15 minutes
- **Total: 15-25 minutes**

## Troubleshooting

### "Command not found: rustup"

Install Rust:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### "Target x86_64-apple-darwin is not installed"

The build script automatically installs both targets, but if you see this error:
```bash
rustup target add x86_64-apple-darwin
rustup target add aarch64-apple-darwin
```

### "PyInstaller build failed"

Make sure all Python dependencies install correctly:
```bash
cd packaging/macos
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../../requirements.txt
```

### "npm install failed"

Clear npm cache and try again:
```bash
npm cache clean --force
cd packaging/macos
./build.sh
```

### Build takes too long

First build downloads:
- ~2GB of Python packages (PyTorch, Transformers, etc.)
- ~500MB of Rust crates (Tauri dependencies)
- Total: ~2.5GB

Subsequent builds are much faster (15-25 minutes).

## Manual Prerequisites Installation

If automatic installation fails:

### Xcode Command Line Tools
```bash
xcode-select --install
```

### Python 3.12
```bash
brew install python@3.12
```

### Node.js LTS
```bash
brew install node
```

### Rust
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

## Distribution

The DMG is **not code-signed** by default. For public distribution:

1. **Get an Apple Developer account** ($99/year)
2. **Code sign the app**:
   ```bash
   codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" PhotoSense-AI.app
   ```
3. **Notarize with Apple**:
   ```bash
   xcrun notarytool submit PhotoSense-AI.dmg --apple-id your@email.com --password app-specific-password --team-id TEAMID
   ```

Without code signing, users will see "PhotoSense-AI.app cannot be opened because the developer cannot be verified."

**Workaround for users:**
1. Right-click the app
2. Select "Open"
3. Click "Open" in the dialog

This only needs to be done once per installation.
