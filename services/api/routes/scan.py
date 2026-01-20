"""Scanning and processing endpoints."""

import asyncio
import logging
import threading
import uuid
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from services.api.models import GlobalScanStatusResponse, JobStatusResponse, ScanRequest, ScanResponse
from services.ml.utils.path_utils import validate_folder_path as _validate_folder_path

router = APIRouter(prefix="/scan", tags=["scan"])

# In-memory job tracking (use Redis in production)
_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()

# Global scan state for progress tracking across all jobs
# This provides a single source of truth for the UI to poll
_global_scan_state: Dict = {
    "status": "idle",  # idle | scanning | indexing | done | paused
    "total_photos": 0,
    "scanned_photos": 0,
    "message": "Ready",
    "current_job_id": None,
    "error": None,
}
_global_state_lock = threading.Lock()


def _update_global_state(**kwargs) -> None:
    """Thread-safe global scan state update."""
    with _global_state_lock:
        _global_scan_state.update(kwargs)


def _get_global_state() -> Dict:
    """Thread-safe global scan state retrieval."""
    with _global_state_lock:
        return _global_scan_state.copy()


def _reset_global_state() -> None:
    """Reset global state to idle."""
    with _global_state_lock:
        _global_scan_state.update({
            "status": "idle",
            "total_photos": 0,
            "scanned_photos": 0,
            "message": "Ready",
            "current_job_id": None,
            "error": None,
        })


def _update_job(job_id: str, **kwargs) -> None:
    """Thread-safe job state update."""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _get_job(job_id: str) -> Dict:
    """Thread-safe job state retrieval."""
    with _jobs_lock:
        return _jobs.get(job_id, {}).copy()


def _create_job(job_id: str, initial_state: Dict) -> None:
    """Thread-safe job creation."""
    with _jobs_lock:
        _jobs[job_id] = initial_state.copy()


