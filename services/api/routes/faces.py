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

from typing import List

from fastapi import APIRouter, HTTPException

from services.ml.pipeline import MLPipeline
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/faces", tags=["faces"])


@router.delete("/{face_id}")
async def delete_face(face_id: int):
    """Delete a specific face detection."""
    try:
        pipeline = MLPipeline()
        result = await pipeline.delete_face(face_id)
        
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Face not found")
        
        return {"status": "success", "message": "Face deleted successfully"}
    except HTTPException:
        raise
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
