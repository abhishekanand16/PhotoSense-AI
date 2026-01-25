# PhotoSense-AI Packaging

Build scripts for creating distributable installers for PhotoSense-AI.

## Windows Installer

### Quick Start

1. Navigate to `packaging\windows\` in File Explorer
2. **Double-click `install.bat`**
3. Follow the prompts

That's it! The script will:
- Check for required tools (Python, Node.js, Rust)
- Build the Python backend (~15-30 minutes)
- Build the Tauri frontend (~10-15 minutes)
- Create the final installer

### Output

After successful build:
```
packaging\windows\dist\PhotoSense-AI-1.0.0-Setup.exe
```

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.10+ | `winget install Python.Python.3.12` or [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ | `winget install OpenJS.NodeJS.LTS` or [nodejs.org](https://nodejs.org/) |
| Rust | Latest | `winget install Rustlang.Rustup` or [rustup.rs](https://rustup.rs/) |

**Disk Space:** ~20GB free space recommended

### Build Scripts

| File | Description |
|------|-------------|
| `install.bat` | **Main entry point** - builds everything |
| `build-backend.bat` | Builds Python backend only |
| `build-frontend.bat` | Builds Tauri frontend only (run backend first) |

### Troubleshooting

**"Python not found"**
- Install Python from https://www.python.org/downloads/
- Check "Add Python to PATH" during installation
- Restart the command prompt

**"Node.js not found"**
- Install Node.js LTS from https://nodejs.org/
- Restart the command prompt

**"Rust not found"**
- Install Rust from https://rustup.rs/
- Restart the command prompt after installation

**Build takes too long**
- First build downloads ~5GB of dependencies
- Subsequent builds are faster

**Installer won't run**
- Windows SmartScreen may block unsigned executables
- Click "More info" then "Run anyway"
