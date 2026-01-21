import asyncio
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, Set

from fastapi import APIRouter, BackgroundTasks, HTTPException

from services.api.models import GlobalScanStatusResponse, JobStatusResponse, ScanRequest, ScanResponse
from services.config import SCAN_BATCH_SIZE, STATE_DIR
from services.ml.utils.path_utils import validate_folder_path as _validate_folder_path

router = APIRouter(prefix="/scan", tags=["scan"])

_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()

_global_scan_state: Dict = {
    "status": "idle",
    "total_photos": 0,
    "processed_photos": 0,
    "started_at": None,
    "eta_seconds": None,
    "progress_percent": 0,
    "message": "Ready",
    "current_job_id": None,
    "error": None,
}
_global_state_lock = threading.Lock()

_state_dir = STATE_DIR
_state_file = _state_dir / "scan_state.json"

def _load_scan_state() -> None:
    if not _state_file.exists():
        return
    try:
        payload = json.loads(_state_file.read_text())
    except Exception:
        return
    with _global_state_lock:
        for key in _global_scan_state.keys():
            if key in payload:
                _global_scan_state[key] = payload[key]

def _persist_scan_state() -> None:
    try:
        _state_dir.mkdir(parents=True, exist_ok=True)
        snapshot = _get_global_state()
        _state_file.write_text(json.dumps(snapshot))
    except Exception:
        return

_load_scan_state()


def _update_global_state(**kwargs) -> None:
    with _global_state_lock:
        _global_scan_state.update(kwargs)
    _persist_scan_state()


def _get_global_state() -> Dict:
    with _global_state_lock:
        return _global_scan_state.copy()


def _reset_global_state() -> None:
    with _global_state_lock:
        _global_scan_state.update({
            "status": "idle",
            "total_photos": 0,
            "processed_photos": 0,
            "started_at": None,
            "eta_seconds": None,
            "progress_percent": 0,
            "message": "Ready",
            "current_job_id": None,
            "error": None,
        })


def _update_job(job_id: str, **kwargs) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _get_job(job_id: str) -> Dict:
    with _jobs_lock:
        return _jobs.get(job_id, {}).copy()


def _create_job(job_id: str, initial_state: Dict) -> None:
    with _jobs_lock:
        _jobs[job_id] = initial_state.copy()


def _compute_eta_seconds(started_at: Optional[str], processed: int, total: int) -> Optional[int]:
    if not started_at or total <= 0 or processed <= 0:
        return None
    try:
        started = datetime.fromisoformat(started_at)
    except ValueError:
        return None
    elapsed = (datetime.now() - started).total_seconds()
    if elapsed <= 0:
        return None
    rate = processed / elapsed
    if rate <= 0:
        return None
    remaining = max(0, total - processed)
    return int(remaining / rate)


