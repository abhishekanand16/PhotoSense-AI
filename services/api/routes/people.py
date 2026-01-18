"""People/cluster-related endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import MergePeopleRequest, PersonResponse, UpdatePersonRequest
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
