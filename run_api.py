#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()

sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

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
