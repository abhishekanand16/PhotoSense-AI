"""FastAPI application entry point."""

import os
from PIL import Image

# Configure PIL to support large images (up to 250MP)
# Default limit is ~89MP, which triggers DecompressionBombWarning
Image.MAX_IMAGE_PIXELS = 250_000_000  # 250 megapixels

def _set_default_env(key: str, value: str) -> None:
    """Set an env var only if the user hasn't set it."""
    if os.environ.get(key) is None:
        os.environ[key] = value

# ---------------------------------------------------------------------------
# CPU / threading defaults (lower CPU spikes & keep UI responsive)
# ---------------------------------------------------------------------------
# NOTE: These are safe defaults; users can override by setting env vars.
_cpu_count = os.cpu_count() or 4
_default_threads = max(1, min(4, _cpu_count // 2))

for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _set_default_env(_k, str(_default_threads))

# HuggingFace tokenizers sometimes parallelize aggressively
_set_default_env("TOKENIZERS_PARALLELISM", "false")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.routes import faces, models, objects, people, pets, photos, places, scan, scenes, search, stats, tags

app = FastAPI(
    title="PhotoSense-AI API",
    description="Local API service for PhotoSense-AI desktop application",
    version="1.0.0",
)

# CORS middleware for desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(photos.router)
app.include_router(people.router)
app.include_router(pets.router)
app.include_router(faces.router)
app.include_router(places.router)
app.include_router(scan.router)
app.include_router(search.router)
app.include_router(objects.router)
app.include_router(scenes.router)
app.include_router(stats.router)
app.include_router(tags.router)
app.include_router(models.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PhotoSense-AI API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
