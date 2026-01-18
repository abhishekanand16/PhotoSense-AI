#!/usr/bin/env python3
"""
Helper script to run the PhotoSense-AI API server.
Can be run from any directory.
"""
import os
import sys
import subprocess
from pathlib import Path

# Get the project root directory (where this script is located)
PROJECT_ROOT = Path(__file__).parent.absolute()

# Add project root to Python path
sys.path.insert(0, str(PROJECT_ROOT))

# Change to project root directory
os.chdir(PROJECT_ROOT)

# Run uvicorn
if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(
            "services.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True
        )
    except ImportError:
        print("Error: uvicorn not found. Please install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
