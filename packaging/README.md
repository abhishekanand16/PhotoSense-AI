# PhotoSense-AI Packaging

This directory contains build scripts for creating distributable installers for PhotoSense-AI.

## Windows Installer

The `windows/` directory contains everything needed to build a Windows installer.

### Quick Start

1. **Open PowerShell** (as Administrator is recommended but not required)

2. **Navigate to the packaging directory:**
   ```powershell
   cd path\to\PhotoSense-AI\packaging\windows
   ```

3. **Run the installer builder:**
   ```powershell
   .\install.ps1
   ```

4. **Follow the prompts** - the script will:
   - Check for required tools (Python, Node.js, Rust)
   - Offer to install missing tools via winget
   - Build the Python backend (~15-30 minutes)
   - Build the Tauri frontend (~10-15 minutes)
   - Create the final installer

5. **Find your installer at:**
   ```
   packaging\windows\dist\PhotoSense-AI-1.0.0-Setup.exe
   ```

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.10+ | `winget install Python.Python.3.12` or [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | `winget install OpenJS.NodeJS.LTS` or [nodejs.org](https://nodejs.org/) |
| Rust | Latest | `winget install Rustlang.Rustup` or [rustup.rs](https://rustup.rs/) |

**Disk Space:** ~20GB free space recommended (for dependencies and build artifacts)

### Build Scripts

| Script | Description |
|--------|-------------|
| `install.ps1` | Main entry point - runs full build with prerequisite checks |
| `build-backend.ps1` | Builds Python backend with PyInstaller |
| `build-frontend.ps1` | Builds Tauri frontend with NSIS installer |

### Build Options

```powershell
# Full build (default)
.\install.ps1

# Skip prerequisite checks (useful for CI/CD)
.\install.ps1 -SkipChecks

# Build only the backend
.\install.ps1 -BackendOnly

# Build only the frontend (requires backend to be built first)
.\install.ps1 -FrontendOnly
```

### Output Structure

After a successful build:

```
packaging/windows/dist/
├── backend/
│   └── photosense-backend/
│       ├── photosense-backend.exe    # Backend executable
│       ├── _internal/                # Python + dependencies
│       └── version.txt               # Build info
└── PhotoSense-AI-1.0.0-Setup.exe     # Final installer
```

### Installer Features

The generated NSIS installer:

- **Single-file installer** - One .exe to distribute
- **User-level installation** - No admin rights required
- **Start Menu shortcuts** - Easy access to the app
- **Desktop shortcut** - Optional during install
- **Uninstaller** - Clean removal via Windows Settings
- **WebView2 auto-install** - Automatically installs Microsoft Edge WebView2 if needed

### Troubleshooting

#### Build Fails at PyInstaller Step

1. Ensure Python 3.10+ is installed and in PATH
2. Try running `build-backend.ps1` separately to see detailed errors
3. Check that all dependencies install correctly

#### Build Fails at Tauri Step

1. Ensure Node.js 18+ and Rust are installed
2. Try running `npm install` manually in `apps/desktop`
3. Check Rust is properly configured: `rustup show`

#### Installer Won't Run

1. Windows SmartScreen may block unsigned executables
2. Click "More info" then "Run anyway"
3. Or sign the executable with a code signing certificate

#### App Won't Start After Installation

1. Check Windows Event Viewer for errors
2. Ensure WebView2 runtime is installed
3. Try running as Administrator once

### Development Notes

- **Backend entry point:** `backend-entry.py` - Clean Python entry for PyInstaller
- **PyInstaller spec:** `backend.spec` - Configures bundling with all ML dependencies
- **Tauri config:** `tauri.conf.json` - Windows-specific Tauri/NSIS configuration

### CI/CD Integration

For automated builds:

```powershell
# PowerShell
.\install.ps1 -SkipChecks

# Or run steps separately
.\build-backend.ps1
.\build-frontend.ps1
```

The scripts return appropriate exit codes (0 for success, non-zero for failure).
