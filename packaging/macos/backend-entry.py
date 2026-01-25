#!/usr/bin/env python3
"""
Backend entry point for PhotoSense-AI macOS app
Handles environment setup and launches the FastAPI server
"""
import os
import sys
from pathlib import Path

# Determine if running from PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running from PyInstaller bundle
    BUNDLE_DIR = Path(sys._MEIPASS)
    BASE_DIR = BUNDLE_DIR
else:
    # Running from source
    BASE_DIR = Path(__file__).parent.parent.parent

# Set up environment
os.environ['PHOTOSENSE_DATA_DIR'] = str(Path.home() / 'Library' / 'Application Support' / 'PhotoSense-AI')
os.environ['TRANSFORMERS_CACHE'] = os.path.join(os.environ['PHOTOSENSE_DATA_DIR'], 'models', 'transformers')
os.environ['TORCH_HOME'] = os.path.join(os.environ['PHOTOSENSE_DATA_DIR'], 'models', 'torch')
os.environ['INSIGHTFACE_HOME'] = os.path.join(os.environ['PHOTOSENSE_DATA_DIR'], 'models', 'insightface')

# Create data directory
Path(os.environ['PHOTOSENSE_DATA_DIR']).mkdir(parents=True, exist_ok=True)

# Launch the FastAPI server
if __name__ == "__main__":
    import uvicorn
    
    # Import the app
    sys.path.insert(0, str(BASE_DIR))
    from services.api.main import app
    
    # Run server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
