"""Object-related endpoints."""

import sqlite3
from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import ObjectResponse, PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/objects", tags=["objects"])


@router.get("/categories")
async def list_categories():
    """Get all object categories (excluding 'person' and 'other')."""
    store = SQLiteStore()
    try:
        # Get unique categories, excluding 'person' (handled in People tab) and 'other' (too generic)
        photos = store.get_all_photos()
        categories = set()
        for photo in photos:
            objects = store.get_objects_for_photo(photo["id"])
            for obj in objects:
                category = obj["category"]
                # Exclude person-related categories (handles both "person" and "person:person" formats)
                if "person" in category.lower():
                    continue
                # Exclude 'other' as too generic
                if category.lower() == "other":
                    continue
                categories.add(category)
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
    # Block access to excluded categories (handles both "person" and "person:person" formats)
    if "person" in category.lower() or category.lower() == "other":
        return []
    
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


@router.post("/cleanup-person-objects")
async def cleanup_person_objects(dry_run: bool = False):
    """Remove all 'person' objects from the database.
    
    Since we have a dedicated face detection system for people,
    we don't need person objects in the objects table.
    
    Args:
        dry_run: If True, only reports what would be removed without making changes
        
    Returns:
        Statistics about the cleanup operation
    """
    store = SQLiteStore()
    
    try:
        conn = sqlite3.connect(store.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find all person objects
        cursor.execute("""
            SELECT id, photo_id, category, confidence 
            FROM objects 
            WHERE category LIKE '%person%'
        """)
        
        person_objects = cursor.fetchall()
        object_count = len(person_objects)
        
        # Count affected photos
        cursor.execute("""
            SELECT COUNT(DISTINCT photo_id) 
            FROM objects 
            WHERE category LIKE '%person%'
        """)
        affected_photos = cursor.fetchone()[0]
        
        if not dry_run and object_count > 0:
            # Remove person objects
            cursor.execute("DELETE FROM objects WHERE category LIKE '%person%'")
            conn.commit()
        
        conn.close()
        
        return {
            "status": "success",
            "person_objects_found": object_count,
            "person_objects_removed": object_count if not dry_run else 0,
            "affected_photos": affected_photos,
            "dry_run": dry_run,
            "message": f"{'Would remove' if dry_run else 'Removed'} {object_count} person objects from {affected_photos} photos"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
