#!/bin/bash
set -e

echo ""
echo "============================================================"
echo "PhotoSense-AI macOS Installer Build"
echo "============================================================"
echo ""

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DESKTOP_SRC="$PROJECT_ROOT/apps/desktop"
BUILD_DIR="$SCRIPT_DIR/.build"

echo "Project Root: $PROJECT_ROOT"
echo "Desktop Source: $DESKTOP_SRC"
echo ""

# ============================================================
# Step 1: Build Backend
# ============================================================
echo "============================================================"
echo "STEP 1: BUILD BACKEND"
echo "============================================================"
echo ""

cd "$SCRIPT_DIR"

# Create venv
echo "[1/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    rm -rf .venv
fi
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
echo "[2/5] Upgrading pip..."
pip install --upgrade pip setuptools wheel --quiet

# Install dependencies
echo "[3/5] Installing dependencies (10-30 minutes)..."
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
pip install pyinstaller --quiet

# Clean previous build
echo "[4/5] Cleaning previous build..."
rm -rf build dist

# Build with PyInstaller
echo "[5/5] Building with PyInstaller (5-15 minutes)..."
pyinstaller backend.spec --noconfirm --clean

if [ ! -f "dist/photosense-backend/photosense-backend" ]; then
    echo ""
    echo "ERROR: Backend build failed!"
    exit 1
fi

echo ""
echo "✅ Backend built: $SCRIPT_DIR/dist/photosense-backend/"
echo ""

# ============================================================
# Step 2: Prepare Frontend Build
# ============================================================
echo "============================================================"
echo "STEP 2: PREPARE FRONTEND BUILD"
echo "============================================================"
echo ""

# Create build directory
echo "[1/3] Setting up build directory..."
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR"

# Copy desktop source
cp -R "$DESKTOP_SRC/"* "$BUILD_DIR/"

# Copy macOS Tauri config
echo "[2/3] Applying macOS Tauri config..."
cp "$SCRIPT_DIR/tauri.conf.json" "$BUILD_DIR/src-tauri/"

# Copy backend bundle
echo "[3/3] Copying backend bundle..."
RESOURCES_DIR="$BUILD_DIR/src-tauri/resources/backend"
mkdir -p "$RESOURCES_DIR"

# Copy all files from backend dist
cp -R "$SCRIPT_DIR/dist/photosense-backend/"* "$RESOURCES_DIR/"

# Ensure executable has correct permissions
chmod +x "$RESOURCES_DIR/photosense-backend"

# Verify the executable exists
if [ ! -f "$RESOURCES_DIR/photosense-backend" ]; then
    echo "ERROR: Backend executable not found after copy!"
    exit 1
fi

echo "         Backend executable: $RESOURCES_DIR/photosense-backend"
ls -lh "$RESOURCES_DIR/photosense-backend"

echo ""
echo "✅ Frontend build directory ready"
echo ""

# ============================================================
# Step 3: Build Frontend
# ============================================================
echo "============================================================"
echo "STEP 3: BUILD TAURI FRONTEND"
echo "============================================================"
echo ""

cd "$BUILD_DIR"

# Install Rust targets
echo "[1/4] Installing Rust targets..."
rustup target add x86_64-apple-darwin 2>/dev/null || true
rustup target add aarch64-apple-darwin 2>/dev/null || true

# Install npm dependencies
echo "[2/4] Installing npm dependencies..."
npm install --silent

# Build Tauri app
echo "[3/4] Building Tauri app (10-20 minutes)..."
echo "         This creates a universal binary for Intel + Apple Silicon"
echo ""
npm run tauri build -- --target universal-apple-darwin

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Tauri build failed!"
    exit 1
fi

# Move DMG to dist
echo "[4/4] Moving installer..."
mkdir -p "$SCRIPT_DIR/dist"
DMG_FILE=$(find "$BUILD_DIR/src-tauri/target/universal-apple-darwin/release/bundle/dmg" -name "*.dmg" | head -n 1)

if [ -z "$DMG_FILE" ]; then
    echo ""
    echo "ERROR: DMG file not found!"
    exit 1
fi

cp "$DMG_FILE" "$SCRIPT_DIR/dist/PhotoSense-AI.dmg"

echo ""
echo "============================================================"
echo "BUILD COMPLETE!"
echo "============================================================"
echo ""
echo "Installer: $SCRIPT_DIR/dist/PhotoSense-AI.dmg"
echo ""
echo "This DMG contains:"
echo "  ✅ Universal binary (Intel + Apple Silicon)"
echo "  ✅ Python backend bundled inside"
echo "  ✅ All ML models and dependencies"
echo ""
echo "Users can drag PhotoSense-AI.app to Applications folder"
echo ""