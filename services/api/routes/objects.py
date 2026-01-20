"""Object-related endpoints."""

import sqlite3
from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import CategorySummaryResponse, ObjectResponse, PhotoResponse
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


@router.get("/categories/summary", response_model=List[CategorySummaryResponse])
async def list_categories_summary():
    """Get object categories with photo counts (excluding 'person' and 'other'). Auto-cleans orphaned objects."""
    store = SQLiteStore()
    try:
        # Clean up orphaned objects (where photo was deleted)
        orphaned_count = store.cleanup_orphaned_objects()
        if orphaned_count > 0:
            import logging
            logging.info(f"Cleaned up {orphaned_count} orphaned objects")
        
        photos = store.get_all_photos()
        category_photos = {}
        for photo in photos:
            objects = store.get_objects_for_photo(photo["id"])
            for obj in objects:
                category = obj["category"]
                category_lower = category.lower()
                if "person" in category_lower:
                    continue
                if category_lower == "other":
                    continue
                category_photos.setdefault(category, set()).add(photo["id"])

        summaries = [
            {"category": category, "photo_count": len(photo_ids)}
            for category, photo_ids in category_photos.items()
            if photo_ids
        ]
        summaries.sort(key=lambda item: (-item["photo_count"], item["category"]))
        return summaries
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


@router.post("/cleanup-orphans")
async def cleanup_orphaned_objects():
    """
    Manually clean up orphaned objects that reference deleted photos.
    
    Returns:
        Count of deleted objects
    """
    try:
        store = SQLiteStore()
        deleted_count = store.cleanup_orphaned_objects()
        
        return {
            "status": "success",
            "deleted_objects": deleted_count,
            "message": f"Cleaned up {deleted_count} orphaned objects"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