async def process_folder_async(folder_path: str, recursive: bool, job_id: str):
    """Background task to process a folder using two-phase approach.
    
    Phase 1: Import photos with metadata (fast) - allows immediate display in dashboard
    Phase 2: AI processing for faces and objects (slow) - runs after all imports complete
    """
    _update_job(job_id, status="processing", progress=0.0, message="Scanning folder...", phase="import")
    _update_global_state(
        status="scanning",
        total_photos=0,
        scanned_photos=0,
        message="Scanning folder...",
        current_job_id=job_id,
        error=None,
    )

    # Lazy import to avoid blocking server startup
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        # Validate folder path for safety
        try:
            folder = _validate_folder_path(folder_path)
        except ValueError as e:
            _update_job(job_id, status="error", message=str(e))
            _update_global_state(status="paused", message=str(e), error=str(e))
            return
        
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
        image_paths = []
        if recursive:
            image_paths = [str(p) for p in folder.rglob("*") if p.suffix.lower() in image_extensions]
        else:
            image_paths = [str(p) for p in folder.iterdir() if p.suffix.lower() in image_extensions]

        total = len(image_paths)
        _update_job(job_id, message=f"Found {total} images")
        _update_global_state(total_photos=total, message=f"Found {total} images")

        # Handle empty folder
        if total == 0:
            _update_job(job_id, status="completed", progress=1.0, message="No photos found to import")
            _update_global_state(status="idle", message="No photos to scan", scanned_photos=0)
            return

        # ============================================
        # PHASE 1: Import photos with metadata (fast)
        # Progress: 0% - 50%
        # ============================================
        _update_job(job_id, phase="import")
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
            progress = (idx + 1) / total * 0.5 if total > 0 else 0.5
            msg = f"Importing photos... {idx + 1}/{total}"
            _update_job(job_id, progress=progress, message=msg)
            _update_global_state(scanned_photos=idx + 1, message=msg)
            
            # Yield to event loop to allow status endpoint to respond
            await asyncio.sleep(0)

        # Mark Phase 1 complete - photos are now visible in dashboard
        msg = f"Import complete: {len(imported_photos)} photos ready. Starting AI analysis..."
        _update_job(job_id, message=msg, phase="scanning")
        _update_global_state(status="indexing", message=msg)

        # ============================================
        # PHASE 2: AI Processing (face/object detection)
        # Progress: 50% - 100%
        # ============================================
        processed = 0
        total_faces = 0
        total_objects = 0
        total_to_process = len(imported_photos)
        
        for idx, (photo_id, image_path) in enumerate(imported_photos):
            try:
                result = await pipeline.process_photo_ml(photo_id, image_path)
                processed += 1
                faces_found = len(result.get("faces", []))
                objects_found = len(result.get("objects", []))
                total_faces += faces_found
                total_objects += objects_found
                logging.info(f"Processed {image_path}: {faces_found} faces, {objects_found} objects")
            except Exception as e:
                logging.error(f"Failed to process ML for {image_path}: {str(e)}", exc_info=True)

            # Progress for Phase 2: 50% to 100%
            progress = 0.5 + (idx + 1) / total_to_process * 0.5 if total_to_process > 0 else 1.0
            msg = f"Analyzing photos... {idx + 1}/{total_to_process}"
            _update_job(job_id, progress=progress, message=msg)
            _update_global_state(scanned_photos=idx + 1, total_photos=total_to_process, message=msg)
            
            # Yield to event loop to allow status endpoint to respond
            await asyncio.sleep(0)

        # Run clustering (always cluster after bulk import)
        _update_job(job_id, message="Organizing faces...")
        _update_global_state(message="Organizing faces...")
        cluster_result = await pipeline.cluster_faces()
        
        # Build summary message
        clusters = cluster_result.get("clusters", 0)
        faces_clustered = cluster_result.get("faces_clustered", 0)
        final_msg = f"Completed: {len(imported_photos)} photos, {total_faces} faces, {clusters} people found"
        _update_job(
            job_id,
            status="completed",
            progress=1.0,
            phase="complete",
            message=final_msg
        )
        _update_global_state(
            status="done",
            scanned_photos=total_to_process,
            message=final_msg,
        )
        logging.info(f"Scan complete: {processed} photos, {total_faces} faces, {total_objects} objects, {clusters} clusters")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        _update_job(job_id, status="error", message=error_msg)
        _update_global_state(status="paused", message="Scan paused", error=error_msg)


@router.post("", response_model=ScanResponse)
async def scan_folder(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start scanning a folder."""
    job_id = str(uuid.uuid4())
    _create_job(job_id, {
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued",
    })

    background_tasks.add_task(process_folder_async, request.folder_path, request.recursive, job_id)

    return ScanResponse(
        job_id=job_id,
        status="queued",
        message="Scan started",
    )


@router.get("/status", response_model=GlobalScanStatusResponse)
async def get_global_scan_status():
    """Get global scan status for progress tracking.
    
    Returns the current state of any active scan, or idle status with library stats.
    This endpoint is polled by the frontend to show progress.
    """
    state = _get_global_state()
    
    # If idle or done, get library stats from database
    if state["status"] in ("idle", "done"):
        try:
            from services.ml.storage.sqlite_store import SQLiteStore
            store = SQLiteStore()
            stats = store.get_statistics()
            total_photos = stats.get("total_photos", 0)
            
            # Determine appropriate message
            if total_photos == 0:
                message = "No photos to scan"
            else:
                message = "Up to date"
            
            return GlobalScanStatusResponse(
                status="idle",
                total_photos=total_photos,
                scanned_photos=total_photos,
                progress_percent=100,
                message=message,
                current_job_id=None,
            )
        except Exception:
            # Fallback if database is unavailable
            return GlobalScanStatusResponse(
                status="idle",
                total_photos=0,
                scanned_photos=0,
                progress_percent=100,
                message="Ready",
                current_job_id=None,
            )
    
    # Active scan - return current progress
    total = state.get("total_photos", 0)
    scanned = state.get("scanned_photos", 0)
    progress_percent = int((scanned / total * 100) if total > 0 else 0)
    
    # If paused (error state), keep progress but show paused status
    if state["status"] == "paused":
        return GlobalScanStatusResponse(
            status="paused",
            total_photos=total,
            scanned_photos=scanned,
            progress_percent=progress_percent,
            message=state.get("message", "Scan paused"),
            current_job_id=state.get("current_job_id"),
        )
    
    return GlobalScanStatusResponse(
        status=state["status"],
        total_photos=total,
        scanned_photos=scanned,
        progress_percent=progress_percent,
        message=state.get("message", "Working..."),
        current_job_id=state.get("current_job_id"),
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a background job."""
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job.get("message"),
        phase=job.get("phase"),
    )


