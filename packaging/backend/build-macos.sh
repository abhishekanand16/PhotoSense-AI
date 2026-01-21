#!/bin/bash
#
# Build PhotoSense-AI Backend for macOS
# Creates a standalone executable that can run without Python installed
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../dist/backend"

echo "============================================================"
echo "Building PhotoSense-AI Backend for macOS"
echo "============================================================"
echo "Project root: $PROJECT_ROOT"
echo "Output dir: $OUTPUT_DIR"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    echo "Install with: brew install python@3.10"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Using: $PYTHON_VERSION"

# Create/activate virtual environment for clean build
VENV_DIR="$SCRIPT_DIR/.build-venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating build virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller
pip install -r "$PROJECT_ROOT/requirements.txt"

# Clean previous build
echo ""
echo "Cleaning previous build..."
rm -rf "$SCRIPT_DIR/build"
rm -rf "$SCRIPT_DIR/dist"
rm -rf "$OUTPUT_DIR"

# Run PyInstaller
echo ""
echo "Running PyInstaller..."
cd "$SCRIPT_DIR"
pyinstaller photosense_backend.spec --noconfirm

# Move to output directory
echo ""
echo "Moving build artifacts..."
mkdir -p "$OUTPUT_DIR"
mv "$SCRIPT_DIR/dist/photosense-backend" "$OUTPUT_DIR/"

# Create version info
echo ""
echo "Creating version info..."
cat > "$OUTPUT_DIR/photosense-backend/version.txt" << EOF
PhotoSense-AI Backend
Version: 1.0.0
Build Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Platform: macOS
EOF

# Make executable
chmod +x "$OUTPUT_DIR/photosense-backend/photosense-backend"

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf "$SCRIPT_DIR/build"
rm -rf "$SCRIPT_DIR/dist"
deactivate

echo ""
echo "============================================================"
echo "Backend build complete!"
echo "Output: $OUTPUT_DIR/photosense-backend/"
echo "============================================================"
