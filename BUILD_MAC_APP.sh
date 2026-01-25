#!/bin/bash
# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
#
# ONE-CLICK MAC BUILD - Creates PhotoSense-AI.dmg
#

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              PhotoSense-AI Mac App Builder                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"

# Determine architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    TARGET="aarch64-apple-darwin"
else
    TARGET="x86_64-apple-darwin"
fi
echo "Building for: $TARGET"

# Check prerequisites
echo ""
echo "[1/7] Checking prerequisites..."

command -v python3 >/dev/null || { echo "ERROR: Python 3 required. brew install python"; exit 1; }
command -v node >/dev/null || { echo "ERROR: Node.js required. brew install node"; exit 1; }
command -v cargo >/dev/null || { echo "ERROR: Rust required. https://rustup.rs"; exit 1; }

echo "  ✓ Python: $(python3 --version)"
echo "  ✓ Node: $(node --version)"  
echo "  ✓ Rust: $(rustc --version)"

command -v create-dmg >/dev/null || { echo "  Installing create-dmg..."; brew install create-dmg; }
echo "  ✓ create-dmg"

# Step 2: Python environment
echo ""
echo "[2/7] Setting up Python environment..."

VENV_DIR="$PROJECT_ROOT/.build-venv"
[ ! -d "$VENV_DIR" ] && python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q
pip install pyinstaller -q
echo "  Installing dependencies (takes a few minutes first time)..."
pip install -r "$PROJECT_ROOT/requirements.txt" -q
echo "  ✓ Python ready"

# Step 3: Build backend
echo ""
echo "[3/7] Building Python backend..."

cd "$PROJECT_ROOT/packaging/backend"
rm -rf build dist
pyinstaller photosense_backend.spec --noconfirm 2>&1 | grep -E "(Building|ERROR)" | head -10

BACKEND_DIR="$PROJECT_ROOT/packaging/backend/dist/photosense-backend"
[ ! -f "$BACKEND_DIR/photosense-backend" ] && { echo "ERROR: Backend build failed"; exit 1; }
echo "  ✓ Backend built"

# Step 4: Setup Tauri binaries  
echo ""
echo "[4/7] Setting up Tauri sidecar..."

BINARIES_DIR="$PROJECT_ROOT/apps/desktop/src-tauri/binaries"
rm -rf "$BINARIES_DIR"
mkdir -p "$BINARIES_DIR"

# Copy the executable with target triple name
cp "$BACKEND_DIR/photosense-backend" "$BINARIES_DIR/photosense-backend-$TARGET"
chmod +x "$BINARIES_DIR/photosense-backend-$TARGET"

# Copy _internal folder (required for PyInstaller)
cp -R "$BACKEND_DIR/_internal" "$BINARIES_DIR/_internal"

echo "  ✓ Sidecar ready"

# Step 5: Build Tauri
echo ""
echo "[5/7] Building Tauri app..."

cd "$PROJECT_ROOT/apps/desktop"
npm install --silent 2>/dev/null
npm run tauri build 2>&1 | grep -E "(Compiling|Finished|Bundling|error\[)" | head -20

# Find the built app
APP_PATH=$(find "$PROJECT_ROOT/apps/desktop/src-tauri/target/release/bundle/macos" -name "*.app" -type d 2>/dev/null | head -1)
[ -z "$APP_PATH" ] && { echo "ERROR: Tauri build failed"; exit 1; }
echo "  ✓ App built: $(basename "$APP_PATH")"

# Step 6: Fix the app bundle - copy _internal to MacOS folder
echo ""
echo "[6/7] Fixing app bundle for PyInstaller..."

APP_MACOS="$APP_PATH/Contents/MacOS"
APP_RESOURCES="$APP_PATH/Contents/Resources"

# The _internal folder needs to be next to the executable in MacOS/
if [ -d "$APP_RESOURCES/_internal" ]; then
    mv "$APP_RESOURCES/_internal" "$APP_MACOS/_internal"
    echo "  ✓ Moved _internal to MacOS/"
elif [ -d "$APP_RESOURCES/binaries/_internal" ]; then
    mv "$APP_RESOURCES/binaries/_internal" "$APP_MACOS/_internal"
    echo "  ✓ Moved _internal from binaries/ to MacOS/"
fi

# Verify the backend can find its files
if [ -d "$APP_MACOS/_internal" ]; then
    echo "  ✓ _internal folder in correct location"
else
    echo "  WARNING: _internal folder not found, backend may not work"
fi

# Step 7: Create DMG
echo ""
echo "[7/7] Creating DMG..."

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
    "$APP_PATH" 2>/dev/null || hdiutil create -volname "PhotoSense-AI" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf "$PROJECT_ROOT/packaging/backend/build"
rm -rf "$PROJECT_ROOT/packaging/backend/dist"  
rm -rf "$BINARIES_DIR"
deactivate 2>/dev/null || true

DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    BUILD COMPLETE!                             ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  📦 dist/PhotoSense-AI.dmg ($DMG_SIZE)                         ║"
echo "║                                                                ║"
echo "║  Install: Drag to Applications                                 ║"
echo "║  If 'damaged' error: xattr -cr /Applications/PhotoSense-AI.app ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

open "$OUTPUT_DIR"
