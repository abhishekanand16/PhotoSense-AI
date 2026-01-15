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
    """Background task to process a folder."""
    _jobs[job_id]["status"] = "processing"
    _jobs[job_id]["progress"] = 0.0
    _jobs[job_id]["message"] = "Scanning folder..."

    # Lazy import to avoid blocking server startup
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        # Find all images
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
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

        processed = 0
        for idx, image_path in enumerate(image_paths):
            try:
                await pipeline.process_photo(image_path)
                processed += 1
            except Exception as e:
                # Log error but continue
                logging.error(f"Failed to process {image_path}: {str(e)}")

            _jobs[job_id]["progress"] = (idx + 1) / total if total > 0 else 1.0
            _jobs[job_id]["message"] = f"Processed {idx + 1}/{total} images"

        # Run clustering
        _jobs[job_id]["message"] = "Organizing faces..."
        await pipeline.cluster_faces()

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["progress"] = 1.0
        _jobs[job_id]["message"] = f"Completed: {processed} photos processed"

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
    )