async def process_folder_async(folder_path: str, recursive: bool, job_id: str):
    _update_job(job_id, status="processing", progress=0.0, message="Scanning folder...", phase="import")
    _update_global_state(
        status="scanning",
        total_photos=0,
        processed_photos=0,
        started_at=datetime.now().isoformat(),
        eta_seconds=None,
        progress_percent=0,
        message="Scanning folder...",
        current_job_id=job_id,
        error=None,
    )

    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        try:
            folder = _validate_folder_path(folder_path)
        except ValueError as e:
            _update_job(job_id, status="error", message=str(e))
            _update_global_state(status="error", message=str(e), error=str(e))
            return

        image_extensions = {
            ".jpg", ".jpeg", ".jpe", ".jfif",
            ".jp2", ".j2k", ".jpc", ".jpx",
            ".png",
            ".gif",
            ".bmp", ".dib",
            ".tiff", ".tif",
            ".webp",
            ".heic", ".heif",
            ".avif",
            ".ico",
            ".ppm", ".pgm", ".pbm", ".pnm",
            ".xbm", ".xpm",
            ".pcx",
            ".tga",
            ".sgi",
            ".spider",
            ".dds",
            ".icns",
            ".eps", ".epi", ".epsf", ".epsi",
            ".wmf",
            ".exr",
            ".hdr",
            ".sr", ".ras",
            ".pic",
        }
        if recursive:
            image_paths = [str(p) for p in folder.rglob("*") if p.suffix.lower() in image_extensions]
        else:
            image_paths = [str(p) for p in folder.iterdir() if p.suffix.lower() in image_extensions]

        # Pass A: count images (streaming, no list allocation)
        total = 0
        for _ in _iter_image_paths(folder, recursive, image_extensions):
            total += 1
            if total % 5000 == 0:
                await asyncio.sleep(0)

        _update_job(job_id, message=f"Found {total} images")
        _update_global_state(total_photos=total, processed_photos=0, message=f"Found {total} images", progress_percent=0)

        if total == 0:
            _update_job(job_id, status="completed", progress=1.0, message="No photos found to import")
            _update_global_state(status="completed", message="No photos to scan", processed_photos=0, progress_percent=100, eta_seconds=0)
            return

        _update_job(job_id, phase="import")
        imported_photos = []
        
        for idx, image_path in enumerate(_iter_image_paths(folder, recursive, image_extensions)):
            try:
                result = await pipeline.import_photo(image_path)
                if result.get("status") in ["imported", "exists"]:
                    imported_count += 1
            except Exception as e:
                logging.error(f"Failed to import {image_path}: {str(e)}")

            progress = (idx + 1) / total * 0.5 if total > 0 else 0.5
            msg = f"Importing photos... {idx + 1}/{total}"
            eta_seconds = _compute_eta_seconds(_get_global_state().get("started_at"), idx + 1, total)
            _update_job(job_id, progress=progress, message=msg)
            _update_global_state(
                processed_photos=idx + 1,
                message=msg,
                progress_percent=int(progress * 100),
                eta_seconds=eta_seconds,
            )
            await asyncio.sleep(0)

        msg = f"Import complete: {len(imported_photos)} photos ready. Starting AI analysis..."
        _update_job(job_id, message=msg, phase="scanning")
        _update_global_state(status="indexing", processed_photos=0, message=msg, progress_percent=50, eta_seconds=None)

        processed = 0
        total_faces = 0
        total_objects = 0
        total_to_process = len(imported_photos)
        for batch_start in range(0, total_to_process, SCAN_BATCH_SIZE):
            batch_end = min(batch_start + SCAN_BATCH_SIZE, total_to_process)
            batch = imported_photos[batch_start:batch_end]
            
            for photo_id, image_path in batch:
                try:
                    result = await pipeline.process_photo_ml(photo_id, path)
                    processed += 1
                    faces_found = len(result.get("faces", []))
                    objects_found = len(result.get("objects", []))
                    total_faces += faces_found
                    total_objects += objects_found
                except Exception as e:
                    logging.error(f"Failed to process ML for {image_path}: {str(e)}", exc_info=True)
                
                # Update progress after each photo and yield to allow status endpoint to respond
                progress = 0.5 + (processed / total_to_process) * 0.5 if total_to_process > 0 else 1.0
                msg = f"Analyzing photos... {processed}/{total_to_process}"
                eta_seconds = _compute_eta_seconds(_get_global_state().get("started_at"), processed, total_to_process)
                _update_job(job_id, progress=progress, message=msg)
                _update_global_state(
                    processed_photos=processed,
                    total_photos=total_to_process,
                    message=msg,
                    progress_percent=int(progress * 100),
                    eta_seconds=eta_seconds,
                )
                await asyncio.sleep(0)

            pipeline.index.save_all_dirty()

        _update_job(job_id, message="Organizing faces...")
        _update_global_state(message="Organizing faces...")
        cluster_result = await pipeline.cluster_faces()
        
        clusters = cluster_result.get("clusters", 0)
        faces_clustered = cluster_result.get("faces_clustered", 0)
        final_msg = f"Completed: {processed} photos analyzed, {total_faces} faces, {clusters} people found"
        _update_job(
            job_id,
            status="completed",
            progress=1.0,
            phase="complete",
            message=final_msg
        )
        _update_global_state(
            status="completed",
            processed_photos=total_to_process,
            message=final_msg,
            progress_percent=100,
            eta_seconds=0,
        )
        logging.info(f"Scan complete: {processed} photos, {total_faces} faces, {total_objects} objects, {clusters} clusters")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        _update_job(job_id, status="error", message=error_msg)
        _update_global_state(status="error", message="Scan failed", error=error_msg)


