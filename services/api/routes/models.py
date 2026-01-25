"""
Models API - Endpoints for ML model status and initialization.

Provides real-time visibility into model download/load status for first-time setup UX.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from services.ml.utils.model_tracker import get_model_tracker, ModelStatus

router = APIRouter(prefix="/models", tags=["models"])

# Thread pool for model initialization
_init_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="model_init")


class ModelStatusResponse(BaseModel):
    """Status of a single model."""
    name: str
    display_name: str
    size_mb: int
    status: str
    progress: float
    error: Optional[str] = None
    downloaded_mb: float = 0.0


class ModelsOverallStatusResponse(BaseModel):
    """Overall status of all models."""
    overall_progress: float
    total_size_mb: int
    completed_size_mb: float
    models_ready: int
    models_downloading: int
    models_pending: int
    models_error: int
    all_ready: bool
    any_downloading: bool
    needs_setup: bool
    models: dict


@router.get("/status", response_model=ModelsOverallStatusResponse)
async def get_models_status():
    """
    Get status of all ML models.
    
    Returns overall progress and individual model statuses.
    Used by frontend to show first-time setup progress.
    
    NOTE: Automatically starts model initialization on first call if models aren't ready.
    """
    global _auto_init_started
    
    tracker = get_model_tracker()
    overall = tracker.get_overall_progress()
    models = tracker.get_all_status()
    
    return ModelsOverallStatusResponse(
        overall_progress=overall["overall_progress"],
        total_size_mb=overall["total_size_mb"],
        completed_size_mb=overall["completed_size_mb"],
        models_ready=overall["models_ready"],
        models_downloading=overall["models_downloading"],
        models_pending=overall["models_pending"],
        models_error=overall["models_error"],
        all_ready=overall["all_ready"],
        any_downloading=overall["any_downloading"],
        needs_setup=overall["needs_setup"],
        models=models,
    )


@router.get("/status/{model_name}", response_model=ModelStatusResponse)
async def get_model_status(model_name: str):
    """Get status of a specific model."""
    tracker = get_model_tracker()
    model = tracker.get_model_status(model_name)
    
    if model is None:
        return ModelStatusResponse(
            name=model_name,
            display_name="Unknown",
            size_mb=0,
            status="unknown",
            progress=0.0,
        )
    
    return ModelStatusResponse(
        name=model.name,
        display_name=model.display_name,
        size_mb=model.size_mb,
        status=model.status.value,
        progress=model.progress,
        error=model.error,
        downloaded_mb=model.downloaded_mb,
    )


def _initialize_models_sync():
    """
    Synchronously initialize all models.
    This triggers downloads and loads models into memory.
    Designed to run in a background thread.
    """
    import logging
    from services.ml.utils.model_tracker import get_model_tracker, ModelStatus
    
    tracker = get_model_tracker()
    
    # Import pipeline which triggers lazy loading
    try:
        from services.ml.pipeline import MLPipeline
        
        # Create pipeline instance - this will initialize essential models
        tracker.set_checking("insightface")
        tracker.set_checking("yolo")
        
        pipeline = MLPipeline()
        
        # Mark essential models as loading/ready
        tracker.set_loading("insightface")
        # Access face_detector to ensure it's loaded
        _ = pipeline.face_detector
        tracker.set_ready("insightface")
        
        tracker.set_loading("yolo")
        # Access object_detector to ensure it's loaded
        _ = pipeline.object_detector
        tracker.set_ready("yolo")
        
        # Load deferred models
        tracker.set_checking("places365")
        tracker.set_loading("places365")
        _ = pipeline.scene_detector
        tracker.set_ready("places365")
        
        tracker.set_checking("clip")
        tracker.set_loading("clip")
        _ = pipeline.image_embedder
        tracker.set_ready("clip")
        
        tracker.set_checking("florence")
        tracker.set_loading("florence")
        _ = pipeline.florence_detector
        tracker.set_ready("florence")
        
        logging.info("All models initialized successfully")
        
    except Exception as e:
        logging.error(f"Model initialization failed: {e}", exc_info=True)
        # Mark failed models
        tracker.set_error("unknown", str(e))


@router.post("/initialize")
async def initialize_models(background_tasks: BackgroundTasks):
    """
    Start initializing all models in the background.
    
    This triggers model downloads and loading.
    Poll /models/status to track progress.
    """
    loop = asyncio.get_event_loop()
    
    # Run initialization in thread pool
    background_tasks.add_task(
        lambda: loop.run_in_executor(_init_executor, _initialize_models_sync)
    )
    
    return {"status": "initializing", "message": "Model initialization started"}


@router.post("/check")
async def check_models():
    """
    Quick check of model cache status without loading.
    
    Returns which models are cached vs need downloading.
    """
    import os
    from pathlib import Path
    
    tracker = get_model_tracker()
    results = {}
    
    # Check HuggingFace cache
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    torch_cache = Path.home() / ".cache" / "torch" / "hub"
    
    # CLIP model check
    clip_cached = any(
        (hf_cache / d).exists() 
        for d in hf_cache.iterdir() 
        if d.is_dir() and "clip" in d.name.lower()
    ) if hf_cache.exists() else False
    
    # Florence model check  
    florence_cached = any(
        (hf_cache / d).exists()
        for d in hf_cache.iterdir()
        if d.is_dir() and "florence" in d.name.lower()
    ) if hf_cache.exists() else False
    
    # Places365 check
    places_cached = any(
        (torch_cache / d).exists()
        for d in torch_cache.iterdir()
        if d.is_dir() and "places365" in d.name.lower()
    ) if torch_cache.exists() else False
    
    results = {
        "clip": {"cached": clip_cached},
        "florence": {"cached": florence_cached},
        "places365": {"cached": places_cached},
        "insightface": {"cached": True},  # Usually bundled
        "yolo": {"cached": True},  # Small, usually cached
    }
    
    # Update tracker with cache status
    for model_name, info in results.items():
        if info["cached"]:
            tracker.set_checking(model_name)
        else:
            tracker.update_status(model_name, ModelStatus.PENDING)
    
    return {
        "models": results,
        "needs_download": not all(m["cached"] for m in results.values()),
    }
