#!/bin/bash
set -e

echo "Building PhotoSense-AI for macOS..."
echo ""

# Get directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DESKTOP_SRC="$PROJECT_ROOT/apps/desktop"

# Build backend
echo "[1/3] Building Python backend..."
cd "$SCRIPT_DIR"

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel --quiet
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
pip install pyinstaller --quiet

# Build with PyInstaller
pyinstaller --noconfirm --clean \
  --name photosense-backend \
  --onedir \
  --console \
  --add-data "$PROJECT_ROOT/services:services" \
  --add-data "$PROJECT_ROOT/requirements.txt:." \
  --hidden-import uvicorn \
  --hidden-import fastapi \
  --hidden-import pydantic \
  --hidden-import torch \
  --hidden-import torchvision \
  --hidden-import transformers \
  --hidden-import insightface \
  --hidden-import onnxruntime \
  --hidden-import ultralytics \
  --hidden-import faiss \
  --collect-all torch \
  --collect-all torchvision \
  --collect-all transformers \
  --collect-all insightface \
  "$PROJECT_ROOT/services/api/main.py"

echo "Backend built: $SCRIPT_DIR/dist/photosense-backend/"

# Build frontend
echo ""
echo "[2/3] Building Tauri frontend..."
cd "$DESKTOP_SRC"

# Install npm dependencies
npm install --silent

# Build Tauri app
npm run tauri build -- --target universal-apple-darwin

echo "Frontend built: $DESKTOP_SRC/src-tauri/target/release/bundle/dmg/"

# Copy DMG to dist
echo ""
echo "[3/3] Copying installer..."
mkdir -p "$SCRIPT_DIR/dist"
cp "$DESKTOP_SRC/src-tauri/target/release/bundle/dmg/"*.dmg "$SCRIPT_DIR/dist/PhotoSense-AI.dmg"

echo ""
echo "✅ Build complete!"
echo "Installer: $SCRIPT_DIR/dist/PhotoSense-AI.dmg"
