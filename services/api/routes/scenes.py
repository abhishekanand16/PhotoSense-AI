"""Scene-related endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse, SceneResponse, SceneSummaryResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.get("/labels")
async def list_scene_labels():
    """Get all unique scene labels detected across all photos."""
    store = SQLiteStore()
    try:
        labels = store.get_all_scene_labels()
        return labels
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=List[SceneSummaryResponse])
async def list_scene_summary(
    prefix: Optional[str] = None,
    min_photo_count: int = 1,
    min_avg_confidence: float = 0.0,
):
    """Get scene labels with photo counts and average confidence. Auto-cleans orphaned scenes."""
    store = SQLiteStore()
    try:
        # Clean up orphaned scenes (where photo was deleted)
        orphaned_count = store.cleanup_orphaned_scenes()
        if orphaned_count > 0:
            import logging
            logging.info(f"Cleaned up {orphaned_count} orphaned scenes")
        
        summaries = store.get_scene_label_stats(prefix=prefix)
        filtered = [
            summary
            for summary in summaries
            if summary["photo_count"] >= min_photo_count
            and summary["avg_confidence"] >= min_avg_confidence
        ]
        return filtered
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/label/{label}/photos", response_model=List[PhotoResponse])
async def get_photos_by_scene(label: str):
    """Get all photos containing a specific scene."""
    store = SQLiteStore()
    try:
        photo_ids = store.get_photos_by_scene(label)
        photos = []
        for photo_id in photo_ids:
            photo = store.get_photo(photo_id)
            if photo:
                photo_dict = {
                    "id": photo["id"],
                    "file_path": photo["file_path"],
                    "date_taken": photo.get("date_taken"),
                    "camera_model": photo.get("camera_model"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "file_size": photo.get("file_size"),
                    "created_at": str(photo.get("created_at", "")) if photo.get("created_at") else "",
                }
                photos.append(photo_dict)
        return photos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photo/{photo_id}", response_model=List[SceneResponse])
async def get_scenes_for_photo(photo_id: int):
    """Get all scenes detected in a specific photo."""
    store = SQLiteStore()
    try:
        scenes = store.get_scenes_for_photo(photo_id)
        return scenes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
