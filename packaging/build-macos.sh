#!/bin/bash
#
# PhotoSense-AI Complete macOS Build Script
# 
# This script builds everything needed for a distributable macOS application:
# 1. Python backend (bundled with PyInstaller)
# 2. Tauri frontend (with backend as sidecar)
# 3. DMG installer for drag-and-drop installation
#
# Output: dist/PhotoSense-AI-1.0.0-macos.dmg
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="1.0.0"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           PhotoSense-AI macOS Build                          ║"
echo "║           Version: $VERSION                                     ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Create dist directory
DIST_DIR="$SCRIPT_DIR/dist"
mkdir -p "$DIST_DIR"

# Step 1: Build Backend
echo ""
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  Step 1/3: Building Python Backend                           │"
echo "└──────────────────────────────────────────────────────────────┘"
echo ""

chmod +x "$SCRIPT_DIR/backend/build-macos.sh"
"$SCRIPT_DIR/backend/build-macos.sh"

# Step 2: Build Frontend
echo ""
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  Step 2/3: Building Tauri Frontend                           │"
echo "└──────────────────────────────────────────────────────────────┘"
echo ""

chmod +x "$SCRIPT_DIR/frontend/build-macos.sh"
"$SCRIPT_DIR/frontend/build-macos.sh"

# Step 3: Create DMG (if create-dmg is available)
echo ""
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  Step 3/3: Creating DMG Installer                            │"
echo "└──────────────────────────────────────────────────────────────┘"
echo ""

APP_NAME="PhotoSense-AI"
APP_BUNDLE="$DIST_DIR/frontend/$APP_NAME.app"
DMG_OUTPUT="$DIST_DIR/$APP_NAME-$VERSION-macos.dmg"

if [ -d "$APP_BUNDLE" ]; then
    if command -v create-dmg &> /dev/null; then
        echo "Creating DMG with create-dmg..."
        
        # Remove existing DMG if present
        rm -f "$DMG_OUTPUT"
        
        create-dmg \
            --volname "$APP_NAME" \
            --volicon "$APP_BUNDLE/Contents/Resources/icon.icns" \
            --window-pos 200 120 \
            --window-size 600 400 \
            --icon-size 100 \
            --icon "$APP_NAME.app" 150 190 \
            --hide-extension "$APP_NAME.app" \
            --app-drop-link 450 185 \
            --no-internet-enable \
            "$DMG_OUTPUT" \
            "$APP_BUNDLE" \
            || echo "Warning: create-dmg failed, using hdiutil fallback"
        
        if [ ! -f "$DMG_OUTPUT" ]; then
            # Fallback to hdiutil
            echo "Using hdiutil fallback..."
            hdiutil create -volname "$APP_NAME" -srcfolder "$APP_BUNDLE" -ov -format UDZO "$DMG_OUTPUT"
        fi
    else
        echo "create-dmg not found, using hdiutil..."
        echo "For a prettier DMG, install create-dmg: brew install create-dmg"
        hdiutil create -volname "$APP_NAME" -srcfolder "$APP_BUNDLE" -ov -format UDZO "$DMG_OUTPUT"
    fi
    
    if [ -f "$DMG_OUTPUT" ]; then
        echo ""
        echo "DMG created: $DMG_OUTPUT"
        DMG_SIZE=$(du -h "$DMG_OUTPUT" | cut -f1)
        echo "Size: $DMG_SIZE"
    fi
else
    echo "Warning: App bundle not found at $APP_BUNDLE"
    echo "DMG creation skipped."
fi

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                     BUILD COMPLETE                           ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║                                                              ║"

if [ -f "$DMG_OUTPUT" ]; then
    echo "║  ✓ DMG Installer: dist/$(basename "$DMG_OUTPUT")"
fi

if [ -d "$APP_BUNDLE" ]; then
    echo "║  ✓ App Bundle: dist/frontend/$(basename "$APP_BUNDLE")"
fi

echo "║                                                              ║"
echo "║  To install:                                                 ║"
echo "║  1. Open the DMG file                                        ║"
echo "║  2. Drag PhotoSense-AI to Applications                       ║"
echo "║  3. Launch from Applications folder                          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
