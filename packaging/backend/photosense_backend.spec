# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PhotoSense-AI Backend.

This creates a single-folder bundle containing:
- The Python interpreter
- All dependencies (FastAPI, PyTorch, transformers, etc.)
- The services/ code
- Required data files

Usage:
    pyinstaller photosense_backend.spec
"""

import sys
from pathlib import Path

# Get the project root (two levels up from this spec file)
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent.parent

block_cipher = None

# Collect all services code
services_path = PROJECT_ROOT / "services"

# Analysis phase - collect all imports and data
a = Analysis(
    [str(SPEC_DIR / "photosense_backend.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Include the entire services directory
        (str(services_path), "services"),
        # Include requirements for reference
        (str(PROJECT_ROOT / "requirements.txt"), "."),
    ],
    hiddenimports=[
        # FastAPI and web framework
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "pydantic",
        "pydantic_core",
        
        # Database
        "sqlite3",
        
        # ML/AI libraries
        "torch",
        "torchvision",
        "numpy",
        "PIL",
        "PIL.Image",
        "cv2",
        "sklearn",
        "sklearn.cluster",
        "faiss",
        
        # Transformers (for CLIP, Florence)
        "transformers",
        "transformers.models",
        "transformers.models.clip",
        "transformers.models.auto",
        "huggingface_hub",
        
        # InsightFace for face detection
        "insightface",
        "onnxruntime",
        
        # Image processing
        "pillow_heif",
        "exifread",
        
        # Async HTTP for geocoding
        "aiohttp",
        "aiofiles",
        
        # Utilities
        "tqdm",
        "requests",
        "packaging",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "matplotlib",
        "notebook",
        "jupyter",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create the PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="photosense-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Show console for debugging; set False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Create the distribution folder
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="photosense-backend",
)
