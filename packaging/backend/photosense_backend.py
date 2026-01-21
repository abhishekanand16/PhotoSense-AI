#!/usr/bin/env python3
"""
PhotoSense-AI Backend Entry Point for Packaged Application.

This is the entry point when the backend is bundled with PyInstaller.
It starts the FastAPI server that powers the desktop application.
"""

import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """Get platform-specific application data directory."""
    import platform
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Linux
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    app_dir = base / "PhotoSense-AI"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def setup_environment():
    """Configure environment for bundled execution."""
    # Set app data directory
    app_data = get_app_data_dir()
    os.environ["PHOTOSENSE_DATA_DIR"] = str(app_data)
    
    # Configure threading for better CPU usage
    cpu_count = os.cpu_count() or 4
    default_threads = max(1, min(4, cpu_count // 2))
    
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", 
                "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(key) is None:
            os.environ[key] = str(default_threads)
    
    # Disable tokenizers parallelism (can cause issues)
    if os.environ.get("TOKENIZERS_PARALLELISM") is None:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # When running as PyInstaller bundle, add the bundle path to sys.path
    if getattr(sys, 'frozen', False):
        bundle_dir = Path(sys._MEIPASS)
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))


def main():
    """Start the FastAPI backend server."""
    setup_environment()
    
    import uvicorn
    from services.api.main import app
    
    # Get port from environment or use default
    port = int(os.environ.get("PHOTOSENSE_PORT", "8000"))
    host = os.environ.get("PHOTOSENSE_HOST", "127.0.0.1")
    
    print(f"=" * 60)
    print(f"PhotoSense-AI Backend Starting")
    print(f"=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Data directory: {os.environ.get('PHOTOSENSE_DATA_DIR')}")
    print(f"=" * 60)
    
    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        # Disable reload in production bundle
        reload=False,
    )


if __name__ == "__main__":
    main()
