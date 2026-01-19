"""Scanning and processing endpoints."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from services.api.models import JobStatusResponse, ScanRequest, ScanResponse

router = APIRouter(prefix="/scan", tags=["scan"])

# In-memory job tracking (use Redis in production)
_jobs: Dict[str, Dict] = {}


async def process_folder_async(folder_path: str, recursive: bool, job_id: str):
    """Background task to process a folder using two-phase approach.
    
    Phase 1: Import photos with metadata (fast) - allows immediate display in dashboard
    Phase 2: AI processing for faces and objects (slow) - runs after all imports complete
    """
    _jobs[job_id]["status"] = "processing"
    _jobs[job_id]["progress"] = 0.0
    _jobs[job_id]["message"] = "Scanning folder..."
    _jobs[job_id]["phase"] = "import"

    # Lazy import to avoid blocking server startup
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        # Find all images - comprehensive list of supported image formats
        # Supported by PIL/Pillow and OpenCV
        image_extensions = {
            # JPEG variants
            ".jpg", ".jpeg", ".jpe", ".jfif",
            # JPEG 2000
            ".jp2", ".j2k", ".jpc", ".jpx",
            # PNG
            ".png",
            # GIF
            ".gif",
            # BMP variants
            ".bmp", ".dib",
            # TIFF variants
            ".tiff", ".tif",
            # WebP
            ".webp",
            # HEIC/HEIF (modern Apple formats)
            ".heic", ".heif",
            # AVIF
            ".avif",
            # ICO
            ".ico",
            # PPM/PGM/PBM/PNM
            ".ppm", ".pgm", ".pbm", ".pnm",
            # XBM/XPM
            ".xbm", ".xpm",
            # PCX
            ".pcx",
            # TGA
            ".tga",
            # SGI
            ".sgi",
            # SPIDER
            ".spider",
            # DDS
            ".dds",
            # ICNS
            ".icns",
            # EPS
            ".eps", ".epi", ".epsf", ".epsi",
            # WMF
            ".wmf",
            # EXR
            ".exr",
            # HDR
            ".hdr",
            # Sun Raster
            ".sr", ".ras",
            # PIC
            ".pic",
        }
        folder = Path(folder_path)
        if not folder.exists():
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["message"] = "Folder does not exist"
            return

        image_paths = []
        if recursive:
            image_paths = [str(p) for p in folder.rglob("*") if p.suffix.lower() in image_extensions]
        else:
            image_paths = [str(p) for p in folder.iterdir() if p.suffix.lower() in image_extensions]

        total = len(image_paths)
        _jobs[job_id]["message"] = f"Found {total} images"

        # ============================================
        # PHASE 1: Import photos with metadata (fast)
        # Progress: 0% - 50%
        # ============================================
        _jobs[job_id]["phase"] = "import"
        imported_photos = []  # List of (photo_id, photo_path) tuples
        
        for idx, image_path in enumerate(image_paths):
            try:
                result = await pipeline.import_photo(image_path)
                if result.get("status") in ["imported", "exists"]:
                    photo_id = result.get("photo_id")
                    if photo_id:
                        imported_photos.append((photo_id, image_path))
            except Exception as e:
                logging.error(f"Failed to import {image_path}: {str(e)}")

            # Progress for Phase 1: 0% to 50%
            _jobs[job_id]["progress"] = (idx + 1) / total * 0.5 if total > 0 else 0.5
            _jobs[job_id]["message"] = f"Importing photos... {idx + 1}/{total}"

        # Mark Phase 1 complete - photos are now visible in dashboard
        _jobs[job_id]["message"] = f"Import complete: {len(imported_photos)} photos ready. Starting face scanning..."
        _jobs[job_id]["phase"] = "scanning"

        # ============================================
        # PHASE 2: AI Processing (face/object detection)
        # Progress: 50% - 100%
        # ============================================
        processed = 0
        total_to_process = len(imported_photos)
        
        for idx, (photo_id, image_path) in enumerate(imported_photos):
            try:
                await pipeline.process_photo_ml(photo_id, image_path)
                processed += 1
            except Exception as e:
                logging.error(f"Failed to process ML for {image_path}: {str(e)}")

            # Progress for Phase 2: 50% to 100%
            _jobs[job_id]["progress"] = 0.5 + (idx + 1) / total_to_process * 0.5 if total_to_process > 0 else 1.0
            _jobs[job_id]["message"] = f"Scanning faces... {idx + 1}/{total_to_process}"

        # Run clustering
        _jobs[job_id]["message"] = "Organizing faces..."
        await pipeline.cluster_faces()

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 1.0
        _jobs[job_id]["phase"] = "complete"
        _jobs[job_id]["message"] = f"Completed: {len(imported_photos)} photos imported, {processed} scanned"

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["message"] = f"Error: {str(e)}"


@router.post("", response_model=ScanResponse)
async def scan_folder(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start scanning a folder."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued",
    }

    background_tasks.add_task(process_folder_async, request.folder_path, request.recursive, job_id)

    return ScanResponse(
        job_id=job_id,
        status="queued",
        message="Scan started",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a background job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job.get("message"),
        phase=job.get("phase"),
    )


async def scan_faces_async(job_id: str):
    """Background task to scan faces for already-imported photos."""
    _jobs[job_id]["status"] = "processing"
    _jobs[job_id]["progress"] = 0.0
    _jobs[job_id]["message"] = "Loading photos..."
    _jobs[job_id]["phase"] = "scanning"

    from services.ml.pipeline import MLPipeline
    from services.ml.storage.sqlite_store import SQLiteStore
    
    pipeline = MLPipeline()
    store = SQLiteStore()

    try:
        # Get all photos from database
        photos = store.get_all_photos()
        total = len(photos)
        
        if total == 0:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["progress"] = 1.0
            _jobs[job_id]["message"] = "No photos found to scan"
            return

        _jobs[job_id]["message"] = f"Found {total} photos to scan"
        
        processed = 0
        for idx, photo in enumerate(photos):
            try:
                photo_id = photo["id"]
                photo_path = photo["file_path"]
                
                # Check if file exists
                from pathlib import Path
                if not Path(photo_path).exists():
                    logging.warning(f"Photo file not found: {photo_path}")
                    continue
                
                # Run face/object detection
                await pipeline.process_photo_ml(photo_id, photo_path)
                processed += 1
            except Exception as e:
                logging.error(f"Failed to scan faces for photo {photo.get('id')}: {str(e)}")

            _jobs[job_id]["progress"] = (idx + 1) / total if total > 0 else 1.0
            _jobs[job_id]["message"] = f"Scanning faces... {idx + 1}/{total}"

        # Run clustering
        _jobs[job_id]["message"] = "Organizing faces..."
        await pipeline.cluster_faces()

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 1.0
        _jobs[job_id]["phase"] = "complete"
        _jobs[job_id]["message"] = f"Completed: {processed} photos scanned"

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["message"] = f"Error: {str(e)}"


@router.post("/faces", response_model=ScanResponse)
async def scan_faces(background_tasks: BackgroundTasks):
    """Start face scanning for all already-imported photos."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued",
        "phase": "scanning",
    }

    background_tasks.add_task(scan_faces_async, job_id)

    return ScanResponse(
        job_id=job_id,
        status="queued",
        message="Face scanning started",
    )

