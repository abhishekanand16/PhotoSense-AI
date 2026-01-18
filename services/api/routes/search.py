"""Search endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse, SearchRequest
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=List[PhotoResponse])
async def search_photos(request: SearchRequest):
    """Search photos by various criteria."""
    store = SQLiteStore()
    # Lazy import to avoid blocking server startup
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        # Start with all photos or text search results
        candidate_ids = None

        # Text-based semantic search
        if request.query:
            photo_ids = await pipeline.search_similar_images(request.query, k=50)
            candidate_ids = set(photo_ids)
        else:
            # If no query, start with all photos
            all_photos = store.get_all_photos()
            candidate_ids = {photo["id"] for photo in all_photos}

        # Apply filters (AND logic - all filters must match)
        # Person filter
        if request.person_id:
            faces = store.get_faces_for_person(request.person_id)
            person_photo_ids = {face["photo_id"] for face in faces}
            candidate_ids = candidate_ids & person_photo_ids

        # Category filter
        if request.category:
            objects = store.get_objects_by_category(request.category)
            category_photo_ids = {obj["photo_id"] for obj in objects}
            candidate_ids = candidate_ids & category_photo_ids

        # Date range filter
        if request.date_start or request.date_end:
            date_filtered_ids = set()
            for photo_id in candidate_ids:
                photo = store.get_photo(photo_id)
                if photo:
                    date_taken = photo.get("date_taken")
                    if date_taken:
                        if request.date_start and date_taken < request.date_start:
                            continue
                        if request.date_end and date_taken > request.date_end:
                            continue
                        date_filtered_ids.add(photo_id)
            candidate_ids = candidate_ids & date_filtered_ids

        # Convert IDs to photo objects
        results = []
        for photo_id in candidate_ids:
            photo = store.get_photo(photo_id)
            if photo:
                results.append(photo)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
