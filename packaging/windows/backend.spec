# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PhotoSense-AI Backend (Windows).

This creates a folder bundle containing:
- The Python interpreter
- All dependencies (FastAPI, PyTorch, transformers, etc.)
- The services/ code
- Required data files

Usage:
    pyinstaller backend.spec --noconfirm

Output:
    dist/photosense-backend/
        photosense-backend.exe
        _internal/  (Python + dependencies)
"""

import sys
from pathlib import Path

# Get paths - use forward slashes (Python handles Windows conversion)
SPEC_DIR = Path(SPECPATH)
PROJECT_ROOT = SPEC_DIR.parent.parent

block_cipher = None

# Collect all services code
services_path = PROJECT_ROOT / "services"

# Data files to include
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
    [str(SPEC_DIR / "backend-entry.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        # ==========================================
        # FastAPI and Web Framework
        # ==========================================
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
        
        # ==========================================
        # Database
        # ==========================================
        "sqlite3",
        
        # ==========================================
        # PyTorch and ML Core
        # ==========================================
        "torch",
        "torch.nn",
        "torch.nn.functional",
        "torch.utils",
        "torch.utils.data",
        "torchvision",
        "torchvision.transforms",
        "torchvision.transforms.functional",
        "torchvision.models",
        "torchvision.ops",
        
        # ==========================================
        # NumPy and Scientific Computing
        # ==========================================
        "numpy",
        "numpy.core",
        "numpy.core._multiarray_umath",
        
        # ==========================================
        # Image Processing
        # ==========================================
        "PIL",
        "PIL.Image",
        "PIL.ExifTags",
        "PIL.ImageOps",
        "cv2",
        
        # ==========================================
        # Scikit-learn (Clustering)
        # ==========================================
        "sklearn",
        "sklearn.cluster",
        "sklearn.cluster._dbscan",
        "sklearn.cluster._kmeans",
        "sklearn.metrics",
        "sklearn.metrics.pairwise",
        "sklearn.neighbors",
        "sklearn.preprocessing",
        "sklearn.utils",
        "sklearn.utils._cython_blas",
        "sklearn.utils._weight_vector",
        
        # ==========================================
        # FAISS (Vector Search)
        # ==========================================
        "faiss",
        "faiss.swigfaiss",
        
        # ==========================================
        # Transformers (CLIP, Florence)
        # ==========================================
        "transformers",
        "transformers.utils",
        "transformers.utils.hub",
        "transformers.models",
        "transformers.models.clip",
        "transformers.models.clip.modeling_clip",
        "transformers.models.clip.processing_clip",
        "transformers.models.clip.configuration_clip",
        "transformers.models.clip.tokenization_clip",
        "transformers.models.auto",
        "transformers.models.auto.modeling_auto",
        "transformers.models.auto.processing_auto",
        "transformers.models.auto.configuration_auto",
        "transformers.models.auto.tokenization_auto",
        "transformers.image_processing_utils",
        "transformers.feature_extraction_utils",
        "transformers.tokenization_utils",
        "transformers.tokenization_utils_base",
        "transformers.image_utils",
        "huggingface_hub",
        "huggingface_hub.utils",
        "huggingface_hub.file_download",
        "safetensors",
        "safetensors.torch",
        "accelerate",
        "timm",
        "timm.models",
        "timm.layers",
        "einops",
        
        # ==========================================
        # InsightFace (Face Detection)
        # ==========================================
        "insightface",
        "insightface.app",
        "insightface.app.face_analysis",
        "insightface.model_zoo",
        "insightface.model_zoo.model_zoo",
        "insightface.utils",
        
        # ==========================================
        # ONNX Runtime
        # ==========================================
        "onnxruntime",
        "onnx",
        "onnx.numpy_helper",
        
        # ==========================================
        # Ultralytics (YOLO)
        # ==========================================
        "ultralytics",
        "ultralytics.nn",
        "ultralytics.nn.tasks",
        "ultralytics.utils",
        "ultralytics.engine",
        "ultralytics.engine.results",
        "ultralytics.data",
        
        # ==========================================
        # Image Format Support
        # ==========================================
        "pillow_heif",
        "exifread",
        
        # ==========================================
        # Async HTTP (Geocoding)
        # ==========================================
        "aiohttp",
        "aiofiles",
        "multidict",
        "yarl",
        "async_timeout",
        "frozenlist",
        "aiosignal",
        
        # ==========================================
        # Utilities
        # ==========================================
        "tqdm",
        "tqdm.auto",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "idna",
        "packaging",
        "packaging.version",
        "filelock",
        "fsspec",
        "regex",
        "tokenizers",
        "sentencepiece",
        
        # ==========================================
        # Services Modules (PhotoSense-AI)
        # ==========================================
        "services",
        "services.api",
        "services.api.main",
        "services.api.models",
        "services.api.routes",
        "services.api.routes.faces",
        "services.api.routes.models",
        "services.api.routes.objects",
        "services.api.routes.people",
        "services.api.routes.pets",
        "services.api.routes.photos",
        "services.api.routes.places",
        "services.api.routes.scan",
        "services.api.routes.scenes",
        "services.api.routes.search",
        "services.api.routes.stats",
        "services.api.routes.tags",
        "services.config",
        "services.logging_config",
        "services.ml",
        "services.ml.pipeline",
        "services.ml.storage",
        "services.ml.storage.sqlite_store",
        "services.ml.storage.faiss_index",
        "services.ml.detectors",
        "services.ml.detectors.face_detector",
        "services.ml.detectors.object_detector",
        "services.ml.detectors.scene_detector",
        "services.ml.detectors.clip_scene_detector",
        "services.ml.detectors.florence_detector",
        "services.ml.embeddings",
        "services.ml.embeddings.face_embedding",
        "services.ml.embeddings.image_embedding",
        "services.ml.utils",
        "services.ml.utils.exif_utils",
        "services.ml.utils.geocoder",
        "services.ml.utils.image_cache",
        "services.ml.utils.model_tracker",
        "services.ml.utils.path_utils",
        "services.ml.utils.search_utils",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        "tkinter",
        "matplotlib",
        "matplotlib.pyplot",
        "notebook",
        "jupyter",
        "jupyter_client",
        "jupyter_core",
        "IPython",
        "ipykernel",
        "pytest",
        "sphinx",
        "docutils",
        "setuptools",
        "pip",
        "wheel",
        # Exclude TensorFlow (we use PyTorch)
        "tensorflow",
        "tensorboard",
        "keras",
        # Exclude unused ML frameworks
        "jax",
        "flax",
        "paddle",
        "paddlepaddle",
        # Exclude test modules
        "test",
        "tests",
        "_pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create the PYZ archive (compressed Python modules)
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
    console=False,  # Hide console window - Tauri manages this
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "apps" / "desktop" / "src-tauri" / "icons" / "icon.ico"),
)

# Create the distribution folder (folder mode, not onefile)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Don't compress these as it can cause issues
        "vcruntime140.dll",
        "python*.dll",
        "api-ms-win*.dll",
    ],
    name="photosense-backend",
)
