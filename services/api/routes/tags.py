"""
Custom user tags endpoints.

Provides endpoints for managing user-created custom tags on photos:
- Add/remove tags from photos
- List tags for a photo
- List all tags with counts (for Objects > Custom section)
- Get photos by tag
"""

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.api.models import PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/tags", tags=["tags"])


class TagRequest(BaseModel):
    """Request to add a tag."""
    tag: str


class TagsRequest(BaseModel):
    """Request to add multiple tags."""
    tags: List[str]


class TagSummary(BaseModel):
    """Tag with photo count."""
    tag: str
    photo_count: int


@router.get("", response_model=List[TagSummary])
async def list_all_tags():
    """
    Get all custom tags with photo counts.
    Used for Objects > Custom section in the UI.
    """
    store = SQLiteStore()
    try:
        tags = store.get_all_tags_with_counts()
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tag}/photos", response_model=List[PhotoResponse])
async def get_photos_by_tag(tag: str):
    """Get all photos with a specific tag."""
    store = SQLiteStore()
    try:
        photos = store.get_photos_by_tag(tag)
        return [
            {
                "id": p["id"],
                "file_path": p["file_path"],
                "date_taken": p.get("date_taken"),
                "camera_model": p.get("camera_model"),
                "width": p.get("width"),
                "height": p.get("height"),
                "file_size": p.get("file_size"),
                "created_at": str(p.get("created_at", "")) if p.get("created_at") else "",
            }
            for p in photos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photo/{photo_id}", response_model=List[str])
async def get_photo_tags(photo_id: int):
    """Get all tags for a specific photo."""
    store = SQLiteStore()
    try:
        # Verify photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        tags = store.get_tags_for_photo(photo_id)
        return tags
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/photo/{photo_id}")
async def add_tag_to_photo(photo_id: int, request: TagRequest):
    """Add a single tag to a photo."""
    store = SQLiteStore()
    try:
        # Verify photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        if not request.tag or not request.tag.strip():
            raise HTTPException(status_code=400, detail="Tag cannot be empty")
        
        tag_id = store.add_tag(photo_id, request.tag)
        return {"status": "success", "tag_id": tag_id, "tag": request.tag.lower().strip()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/photo/{photo_id}/multiple")
async def add_tags_to_photo(photo_id: int, request: TagsRequest):
    """Add multiple tags to a photo at once."""
    store = SQLiteStore()
    try:
        # Verify photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        added_tags = []
        for tag in request.tags:
            if tag and tag.strip():
                store.add_tag(photo_id, tag)
                added_tags.append(tag.lower().strip())
        
        return {"status": "success", "added_tags": added_tags}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/photo/{photo_id}/{tag}")
async def remove_tag_from_photo(photo_id: int, tag: str):
    """Remove a tag from a photo."""
    store = SQLiteStore()
    try:
        # Verify photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        deleted = store.remove_tag(photo_id, tag)
        if not deleted:
            raise HTTPException(status_code=404, detail="Tag not found on this photo")
        
        return {"status": "success", "message": f"Tag '{tag}' removed from photo"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/photo/{photo_id}")
async def remove_all_tags_from_photo(photo_id: int):
    """Remove all tags from a photo."""
    store = SQLiteStore()
    try:
        # Verify photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        deleted_count = store.delete_tags_for_photo(photo_id)
        return {"status": "success", "deleted_count": deleted_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
