# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
"""
Model Status Tracker - Tracks ML model download and initialization status.

This singleton provides real-time visibility into model loading for first-time setup UX.
"""

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable
import logging
from pathlib import Path


class ModelStatus(str, Enum):
    """Status of a model."""
    PENDING = "pending"           # Not started
    CHECKING = "checking"         # Checking cache
    DOWNLOADING = "downloading"   # Actively downloading
    LOADING = "loading"           # Loading into memory
    READY = "ready"              # Fully loaded and ready
    ERROR = "error"              # Failed to load


@dataclass
class ModelInfo:
    """Information about a single model."""
    name: str
    display_name: str
    size_mb: int
    status: ModelStatus = ModelStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    error: Optional[str] = None
    downloaded_mb: float = 0.0


class ModelStatusTracker:
    """
    Singleton tracker for ML model download/load status.
    
    Thread-safe access to model status information.
    """
    
    _instance: Optional["ModelStatusTracker"] = None
    _lock = threading.Lock()
    
    # Model definitions with approximate sizes
    MODEL_DEFINITIONS = {
        "insightface": ModelInfo(
            name="insightface",
            display_name="Face Detection",
            size_mb=500,
        ),
        "yolo": ModelInfo(
            name="yolo",
            display_name="Object Detection",
            size_mb=6,
        ),
        "places365": ModelInfo(
            name="places365",
            display_name="Scene Recognition",
            size_mb=200,
        ),
        "clip": ModelInfo(
            name="clip",
            display_name="Visual Search",
            size_mb=890,
        ),
        "florence": ModelInfo(
            name="florence",
            display_name="Image Understanding",
            size_mb=990,
        ),
    }
    
    def __new__(cls) -> "ModelStatusTracker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._models: Dict[str, ModelInfo] = {}
        self._status_lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []
        
        # Initialize model info from definitions
        for name, template in self.MODEL_DEFINITIONS.items():
            self._models[name] = ModelInfo(
                name=template.name,
                display_name=template.display_name,
                size_mb=template.size_mb,
                status=ModelStatus.PENDING,
                progress=0.0,
            )
        
        self._initialized = True
    
    def update_status(
        self,
        model_name: str,
        status: ModelStatus,
        progress: float = 0.0,
        error: Optional[str] = None,
        downloaded_mb: float = 0.0,
    ) -> None:
        """Update the status of a model."""
        with self._status_lock:
            if model_name in self._models:
                model = self._models[model_name]
                model.status = status
                model.progress = progress
                model.error = error
                model.downloaded_mb = downloaded_mb
                
                logging.debug(f"Model {model_name}: {status.value} ({progress*100:.1f}%)")
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def set_checking(self, model_name: str) -> None:
        """Mark model as checking cache."""
        self.update_status(model_name, ModelStatus.CHECKING)
    
    def set_downloading(self, model_name: str, progress: float = 0.0, downloaded_mb: float = 0.0) -> None:
        """Mark model as downloading with progress."""
        self.update_status(model_name, ModelStatus.DOWNLOADING, progress, downloaded_mb=downloaded_mb)
    
    def set_loading(self, model_name: str) -> None:
        """Mark model as loading into memory."""
        self.update_status(model_name, ModelStatus.LOADING, progress=1.0)
    
    def set_ready(self, model_name: str) -> None:
        """Mark model as ready."""
        self.update_status(model_name, ModelStatus.READY, progress=1.0)
    
    def set_error(self, model_name: str, error: str) -> None:
        """Mark model as failed with error."""
        self.update_status(model_name, ModelStatus.ERROR, error=error)
    
    def get_model_status(self, model_name: str) -> Optional[ModelInfo]:
        """Get status of a specific model."""
        with self._status_lock:
            if model_name in self._models:
                model = self._models[model_name]
                # Return a copy to avoid race conditions
                return ModelInfo(
                    name=model.name,
                    display_name=model.display_name,
                    size_mb=model.size_mb,
                    status=model.status,
                    progress=model.progress,
                    error=model.error,
                    downloaded_mb=model.downloaded_mb,
                )
        return None
    
    def get_all_status(self) -> Dict[str, dict]:
        """Get status of all models as serializable dict."""
        with self._status_lock:
            result = {}
            for name, model in self._models.items():
                result[name] = {
                    "name": model.name,
                    "display_name": model.display_name,
                    "size_mb": model.size_mb,
                    "status": model.status.value,
                    "progress": model.progress,
                    "error": model.error,
                    "downloaded_mb": model.downloaded_mb,
                }
            return result
    
    def get_overall_progress(self) -> dict:
        """Get overall progress across all models."""
        with self._status_lock:
            total_size = sum(m.size_mb for m in self._models.values())
            completed_size = 0
            downloading_size = 0
            
            models_ready = 0
            models_downloading = 0
            models_pending = 0
            models_error = 0
            
            for model in self._models.values():
                if model.status == ModelStatus.READY:
                    completed_size += model.size_mb
                    models_ready += 1
                elif model.status == ModelStatus.DOWNLOADING:
                    downloading_size += model.downloaded_mb
                    models_downloading += 1
                elif model.status == ModelStatus.ERROR:
                    models_error += 1
                elif model.status in (ModelStatus.PENDING, ModelStatus.CHECKING):
                    models_pending += 1
                elif model.status == ModelStatus.LOADING:
                    completed_size += model.size_mb
                    models_ready += 1  # Count loading as ready for progress
            
            total_completed = completed_size + downloading_size
            overall_progress = total_completed / total_size if total_size > 0 else 1.0
            
            all_ready = models_ready == len(self._models)
            any_downloading = models_downloading > 0
            any_pending = models_pending > 0 or models_downloading > 0
            
            return {
                "overall_progress": overall_progress,
                "total_size_mb": total_size,
                "completed_size_mb": total_completed,
                "models_ready": models_ready,
                "models_downloading": models_downloading,
                "models_pending": models_pending,
                "models_error": models_error,
                "all_ready": all_ready,
                "any_downloading": any_downloading,
                "needs_setup": any_pending and not all_ready,
            }
    
    def is_all_ready(self) -> bool:
        """Check if all models are ready."""
        with self._status_lock:
            return all(m.status == ModelStatus.READY for m in self._models.values())
    
    def needs_setup(self) -> bool:
        """Check if any models need to be downloaded/loaded."""
        with self._status_lock:
            return any(
                m.status in (ModelStatus.PENDING, ModelStatus.CHECKING, ModelStatus.DOWNLOADING)
                for m in self._models.values()
            )
    
    def add_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback to be notified on status changes."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove a status change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def reset(self) -> None:
        """Reset all models to pending state."""
        with self._status_lock:
            for model in self._models.values():
                model.status = ModelStatus.PENDING
                model.progress = 0.0
                model.error = None
                model.downloaded_mb = 0.0


def get_model_tracker() -> ModelStatusTracker:
    """Get the global model status tracker singleton."""
    return ModelStatusTracker()


class HuggingFaceProgressCallback:
    """
    Progress callback for Hugging Face downloads.
    
    Usage:
        callback = HuggingFaceProgressCallback("clip")
        # Pass to huggingface_hub functions
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tracker = get_model_tracker()
        self._total_size = 0
        self._downloaded = 0
    
    def __call__(self, progress: float):
        """Called with progress from 0 to 1."""
        size_mb = self.tracker.MODEL_DEFINITIONS.get(self.model_name, ModelInfo("", "", 0)).size_mb
        downloaded_mb = progress * size_mb
        self.tracker.set_downloading(self.model_name, progress, downloaded_mb)
