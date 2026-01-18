"""Object-related endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import ObjectResponse, PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("/categories")
async def list_categories():
    """Get all object categories."""
    store = SQLiteStore()
    try:
        # Get unique categories
        photos = store.get_all_photos()
        categories = set()
        for photo in photos:
            objects = store.get_objects_for_photo(photo["id"])
            categories.update(obj["category"] for obj in objects)
        return sorted(list(categories))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}", response_model=List[ObjectResponse])
async def get_objects_by_category(category: str):
    """Get all objects of a specific category."""
    store = SQLiteStore()
    try:
        objects = store.get_objects_by_category(category)
        return objects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}/photos", response_model=List[PhotoResponse])
async def get_photos_by_category(category: str):
    """Get all photos containing objects of a specific category."""
    store = SQLiteStore()
    try:
        objects = store.get_objects_by_category(category)
        photo_ids = {obj["photo_id"] for obj in objects}
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