@router.post("", response_model=ScanResponse)
async def scan_folder(request: ScanRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _update_global_state(
        status="scanning",
        total_photos=0,
        processed_photos=0,
        started_at=datetime.now().isoformat(),
        eta_seconds=None,
        progress_percent=0,
        message="Scan starting...",
        current_job_id=job_id,
        error=None,
    )
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
    state = _get_global_state()
    total = state.get("total_photos", 0)
    processed = state.get("processed_photos", 0)
    progress_percent = int(state.get("progress_percent") or 0)
    if progress_percent <= 0:
        progress_percent = int((processed / total * 100) if total > 0 else 0)

    return GlobalScanStatusResponse(
        status=state.get("status", "idle"),
        total_photos=total,
        processed_photos=processed,
        progress_percent=progress_percent,
        message=state.get("message", "Ready"),
        current_job_id=state.get("current_job_id"),
        started_at=state.get("started_at"),
        eta_seconds=state.get("eta_seconds"),
        error=state.get("error"),
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
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
    _update_job(job_id, status="processing", progress=0.0, message="Loading photos...", phase="scanning")
    _update_global_state(
        status="scanning",
        total_photos=0,
        processed_photos=0,
        started_at=datetime.now().isoformat(),
        eta_seconds=None,
        progress_percent=0,
        message="Loading photos...",
        current_job_id=job_id,
        error=None,
    )

    from services.ml.pipeline import MLPipeline
    from services.ml.storage.sqlite_store import SQLiteStore
    
    pipeline = MLPipeline()
    store = SQLiteStore()

    try:
        photos = store.get_all_photos()
        total = len(photos)
        
        if total == 0:
            _update_job(job_id, status="completed", progress=1.0, message="No photos found to scan")
            _update_global_state(status="completed", message="No photos to scan", processed_photos=0, progress_percent=100, eta_seconds=0)
            return

        _update_job(job_id, message=f"Found {total} photos to scan")
        _update_global_state(total_photos=total, processed_photos=0, message=f"Found {total} photos to scan", progress_percent=0)
        
        processed = 0
        total_faces = 0
        total_objects = 0
        for idx, photo in enumerate(photos):
            try:
                photo_id = photo["id"]
                photo_path = photo["file_path"]
                
                if not Path(photo_path).exists():
                    logging.warning(f"Photo file not found: {photo_path}")
                    continue
                
                result = await pipeline.process_photo_ml(photo_id, photo_path)
                processed += 1
                faces_found = len(result.get("faces", []))
                objects_found = len(result.get("objects", []))
                total_faces += faces_found
                total_objects += objects_found
            except Exception as e:
                logging.error(f"Failed to scan faces for photo {photo.get('id')}: {str(e)}", exc_info=True)

            progress = (idx + 1) / total if total > 0 else 1.0
            msg = f"Scanning faces... {idx + 1}/{total}"
            eta_seconds = _compute_eta_seconds(_get_global_state().get("started_at"), idx + 1, total)
            _update_job(job_id, progress=progress, message=msg)
            _update_global_state(processed_photos=idx + 1, message=msg, progress_percent=int(progress * 100), eta_seconds=eta_seconds)

        _update_job(job_id, message="Organizing faces...")
        _update_global_state(status="indexing", message="Organizing faces...", eta_seconds=None)
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
            status="completed",
            processed_photos=total,
            message=final_msg,
            progress_percent=100,
            eta_seconds=0,
        )
        logging.info(f"Face scan complete: {processed} photos, {total_faces} faces, {total_objects} objects, {clusters} clusters")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        _update_job(job_id, status="error", message=error_msg)
        _update_global_state(status="error", message="Scan failed", error=error_msg)


@router.post("/faces", response_model=ScanResponse)
async def scan_faces(background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _update_global_state(
        status="scanning",
        total_photos=0,
        processed_photos=0,
        started_at=datetime.now().isoformat(),
        eta_seconds=None,
        progress_percent=0,
        message="Scan starting...",
        current_job_id=job_id,
        error=None,
    )
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