async def scan_faces_async(job_id: str):
    """Background task to scan faces for already-imported photos."""
    _update_job(job_id, status="processing", progress=0.0, message="Loading photos...", phase="scanning")
    _update_global_state(
        status="scanning",
        total_photos=0,
        scanned_photos=0,
        message="Loading photos...",
        current_job_id=job_id,
        error=None,
    )

    from services.ml.pipeline import MLPipeline
    from services.ml.storage.sqlite_store import SQLiteStore
    
    pipeline = MLPipeline()
    store = SQLiteStore()

    try:
        # Get all photos from database
        photos = store.get_all_photos()
        total = len(photos)
        
        if total == 0:
            _update_job(job_id, status="completed", progress=1.0, message="No photos found to scan")
            _update_global_state(status="idle", message="No photos to scan", scanned_photos=0)
            return

        _update_job(job_id, message=f"Found {total} photos to scan")
        _update_global_state(total_photos=total, message=f"Found {total} photos to scan")
        
        processed = 0
        total_faces = 0
        total_objects = 0
        for idx, photo in enumerate(photos):
            try:
                photo_id = photo["id"]
                photo_path = photo["file_path"]
                
                # Check if file exists
                if not Path(photo_path).exists():
                    logging.warning(f"Photo file not found: {photo_path}")
                    continue
                
                # Run face/object detection
                result = await pipeline.process_photo_ml(photo_id, photo_path)
                processed += 1
                faces_found = len(result.get("faces", []))
                objects_found = len(result.get("objects", []))
                total_faces += faces_found
                total_objects += objects_found
                logging.info(f"Processed {photo_path}: {faces_found} faces, {objects_found} objects")
            except Exception as e:
                logging.error(f"Failed to scan faces for photo {photo.get('id')}: {str(e)}", exc_info=True)

            progress = (idx + 1) / total if total > 0 else 1.0
            msg = f"Scanning faces... {idx + 1}/{total}"
            _update_job(job_id, progress=progress, message=msg)
            _update_global_state(scanned_photos=idx + 1, message=msg)
            
            # Yield to event loop to allow status endpoint to respond
            await asyncio.sleep(0)

        # Run clustering
        _update_job(job_id, message="Organizing faces...")
        _update_global_state(status="indexing", message="Organizing faces...")
        cluster_result = await pipeline.cluster_faces()

        clusters = cluster_result.get("clusters", 0)
        final_msg = f"Completed: {processed} photos scanned, {total_faces} faces, {clusters} people found"
        _update_job(
            job_id,
            status="completed",
            progress=1.0,
            phase="complete",
            message=final_msg
        )
        _update_global_state(
            status="done",
            scanned_photos=total,
            message=final_msg,
        )
        logging.info(f"Face scan complete: {processed} photos, {total_faces} faces, {total_objects} objects, {clusters} clusters")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        _update_job(job_id, status="error", message=error_msg)
        _update_global_state(status="paused", message="Scan paused", error=error_msg)


@router.post("/faces", response_model=ScanResponse)
async def scan_faces(background_tasks: BackgroundTasks):
    """Start face scanning for all already-imported photos."""
    job_id = str(uuid.uuid4())
    _create_job(job_id, {
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued",
        "phase": "scanning",
    })

    background_tasks.add_task(scan_faces_async, job_id)

    return ScanResponse(
        job_id=job_id,
        status="queued",
        message="Face scanning started",
    )

