"""People/cluster-related endpoints."""

import io
from pathlib import Path
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.api.models import MergePeopleRequest, PersonResponse, PhotoResponse, UpdatePersonRequest
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=List[PersonResponse])
async def list_people():
    """Get all people."""
    store = SQLiteStore()
    try:
        people = store.get_all_people()
        # Add face counts
        result = []
        for person in people:
            faces = store.get_faces_for_person(person["id"])
            result.append(
                PersonResponse(
                    id=person["id"],
                    cluster_id=person.get("cluster_id"),
                    name=person.get("name"),
                    face_count=len(faces),
                )
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(person_id: int, request: UpdatePersonRequest):
    """Update person name."""
    store = SQLiteStore()
    try:
        store.update_person_name(person_id, request.name)
        person = next((p for p in store.get_all_people() if p["id"] == person_id), None)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        faces = store.get_faces_for_person(person_id)
        return PersonResponse(
            id=person["id"],
            cluster_id=person.get("cluster_id"),
            name=person.get("name"),
            face_count=len(faces),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/photos", response_model=List[PhotoResponse])
async def get_photos_for_person(person_id: int):
    """Get all photos for a specific person."""
    store = SQLiteStore()
    try:
        faces = store.get_faces_for_person(person_id)
        photo_ids = {face["photo_id"] for face in faces}
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


@router.post("/merge")
async def merge_people(request: MergePeopleRequest):
    """Merge two people."""
    store = SQLiteStore()
    try:
        if request.source_person_id == request.target_person_id:
            raise HTTPException(status_code=400, detail="Cannot merge person with itself")
        store.merge_people(request.source_person_id, request.target_person_id)
        return {"status": "success", "message": "People merged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{person_id}")
async def delete_person(person_id: int):
    """Delete a person and unassign all their faces."""
    store = SQLiteStore()
    try:
        deleted = store.delete_person(person_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Person not found")
        return {"status": "success", "message": "Person deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/faces")
async def get_faces_for_person(person_id: int):
    """Get all faces for a specific person."""
    store = SQLiteStore()
    try:
        faces = store.get_faces_for_person(person_id)
        return faces
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{person_id}/recluster")
async def recluster_person(person_id: int):
    """Re-cluster faces for a specific person (split if needed)."""
    from services.ml.pipeline import MLPipeline
    
    try:
        pipeline = MLPipeline()
        result = await pipeline.recluster_person_faces(person_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{person_id}/thumbnail")
async def get_person_thumbnail(person_id: int, size: int = 200):
    """Get a cropped face thumbnail for a person.
    
    Returns the highest-confidence face crop for this person as a JPEG image.
    The crop is square and centered on the face with some padding.
    """
    store = SQLiteStore()
    try:
        # Get all faces for this person
        faces = store.get_faces_for_person(person_id)
        if not faces:
            raise HTTPException(status_code=404, detail="No faces found for this person")
        
        # Sort by confidence and get the best face
        faces_sorted = sorted(faces, key=lambda f: f.get('confidence', 0), reverse=True)
        best_face = faces_sorted[0]
        
        # Get the photo for this face
        photo = store.get_photo(best_face['photo_id'])
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        photo_path = photo['file_path']
        if not Path(photo_path).exists():
            raise HTTPException(status_code=404, detail="Photo file not found")
        
        # Read the image
        img = cv2.imread(photo_path)
        if img is None:
            raise HTTPException(status_code=500, detail="Could not read image")
        
        img_height, img_width = img.shape[:2]
        
        # Get face bounding box
        x = best_face['bbox_x']
        y = best_face['bbox_y']
        w = best_face['bbox_w']
        h = best_face['bbox_h']
        
        # Add padding (30% on each side) and make it square
        padding = 0.3
        face_size = max(w, h)
        padded_size = int(face_size * (1 + 2 * padding))
        
        # Center the crop on the face
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Calculate crop coordinates
        crop_x1 = max(0, center_x - padded_size // 2)
        crop_y1 = max(0, center_y - padded_size // 2)
        crop_x2 = min(img_width, crop_x1 + padded_size)
        crop_y2 = min(img_height, crop_y1 + padded_size)
        
        # Adjust if we hit the edge
        if crop_x2 - crop_x1 < padded_size:
            crop_x1 = max(0, crop_x2 - padded_size)
        if crop_y2 - crop_y1 < padded_size:
            crop_y1 = max(0, crop_y2 - padded_size)
        
        # Crop the face
        face_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Resize to requested size (square)
        face_crop = cv2.resize(face_crop, (size, size), interpolation=cv2.INTER_AREA)
        
        # Convert to JPEG
        _, buffer = cv2.imencode('.jpg', face_crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        return Response(
            content=buffer.tobytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
