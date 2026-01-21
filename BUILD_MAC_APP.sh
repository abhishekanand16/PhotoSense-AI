#!/bin/bash
#
# ONE-CLICK MAC BUILD - Creates PhotoSense-AI.dmg
#

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║              PhotoSense-AI Mac App Builder                     ║"
echo "║                                                                ║"
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

# Step 2: Setup Python environment and build backend
echo ""
echo "[2/6] Setting up Python environment..."

VENV_DIR="$PROJECT_ROOT/.build-venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q
pip install pyinstaller -q
echo "  Installing Python dependencies (this takes a few minutes first time)..."
pip install -r "$PROJECT_ROOT/requirements.txt" -q

echo "  ✓ Python environment ready"

# Step 3: Build Python backend
echo ""
echo "[3/6] Building Python backend..."

cd "$PROJECT_ROOT/packaging/backend"
rm -rf build dist

pyinstaller photosense_backend.spec --noconfirm 2>&1 | grep -E "(Building|INFO|ERROR|WARNING)" | head -20

BACKEND_DIR="$PROJECT_ROOT/packaging/backend/dist/photosense-backend"
if [ ! -f "$BACKEND_DIR/photosense-backend" ]; then
    echo "ERROR: Backend build failed - executable not found"
    exit 1
fi
echo "  ✓ Backend built successfully"

# Step 4: Copy backend to Tauri binaries location
echo ""
echo "[4/6] Preparing Tauri sidecar..."

TAURI_DIR="$PROJECT_ROOT/apps/desktop/src-tauri"
BINARIES_DIR="$TAURI_DIR/binaries"

# Clean and create binaries directory
rm -rf "$BINARIES_DIR"
mkdir -p "$BINARIES_DIR"

# Tauri expects the sidecar at: binaries/name-target-triple
# For PyInstaller onedir bundles, we need ALL files from the bundle

# Copy entire PyInstaller output
cp -R "$BACKEND_DIR/"* "$BINARIES_DIR/"

# Rename the main executable with target triple
mv "$BINARIES_DIR/photosense-backend" "$BINARIES_DIR/photosense-backend-$TARGET"
chmod +x "$BINARIES_DIR/photosense-backend-$TARGET"

echo "  ✓ Sidecar prepared: photosense-backend-$TARGET"
echo "  Files in binaries/:"
ls "$BINARIES_DIR" | head -5
echo "  ... and $(ls "$BINARIES_DIR" | wc -l | tr -d ' ') total files"

# Step 5: Build Tauri app
echo ""
echo "[5/6] Building Tauri app (this takes 5-10 minutes)..."

cd "$PROJECT_ROOT/apps/desktop"
npm install --silent 2>/dev/null

# Build the Tauri app
npm run tauri build 2>&1 | grep -E "(Compiling|Finished|Bundling|Error|error)" | head -30

# Find the built app
APP_PATH=$(find "$TAURI_DIR/target/release/bundle/macos" -name "*.app" -type d 2>/dev/null | head -1)
if [ -z "$APP_PATH" ]; then
    echo "ERROR: Tauri build failed - no .app found"
    echo "Check the output above for errors"
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

# Try create-dmg first, fall back to hdiutil
if create-dmg \
    --volname "PhotoSense-AI" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "$(basename "$APP_PATH")" 150 190 \
    --hide-extension "$(basename "$APP_PATH")" \
    --app-drop-link 450 185 \
    --no-internet-enable \
    "$DMG_PATH" \
    "$APP_PATH" 2>/dev/null; then
    echo "  ✓ DMG created with create-dmg"
else
    echo "  Using hdiutil fallback..."
    hdiutil create -volname "PhotoSense-AI" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
    echo "  ✓ DMG created with hdiutil"
fi

# Cleanup build artifacts (keep the DMG)
echo ""
echo "Cleaning up build artifacts..."
rm -rf "$PROJECT_ROOT/packaging/backend/build"
rm -rf "$PROJECT_ROOT/packaging/backend/dist"
rm -rf "$BINARIES_DIR"
deactivate 2>/dev/null || true

# Get DMG size
DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║                    BUILD COMPLETE!                             ║"
echo "║                                                                ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║   📦 Output: dist/PhotoSense-AI.dmg ($DMG_SIZE)                ║"
echo "║                                                                ║"
echo "║   To install:                                                  ║"
echo "║   1. Double-click PhotoSense-AI.dmg                            ║"
echo "║   2. Drag PhotoSense-AI to Applications                        ║"
echo "║   3. Launch from Applications folder                           ║"
echo "║                                                                ║"
echo "║   First launch note:                                           ║"
echo "║   If macOS says 'damaged', run in Terminal:                    ║"
echo "║   xattr -cr /Applications/PhotoSense-AI.app                    ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Open the folder containing the DMG
open "$OUTPUT_DIR"
