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

# Collect data files
datas_list = [
    # Include the entire services directory
    (str(services_path), "services"),
    # Include requirements for reference
    (str(PROJECT_ROOT / "requirements.txt"), "."),
]

# Include Places365 labels if exists
places365_labels = services_path / "ml" / "detectors" / "places365_labels.txt"
if places365_labels.exists():
    datas_list.append((str(places365_labels), "services/ml/detectors"))

# Analysis phase - collect all imports and data
a = Analysis(
    [str(SPEC_DIR / "photosense_backend.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        # FastAPI and web framework
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "fastapi",
        "fastapi.responses",
        "fastapi.middleware",
        "fastapi.middleware.cors",
        "starlette",
        "starlette.responses",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.routing",
        "pydantic",
        "pydantic_core",
        "pydantic.deprecated",
        "pydantic.deprecated.decorator",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        
        # Database
        "sqlite3",
        
        # ML/AI libraries
        "torch",
        "torch.nn",
        "torch.nn.functional",
        "torchvision",
        "torchvision.transforms",
        "torchvision.models",
        "numpy",
        "PIL",
        "PIL.Image",
        "PIL.ExifTags",
        "cv2",
        "sklearn",
        "sklearn.cluster",
        "sklearn.cluster._dbscan",
        "sklearn.metrics",
        "sklearn.metrics.pairwise",
        "faiss",
        
        # Transformers (for CLIP, Florence)
        "transformers",
        "transformers.utils",
        "transformers.models",
        "transformers.models.clip",
        "transformers.models.clip.modeling_clip",
        "transformers.models.clip.processing_clip",
        "transformers.models.auto",
        "transformers.models.auto.modeling_auto",
        "transformers.models.auto.processing_auto",
        "transformers.image_processing_utils",
        "transformers.feature_extraction_utils",
        "huggingface_hub",
        "huggingface_hub.utils",
        "safetensors",
        "safetensors.torch",
        "accelerate",
        "timm",
        "timm.models",
        
        # InsightFace for face detection
        "insightface",
        "insightface.app",
        "insightface.model_zoo",
        "onnxruntime",
        "onnx",
        
        # Image processing
        "pillow_heif",
        "exifread",
        
        # Async HTTP for geocoding
        "aiohttp",
        "aiofiles",
        "multidict",
        "yarl",
        "async_timeout",
        "frozenlist",
        "aiosignal",
        
        # Utilities
        "tqdm",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        "packaging",
        "filelock",
        "fsspec",
        "regex",
        "tokenizers",
        
        # Services modules
        "services",
        "services.api",
        "services.api.main",
        "services.api.models",
        "services.api.routes",
        "services.ml",
        "services.ml.pipeline",
        "services.ml.storage",
        "services.ml.storage.sqlite_store",
        "services.ml.storage.faiss_index",
        "services.ml.detectors",
        "services.ml.embeddings",
        "services.ml.utils",
        "services.config",
        "services.logging_config",
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
        "pytest",
        "sphinx",
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
    console=False,  # Hide console window in production
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
