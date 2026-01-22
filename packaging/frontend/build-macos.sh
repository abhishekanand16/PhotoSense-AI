#!/bin/bash
#
# Build PhotoSense-AI Frontend (Tauri) for macOS
# Creates the .app bundle with the backend sidecar
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGING_DIR/.." && pwd)"
DESKTOP_SRC="$PROJECT_ROOT/apps/desktop"
OUTPUT_DIR="$PACKAGING_DIR/dist/frontend"
BACKEND_DIR="$PACKAGING_DIR/dist/backend/photosense-backend"

echo "============================================================"
echo "Building PhotoSense-AI Frontend for macOS"
echo "============================================================"
echo "Project root: $PROJECT_ROOT"
echo "Desktop source: $DESKTOP_SRC"
echo "Output dir: $OUTPUT_DIR"
echo ""

# Check prerequisites
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is required but not installed."
    echo "Install with: brew install node"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo "ERROR: Rust is required but not installed."
    echo "Install from: https://rustup.rs"
    exit 1
fi

# Check if backend was built
if [ ! -f "$BACKEND_DIR/photosense-backend" ]; then
    echo "ERROR: Backend not found at $BACKEND_DIR"
    echo "Run ./backend/build-macos.sh first"
    exit 1
fi

echo "Using Node.js: $(node --version)"
echo "Using Rust: $(rustc --version)"

# Setup frontend build directory
echo ""
echo "Setting up build directory..."
BUILD_DIR="$SCRIPT_DIR/.build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy desktop source
cp -r "$DESKTOP_SRC"/* "$BUILD_DIR/"

# Copy our Tauri config
cp "$SCRIPT_DIR/tauri.conf.json" "$BUILD_DIR/src-tauri/"
cp "$SCRIPT_DIR/Cargo.toml" "$BUILD_DIR/src-tauri/"
cp "$SCRIPT_DIR/build.rs" "$BUILD_DIR/src-tauri/"
mkdir -p "$BUILD_DIR/src-tauri/src"
cp "$SCRIPT_DIR/src/main.rs" "$BUILD_DIR/src-tauri/src/"

# Copy backend bundle to resources
echo ""
echo "Copying backend resources..."
RESOURCES_DIR="$BUILD_DIR/src-tauri/resources/backend"
rm -rf "$RESOURCES_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy the entire PyInstaller output
cp -r "$BACKEND_DIR"/* "$RESOURCES_DIR/"
chmod +x "$RESOURCES_DIR/photosense-backend"

echo "Backend executable: $RESOURCES_DIR/photosense-backend"
echo "Dependencies in: $RESOURCES_DIR/"

# Install npm dependencies
echo ""
echo "Installing npm dependencies..."
cd "$BUILD_DIR"
npm install

# Build Tauri app
echo ""
echo "Building Tauri application..."
npm run tauri build

# Move output
echo ""
echo "Moving build artifacts..."
mkdir -p "$OUTPUT_DIR"

# Find and copy the .app bundle
APP_BUNDLE=$(find "$BUILD_DIR/src-tauri/target/release/bundle/macos" -name "*.app" -type d | head -1)
if [ -n "$APP_BUNDLE" ]; then
    cp -r "$APP_BUNDLE" "$OUTPUT_DIR/"
    echo "App bundle: $OUTPUT_DIR/$(basename "$APP_BUNDLE")"
fi

# Find and copy the .dmg if created
DMG_FILE=$(find "$BUILD_DIR/src-tauri/target/release/bundle/dmg" -name "*.dmg" -type f 2>/dev/null | head -1)
if [ -n "$DMG_FILE" ]; then
    cp "$DMG_FILE" "$OUTPUT_DIR/"
    echo "DMG installer: $OUTPUT_DIR/$(basename "$DMG_FILE")"
fi

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf "$BUILD_DIR"

echo ""
echo "============================================================"
echo "Frontend build complete!"
echo "Output: $OUTPUT_DIR/"
echo "============================================================"
