# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

# Get project root
project_root = Path(os.getcwd()).parent.parent

block_cipher = None

a = Analysis(
    [str(project_root / 'packaging' / 'macos' / 'backend-entry.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'services'), 'services'),
        (str(project_root / 'requirements.txt'), '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pydantic',
        'pydantic.fields',
        'pydantic_core',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'torch',
        'torchvision',
        'transformers',
        'transformers.models',
        'transformers.models.auto',
        'insightface',
        'insightface.app',
        'insightface.model_zoo',
        'onnxruntime',
        'onnx',
        'cv2',
        'PIL',
        'numpy',
        'sklearn',
        'sklearn.cluster',
        'faiss',
        'ultralytics',
        'ultralytics.nn',
        'ultralytics.models',
        'aiohttp',
        'multipart',
        'python_multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'tkinter',
        'PyQt5',
        'PySide2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='photosense-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='photosense-backend',
)
