#!/usr/bin/env python3
"""
PhotoSense-AI Backend Entry Point for Windows Installer.

This is the entry point when the backend is bundled with PyInstaller.
It starts the FastAPI server that powers the desktop application.

All file paths use pathlib.Path for proper Windows compatibility.
"""

import os
import sys
import platform
from pathlib import Path


def get_bundle_dir() -> Path:
    """Get the directory where the bundled app is located."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        # _MEIPASS is the temp directory where PyInstaller extracts files
        return Path(sys._MEIPASS)
    else:
        # Running as script (development)
        return Path(__file__).parent.parent.parent


def get_app_data_dir() -> Path:
    """
    Get Windows-specific application data directory.
    
    Uses %APPDATA% (Roaming) for user data that should sync across machines.
    Falls back to user home directory if APPDATA is not available.
    """
    system = platform.system()
    
    if system == "Windows":
        # Primary: Use APPDATA environment variable
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            # Fallback: Construct path manually
            base = Path.home() / "AppData" / "Roaming"
    elif system == "Darwin":  # macOS
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"
    
    app_dir = base / "PhotoSense-AI"
    
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        print(f"[WARNING] Could not create app data directory: {e}")
        # Fallback to user's home directory
        app_dir = Path.home() / ".photosense-ai"
        app_dir.mkdir(parents=True, exist_ok=True)
    
    return app_dir


def setup_environment():
    """Configure environment for bundled execution on Windows."""
    # Set app data directory
    app_data = get_app_data_dir()
    os.environ["PHOTOSENSE_DATA_DIR"] = str(app_data)
    
    # Configure threading for better CPU usage on Windows
    cpu_count = os.cpu_count() or 4
    default_threads = max(1, min(4, cpu_count // 2))
    
    thread_env_vars = [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS", 
        "OPENBLAS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMEXPR_NUM_THREADS"
    ]
    
    for key in thread_env_vars:
        if os.environ.get(key) is None:
            os.environ[key] = str(default_threads)
    
    # Disable tokenizers parallelism (can cause issues in bundled apps)
    if os.environ.get("TOKENIZERS_PARALLELISM") is None:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    
    # Disable TensorFlow warnings if TF is installed
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    
    # When running as PyInstaller bundle, configure paths
    if getattr(sys, 'frozen', False):
        bundle_dir = get_bundle_dir()
        
        # Add bundle directory to sys.path for imports
        bundle_str = str(bundle_dir)
        if bundle_str not in sys.path:
            sys.path.insert(0, bundle_str)
        
        # Set working directory to bundle dir (for relative paths)
        os.chdir(bundle_dir)
        
        # Log bundle info for debugging
        print(f"[Bundle] Running from: {bundle_dir}")
        print(f"[Bundle] App data: {app_data}")


def main():
    """Start the FastAPI backend server."""
    setup_environment()
    
    # Import after environment setup to ensure paths are correct
    import uvicorn
    from services.api.main import app
    
    # Get port from environment or use default
    port = int(os.environ.get("PHOTOSENSE_PORT", "8000"))
    host = os.environ.get("PHOTOSENSE_HOST", "127.0.0.1")
    
    print("=" * 60)
    print("  PhotoSense-AI Backend Starting")
    print("=" * 60)
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Data directory: {os.environ.get('PHOTOSENSE_DATA_DIR')}")
    print(f"  Platform: {platform.system()} {platform.release()}")
    if getattr(sys, 'frozen', False):
        print(f"  Bundle directory: {get_bundle_dir()}")
    print("=" * 60)
    
    try:
        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            reload=False,
            access_log=False,
        )
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        
        # On Windows, keep console open so user can see error
        if platform.system() == "Windows":
            input("\nPress Enter to exit...")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
