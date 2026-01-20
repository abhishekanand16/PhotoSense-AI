"""
Face management endpoints.

Provides granular control over individual face detections:
- Delete incorrect face detections
- Find similar faces (k-NN search via FAISS)
- Rebuild FAISS index after deletions
- Re-cluster all faces with updated parameters
- Get face details

These endpoints complement the people.py routes which manage identities.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.ml.pipeline import MLPipeline
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/faces", tags=["faces"])


class DeleteMultipleFacesRequest(BaseModel):
    """Request to delete multiple faces."""
    face_ids: List[int]
    rebuild_index: bool = True  # Rebuild FAISS after deletion


@router.delete("/{face_id}")
async def delete_face(face_id: int, rebuild_index: bool = False):
    """
    Delete a specific face detection.
    
    Args:
        face_id: ID of the face to delete
        rebuild_index: If True, rebuild FAISS index after deletion (slower but ensures consistency)
async def delete_face(face_id: int):
    """
    Delete a specific face detection.
    Automatically cleans up the person if this was their last face (even if named).
    """
    try:
        pipeline = MLPipeline()
        result = await pipeline.delete_face(face_id)
        
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Face not found")
        
        # Optionally rebuild FAISS index
        if rebuild_index:
            try:
                rebuild_result = await pipeline.rebuild_faiss_index()
                logging.info(f"FAISS index rebuilt after face deletion: {rebuild_result}")
            except Exception as e:
                logging.warning(f"FAISS rebuild failed: {str(e)}")
        
        return {
            "status": "success",
            "message": "Face deleted successfully",
            "face_id": face_id,
            "index_rebuilt": rebuild_index,
        }
        message = "Face deleted successfully"
        if result.get("person_cleaned_up"):
            message += " (person with no remaining faces was also deleted)"
        
        return {"status": "success", "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-multiple")
async def delete_multiple_faces(request: DeleteMultipleFacesRequest):
    """
    Delete multiple face detections at once.
    
    More efficient than deleting one by one when cleaning up
    multiple incorrect detections.
    """
    try:
        store = SQLiteStore()
        pipeline = MLPipeline()
        
        deleted_count = 0
        not_found = []
        errors = []
        
        for face_id in request.face_ids:
            try:
                result = await pipeline.delete_face(face_id)
                if result["status"] == "not_found":
                    not_found.append(face_id)
                else:
                    deleted_count += 1
            except Exception as e:
                logging.error(f"Failed to delete face {face_id}: {str(e)}")
                errors.append(face_id)
        
        # Rebuild FAISS index once at the end
        index_rebuilt = False
        if request.rebuild_index and deleted_count > 0:
            try:
                rebuild_result = await pipeline.rebuild_faiss_index()
                index_rebuilt = True
                logging.info(f"FAISS index rebuilt after batch deletion: {rebuild_result}")
            except Exception as e:
                logging.warning(f"FAISS rebuild failed: {str(e)}")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "not_found": not_found,
            "errors": errors,
            "index_rebuilt": index_rebuilt,
            "message": f"Deleted {deleted_count} faces",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{face_id}/similar")
async def get_similar_faces(face_id: int, k: int = 10):
    """
    Find similar faces to the given face.
    Returns k most similar faces based on embedding similarity.
    """
    try:
        pipeline = MLPipeline()
        similar_faces = await pipeline.search_similar_faces(face_id, k=k)
        return similar_faces
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild-index")
async def rebuild_faiss_index():
    """
    Rebuild FAISS index from scratch.
    Useful after deletions or index corruption.
    """
    try:
        pipeline = MLPipeline()
        result = await pipeline.rebuild_faiss_index()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recluster")
async def recluster_all_faces():
    """
    Re-run clustering on all faces.
    Useful when adding new faces or adjusting clustering parameters.
    """
    try:
        pipeline = MLPipeline()
        result = await pipeline.cluster_faces()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{face_id}")
async def get_face(face_id: int):
    """Get face details by ID."""
    store = SQLiteStore()
    try:
        face = store.get_face(face_id)
        if not face:
            raise HTTPException(status_code=404, detail="Face not found")
        return face
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
