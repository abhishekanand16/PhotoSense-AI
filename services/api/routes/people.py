"""People/cluster-related endpoints."""

import io
from pathlib import Path
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.api.models import MergePeopleRequest, MergeMultiplePeopleRequest, PersonResponse, PhotoResponse, UpdatePersonRequest
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=List[PersonResponse])
async def list_people():
    """Get all people."""
    store = SQLiteStore()
    try:
        people = store.get_all_people()
        # Add photo counts (unique photos, not face count)
        result = []
        for person in people:
            faces = store.get_faces_for_person(person["id"])
            # Count unique photos, not faces (a person can appear multiple times in one photo)
            unique_photo_ids = {face["photo_id"] for face in faces}
            result.append(
                PersonResponse(
                    id=person["id"],
                    cluster_id=person.get("cluster_id"),
                    name=person.get("name"),
                    face_count=len(unique_photo_ids),  # This is actually photo count now
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
        # Count unique photos, not faces
        unique_photo_ids = {face["photo_id"] for face in faces}
        return PersonResponse(
            id=person["id"],
            cluster_id=person.get("cluster_id"),
            name=person.get("name"),
            face_count=len(unique_photo_ids),
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


@router.post("/merge-multiple")
async def merge_multiple_people(request: MergeMultiplePeopleRequest):
    """
    Merge multiple people into a single target person.
    
    This is the primary endpoint for face management. When merging:
    1. All faces from person_ids are reassigned to target_person_id
    2. Source person records are deleted
    3. Embeddings remain intact under the merged identity
    4. Future scans will auto-assign similar faces to this identity
    
    Args:
        person_ids: List of person IDs to merge (will be deleted)
        target_person_id: The person to merge all others into (kept)
        min_confidence: Minimum face confidence threshold (default 0.5)
    
    Returns:
        Summary of merge operation with face counts
    """
    import logging
    
    store = SQLiteStore()
    try:
        # Validate target exists
        target_person = store.get_person(request.target_person_id)
        if not target_person:
            raise HTTPException(status_code=404, detail=f"Target person {request.target_person_id} not found")
        
        # Validate person_ids don't include target
        if request.target_person_id in request.person_ids:
            raise HTTPException(status_code=400, detail="Target person cannot be in the merge list")
        
        # Validate all source persons exist
        source_persons = []
        for person_id in request.person_ids:
            person = store.get_person(person_id)
            if not person:
                raise HTTPException(status_code=404, detail=f"Source person {person_id} not found")
            source_persons.append(person)
        
        total_faces_merged = 0
        low_confidence_skipped = 0
        persons_merged = 0
        
        for person_id in request.person_ids:
            # Get faces for this person
            faces = store.get_faces_for_person(person_id)
            
            # Filter by confidence threshold
            high_conf_face_ids = []
            for face in faces:
                if face.get("confidence", 0) >= request.min_confidence:
                    high_conf_face_ids.append(face["id"])
                else:
                    low_confidence_skipped += 1
            
            # Reassign faces to target person
            if high_conf_face_ids:
                store.update_faces_person(high_conf_face_ids, request.target_person_id)
                total_faces_merged += len(high_conf_face_ids)
            
            # Delete the source person record
            store.delete_person(person_id)
            persons_merged += 1
            
            logging.info(f"Merged person {person_id} ({len(high_conf_face_ids)} faces) into {request.target_person_id}")
        
        # Get updated target face count
        target_faces = store.get_faces_for_person(request.target_person_id)
        unique_photos = {f["photo_id"] for f in target_faces}
        
        return {
            "status": "success",
            "message": f"Merged {persons_merged} people into person {request.target_person_id}",
            "persons_merged": persons_merged,
            "faces_merged": total_faces_merged,
            "low_confidence_skipped": low_confidence_skipped,
            "target_person_id": request.target_person_id,
            "target_total_faces": len(target_faces),
            "target_unique_photos": len(unique_photos),
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Multi-merge failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{person_id}")
async def delete_person(person_id: int):
    """
    Delete a person and unassign all their faces.
    Faces remain in the database but are unassigned (person_id = NULL).
    """
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


@router.delete("/{person_id}/with-faces")
async def delete_person_with_faces(person_id: int):
    """
    Delete a person AND all their faces from the database.
    
    This is a complete removal:
    1. All face records for this person are deleted
    2. All face embeddings are deleted from DB
    3. The person record is deleted
    4. FAISS index is rebuilt automatically
    
    Use this for removing incorrectly detected faces or unwanted identities.
    """
    import logging
    
    store = SQLiteStore()
    try:
        # Verify person exists
        person = store.get_person(person_id)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get all faces for this person
        faces = store.get_faces_for_person(person_id)
        face_ids = [f["id"] for f in faces]
        
        # Delete all faces (this also deletes embeddings from DB)
        deleted_faces = 0
        for face_id in face_ids:
            if store.delete_face(face_id):
                deleted_faces += 1
        
        # Delete the person record
        store.delete_person(person_id)
        
        # Rebuild FAISS index to remove deleted embeddings
        try:
            from services.ml.pipeline import MLPipeline
            pipeline = MLPipeline()
            rebuild_result = await pipeline.rebuild_faiss_index()
            logging.info(f"FAISS index rebuilt: {rebuild_result}")
        except Exception as e:
            logging.warning(f"FAISS rebuild failed (can be done manually): {str(e)}")
        
        return {
            "status": "success",
            "message": f"Person {person_id} and {deleted_faces} faces deleted",
            "person_id": person_id,
            "faces_deleted": deleted_faces,
        }
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


@router.post("/cleanup-duplicates")
async def cleanup_duplicate_people(dry_run: bool = False):
    """Clean up duplicate people with the same cluster_id.
    
    This merges people who have the same cluster_id, keeping the oldest person
    and merging all others into it. Also removes orphaned people with no faces.
    
    Args:
        dry_run: If True, only reports what would be done without making changes
        
    Returns:
        Statistics about the cleanup operation
    """
    try:
        from services.ml.cleanup_duplicates import merge_duplicate_people, cleanup_orphaned_people
        
        store = SQLiteStore()
        
        # Step 1: Merge duplicate people
        merge_result = merge_duplicate_people(store, dry_run=dry_run)
        
        # Step 2: Clean up orphaned people
        orphan_result = cleanup_orphaned_people(store, dry_run=dry_run)
        
        return {
            "status": "success",
            "merge_result": merge_result,
            "orphan_result": orphan_result,
            "dry_run": dry_run
        }
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
