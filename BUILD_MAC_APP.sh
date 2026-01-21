#!/bin/bash
#
# ONE-CLICK MAC BUILD - Creates PhotoSense-AI.dmg
# Just run: ./BUILD_MAC_APP.sh
#

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║              PhotoSense-AI Mac App Builder                     ║"
echo "║                                                                ║"
echo "║   This will create a DMG file you can distribute.             ║"
echo "║   The build takes about 10-15 minutes.                        ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"

# Check prerequisites
echo "[1/6] Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required. Install with: brew install python"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required. Install with: brew install node"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "ERROR: Rust is required. Install from: https://rustup.rs"
    exit 1
fi

echo "  ✓ Python: $(python3 --version)"
echo "  ✓ Node: $(node --version)"
echo "  ✓ Rust: $(rustc --version)"

# Install create-dmg if needed
if ! command -v create-dmg &> /dev/null; then
    echo "  Installing create-dmg..."
    brew install create-dmg
fi
echo "  ✓ create-dmg installed"

# Step 2: Setup Python environment
echo ""
echo "[2/6] Setting up Python environment..."

VENV_DIR="$PROJECT_ROOT/.build-venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q
pip install pyinstaller -q
pip install -r "$PROJECT_ROOT/requirements.txt" -q

echo "  ✓ Python dependencies installed"

# Step 3: Build Python backend
echo ""
echo "[3/6] Building Python backend (this takes 3-5 minutes)..."

cd "$PROJECT_ROOT/packaging/backend"
rm -rf build dist
pyinstaller photosense_backend.spec --noconfirm

BACKEND_EXE="$PROJECT_ROOT/packaging/backend/dist/photosense-backend/photosense-backend"
if [ ! -f "$BACKEND_EXE" ]; then
    echo "ERROR: Backend build failed"
    exit 1
fi
echo "  ✓ Backend built successfully"

# Step 4: Setup frontend
echo ""
echo "[4/6] Setting up frontend..."

cd "$PROJECT_ROOT/apps/desktop"
npm install --silent

# Step 5: Build Tauri app
echo ""
echo "[5/6] Building Tauri app (this takes 5-10 minutes)..."

# Copy backend to Tauri binaries
mkdir -p "$PROJECT_ROOT/apps/desktop/src-tauri/binaries"

# Determine architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    TARGET="aarch64-apple-darwin"
else
    TARGET="x86_64-apple-darwin"
fi

# Copy entire backend bundle
cp -r "$PROJECT_ROOT/packaging/backend/dist/photosense-backend/"* "$PROJECT_ROOT/apps/desktop/src-tauri/binaries/"
mv "$PROJECT_ROOT/apps/desktop/src-tauri/binaries/photosense-backend" "$PROJECT_ROOT/apps/desktop/src-tauri/binaries/photosense-backend-$TARGET"
chmod +x "$PROJECT_ROOT/apps/desktop/src-tauri/binaries/photosense-backend-$TARGET"

# Update tauri.conf.json to include sidecar
cd "$PROJECT_ROOT/apps/desktop"
npm run tauri build

# Find the built app
APP_PATH=$(find "$PROJECT_ROOT/apps/desktop/src-tauri/target/release/bundle/macos" -name "*.app" -type d 2>/dev/null | head -1)
if [ -z "$APP_PATH" ]; then
    echo "ERROR: Tauri build failed - no .app found"
    exit 1
fi
echo "  ✓ App built: $(basename "$APP_PATH")"

# Step 6: Create DMG
echo ""
echo "[6/6] Creating DMG installer..."

OUTPUT_DIR="$PROJECT_ROOT/dist"
mkdir -p "$OUTPUT_DIR"
DMG_PATH="$OUTPUT_DIR/PhotoSense-AI.dmg"
rm -f "$DMG_PATH"

create-dmg \
    --volname "PhotoSense-AI" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "$(basename "$APP_PATH")" 150 190 \
    --hide-extension "$(basename "$APP_PATH")" \
    --app-drop-link 450 185 \
    --no-internet-enable \
    "$DMG_PATH" \
    "$APP_PATH" \
    2>/dev/null || hdiutil create -volname "PhotoSense-AI" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf "$PROJECT_ROOT/packaging/backend/build"
rm -rf "$PROJECT_ROOT/packaging/backend/dist"
rm -rf "$PROJECT_ROOT/apps/desktop/src-tauri/binaries"
deactivate 2>/dev/null || true

# Done
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║                    BUILD COMPLETE!                             ║"
echo "║                                                                ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║   Your installer is ready:                                     ║"
echo "║                                                                ║"
echo "║   📦  $DMG_PATH"
echo "║                                                                ║"
echo "║   To install:                                                  ║"
echo "║   1. Double-click the DMG file                                 ║"
echo "║   2. Drag PhotoSense-AI to Applications                        ║"
echo "║   3. Launch from Applications folder                           ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Open the folder containing the DMG
open "$OUTPUT_DIR"
