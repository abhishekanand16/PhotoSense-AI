"""Object-related endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import ObjectResponse
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
