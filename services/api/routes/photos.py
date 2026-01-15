"""Photo-related endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("", response_model=List[PhotoResponse])
async def list_photos():
    """Get all photos."""
    store = SQLiteStore()
    try:
        photos = store.get_all_photos()
        # Convert to PhotoResponse format, ensuring all fields are properly formatted
        result = []
        for photo in photos:
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
            result.append(photo_dict)
        return result
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(photo_id: int):
    """Get a specific photo."""
    store = SQLiteStore()
    try:
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        # Ensure created_at is a string
        if photo.get("created_at") and not isinstance(photo["created_at"], str):
            photo["created_at"] = str(photo["created_at"])
        elif not photo.get("created_at"):
            photo["created_at"] = ""
        return photo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
