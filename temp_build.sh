#!/bin/bash
set -e

cd /Users/abhishek/Documents/GitHub/PhotoSense-AI/apps/desktop

echo "Installing npm dependencies..."
npm install

echo "Building Tauri application..."
npm run tauri build

echo "Build complete!"
