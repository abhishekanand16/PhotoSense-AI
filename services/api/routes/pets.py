# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
"""Pet identity endpoints (parallel to people endpoints)."""

import io
from pathlib import Path
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.api.models import (
    MergePetsRequest,
    PetDetectionResponse,
    PetResponse,
    PhotoResponse,
    SimilarPetResponse,
    UpdatePetRequest,
)
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("", response_model=List[PetResponse])
async def list_pets():
    """Get all pets. Automatically cleans up orphaned pets with zero detections."""
    store = SQLiteStore()
    try:
        # Clean up orphaned pets (with 0 detections) before listing
        orphaned = store.cleanup_orphaned_pets()
        if orphaned:
            import logging
            logging.info(f"Cleaned up {len(orphaned)} orphaned pets with no detections: {orphaned}")
        
        pets = store.get_all_pets()
        result = []
        for pet in pets:
            detections = store.get_pet_detections_for_pet(pet["id"])
            # Count unique photos, not detections
            unique_photo_ids = {d["photo_id"] for d in detections}
            result.append(
                PetResponse(
                    id=pet["id"],
                    cluster_id=pet.get("cluster_id"),
                    name=pet.get("name"),
                    species=pet.get("species"),
                    detection_count=len(unique_photo_ids),
                )
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pet_id}", response_model=PetResponse)
async def get_pet(pet_id: int):
    """Get a specific pet."""
    store = SQLiteStore()
    try:
        pet = store.get_pet(pet_id)
        if not pet:
            raise HTTPException(status_code=404, detail="Pet not found")
        detections = store.get_pet_detections_for_pet(pet_id)
        unique_photo_ids = {d["photo_id"] for d in detections}
        return PetResponse(
            id=pet["id"],
            cluster_id=pet.get("cluster_id"),
            name=pet.get("name"),
            species=pet.get("species"),
            detection_count=len(unique_photo_ids),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{pet_id}", response_model=PetResponse)
async def update_pet(pet_id: int, request: UpdatePetRequest):
    """Update pet name."""
    store = SQLiteStore()
    try:
        pet = store.get_pet(pet_id)
        if not pet:
            raise HTTPException(status_code=404, detail="Pet not found")
        store.update_pet_name(pet_id, request.name)
        pet = store.get_pet(pet_id)
        detections = store.get_pet_detections_for_pet(pet_id)
        unique_photo_ids = {d["photo_id"] for d in detections}
        return PetResponse(
            id=pet["id"],
            cluster_id=pet.get("cluster_id"),
            name=pet.get("name"),
            species=pet.get("species"),
            detection_count=len(unique_photo_ids),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pet_id}/photos", response_model=List[PhotoResponse])
async def get_photos_for_pet(pet_id: int):
    """Get all photos containing a specific pet."""
    store = SQLiteStore()
    try:
        detections = store.get_pet_detections_for_pet(pet_id)
        photo_ids = {d["photo_id"] for d in detections}
        photos = []
        for photo_id in photo_ids:
            photo = store.get_photo(photo_id)
            if photo:
                photos.append({
                    "id": photo["id"],
                    "file_path": photo["file_path"],
                    "date_taken": photo.get("date_taken"),
                    "camera_model": photo.get("camera_model"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "file_size": photo.get("file_size"),
                    "created_at": str(photo.get("created_at", "")) if photo.get("created_at") else "",
                })
        return photos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge")
async def merge_pets(request: MergePetsRequest):
    """Merge two pets."""
    store = SQLiteStore()
    try:
        if request.source_pet_id == request.target_pet_id:
            raise HTTPException(status_code=400, detail="Cannot merge pet with itself")
        source = store.get_pet(request.source_pet_id)
        target = store.get_pet(request.target_pet_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source pet not found")
        if not target:
            raise HTTPException(status_code=404, detail="Target pet not found")
        store.merge_pets(request.source_pet_id, request.target_pet_id)
        return {"status": "success", "message": "Pets merged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{pet_id}")
async def delete_pet(pet_id: int):
    """Delete a pet and unassign all detections."""
    store = SQLiteStore()
    try:
        deleted = store.delete_pet(pet_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Pet not found")
        return {"status": "success", "message": "Pet deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pet_id}/detections", response_model=List[PetDetectionResponse])
async def get_detections_for_pet(pet_id: int):
    """Get all detections for a specific pet."""
    store = SQLiteStore()
    try:
        detections = store.get_pet_detections_for_pet(pet_id)
        return [
            PetDetectionResponse(
                id=d["id"],
                photo_id=d["photo_id"],
                species=d["species"],
                confidence=d["confidence"],
                bbox_x=d["bbox_x"],
                bbox_y=d["bbox_y"],
                bbox_w=d["bbox_w"],
                bbox_h=d["bbox_h"],
                pet_id=d.get("pet_id"),
            )
            for d in detections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cluster")
async def cluster_pets():
    """Run pet clustering to group pet detections by identity."""
    from services.ml.pipeline import MLPipeline
    
    try:
        pipeline = MLPipeline()
        result = await pipeline.cluster_pets()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pet_id}/similar", response_model=List[SimilarPetResponse])
async def get_similar_pets(pet_id: int, k: int = 10):
    """Find similar pet detections using FAISS k-NN search."""
    from services.ml.pipeline import MLPipeline
    
    store = SQLiteStore()
    try:
        # Get any detection for this pet to use as query
        detections = store.get_pet_detections_for_pet(pet_id)
        if not detections:
            raise HTTPException(status_code=404, detail="No detections found for this pet")
        
        # Use the highest confidence detection as query
        best_detection = max(detections, key=lambda d: d.get("confidence", 0))
        
        pipeline = MLPipeline()
        results = await pipeline.search_similar_pets(best_detection["id"], k=k)
        
        return [
            SimilarPetResponse(
                pet_detection_id=r["pet_detection_id"],
                photo_id=r["photo_id"],
                similarity=r["similarity"],
                species=r["species"],
                confidence=r["confidence"],
                pet_id=r.get("pet_id"),
            )
            for r in results
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pet_id}/thumbnail")
async def get_pet_thumbnail(pet_id: int, size: int = 200):
    """Get a cropped thumbnail for a pet.
    
    Returns the highest-confidence detection crop as a JPEG image.
    """
    store = SQLiteStore()
    try:
        detections = store.get_pet_detections_for_pet(pet_id)
        if not detections:
            raise HTTPException(status_code=404, detail="No detections found for this pet")
        
        # Get best detection
        best = max(detections, key=lambda d: d.get("confidence", 0))
        
        photo = store.get_photo(best["photo_id"])
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        photo_path = photo["file_path"]
        if not Path(photo_path).exists():
            raise HTTPException(status_code=404, detail="Photo file not found")
        
        # Read image
        img = cv2.imread(photo_path)
        if img is None:
            raise HTTPException(status_code=500, detail="Could not read image")
        
        img_height, img_width = img.shape[:2]
        
        # Get bounding box
        x = best["bbox_x"]
        y = best["bbox_y"]
        w = best["bbox_w"]
        h = best["bbox_h"]
        
        # Add padding (30%) and make square
        padding = 0.3
        pet_size = max(w, h)
        padded_size = int(pet_size * (1 + 2 * padding))
        
        center_x = x + w // 2
        center_y = y + h // 2
        
        crop_x1 = max(0, center_x - padded_size // 2)
        crop_y1 = max(0, center_y - padded_size // 2)
        crop_x2 = min(img_width, crop_x1 + padded_size)
        crop_y2 = min(img_height, crop_y1 + padded_size)
        
        if crop_x2 - crop_x1 < padded_size:
            crop_x1 = max(0, crop_x2 - padded_size)
        if crop_y2 - crop_y1 < padded_size:
            crop_y1 = max(0, crop_y2 - padded_size)
        
        # Crop
        crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Resize
        crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
        
        # Encode as JPEG
        _, buffer = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        return Response(
            content=buffer.tobytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_pet_statistics():
    """Get pet-related statistics."""
    store = SQLiteStore()
    try:
        return store.get_pet_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/detection/{detection_id}")
async def delete_pet_detection(detection_id: int):
    """Delete a specific pet detection."""
    store = SQLiteStore()
    try:
        deleted = store.delete_pet_detection(detection_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Detection not found")
        return {"status": "success", "message": "Detection deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
