#!/usr/bin/env python3
"""
PhotoSense-AI Backend Entry Point for Packaged Application.

This is the entry point when the backend is bundled with PyInstaller.
It starts the FastAPI server that powers the desktop application.
"""

import os
import sys
from pathlib import Path


def get_bundle_dir() -> Path:
    """Get the directory where the bundled app is located."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running as script (development)
        return Path(__file__).parent.parent


def get_app_data_dir() -> Path:
    """Get platform-specific application data directory."""
    import platform
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        # Use APPDATA with proper fallback
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:  # Linux
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"
    
    app_dir = base / "PhotoSense-AI"
    
    # Create directory with proper error handling
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to user's home directory if APPDATA is not writable
        app_dir = Path.home() / ".photosense-ai"
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
    
    # Disable tokenizers parallelism (can cause issues in bundled apps)
    if os.environ.get("TOKENIZERS_PARALLELISM") is None:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # When running as PyInstaller bundle, configure paths
    if getattr(sys, 'frozen', False):
        bundle_dir = get_bundle_dir()
        
        # Add bundle directory to sys.path for imports
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))
        
        # Set working directory to bundle dir (for relative paths)
        os.chdir(bundle_dir)
        
        # Log bundle info for debugging
        print(f"[Bundle] Running from: {bundle_dir}")
        print(f"[Bundle] sys.path[0]: {sys.path[0]}")


def main():
    """Start the FastAPI backend server."""
    setup_environment()
    
    # Import after environment setup
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
    if getattr(sys, 'frozen', False):
        print(f"Bundle directory: {get_bundle_dir()}")
    print(f"=" * 60)
    
    try:
        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            # Disable reload in production bundle
            reload=False,
            # Disable access log for cleaner output
            access_log=False,
        )
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
