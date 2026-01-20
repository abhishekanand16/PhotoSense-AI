"""Search endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse, SearchRequest
from services.ml.storage.sqlite_store import SQLiteStore
from services.ml.utils.search_utils import SearchQueryProcessor

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=List[PhotoResponse])
async def search_photos(request: SearchRequest):
    """Enhanced search with scene detection, object detection, and CLIP fallback."""
    import logging
    
    store = SQLiteStore()
    # Lazy import to avoid blocking server startup
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        # Start with all photos or text search results
        candidate_ids = None

        # Text-based search with intelligent query processing
        if request.query:
            # Process query using SearchQueryProcessor
            query_info = SearchQueryProcessor.process_query(request.query)
            scene_tags = query_info['scene_tags']
            object_patterns = query_info['object_patterns']
            should_use_clip = query_info['should_use_clip']
            
            # Priority 1: Scene detection matches
            scene_photo_ids = set()
            if scene_tags:
                for tag in scene_tags:
                    try:
                        scene_photo_ids.update(store.get_photos_by_scene(tag))
                    except Exception as e:
                        logging.warning(f"Scene search failed for tag '{tag}': {e}")
            
            # Priority 2: Object detection matches
            object_photo_ids = set()
            if object_patterns:
                # Search for objects matching any of the patterns
                for pattern in object_patterns:
                    try:
                        # Use pattern matching to find objects
                        # This searches the "simplified:original" format
                        objects = store.get_objects_by_pattern(pattern)
                        for obj in objects:
                            object_photo_ids.add(obj["photo_id"])
                    except Exception as e:
                        logging.warning(f"Object search failed for pattern '{pattern}': {e}")
            
            # Priority 2.5: Pet detection matches (for animal-related queries)
            pet_photo_ids = set()
            pet_species = ['dog', 'cat', 'bird', 'horse', 'animal']
            query_lower = request.query.lower()
            is_pet_query = any(species in query_lower for species in ['dog', 'cat', 'bird', 'horse', 'pet', 'puppy', 'kitten', 'animal'])
            
            if is_pet_query:
                try:
                    # Search pet detections by species
                    for species in pet_species:
                        if species in query_lower or 'pet' in query_lower or 'animal' in query_lower:
                            detections = store.get_pet_detections_by_species(species)
                            for det in detections:
                                pet_photo_ids.add(det["photo_id"])
                except Exception as e:
                    logging.warning(f"Pet search failed: {e}")
            
            # Combine results (OR logic - photos matching scenes OR objects OR pets)
            if scene_photo_ids or object_photo_ids or pet_photo_ids:
                candidate_ids = scene_photo_ids | object_photo_ids | pet_photo_ids
            
            # Priority 3: CLIP semantic search fallback
            if not candidate_ids or should_use_clip:
                try:
                    # Use CLIP for complex queries or when no matches found
                    # Apply similarity threshold to filter out irrelevant results
                    #
                    # CLIP cosine similarity ranges (based on empirical testing):
                    # - 0.30+ = Strong match (image clearly contains the query concept)
                    # - 0.26-0.30 = Good match (likely relevant)
                    # - 0.22-0.26 = Weak match (might be tangentially related)
                    # - <0.22 = No match (random/unrelated images)
                    #
                    # Threshold selection:
                    # - If we have scene/object matches, use higher threshold (0.28)
                    #   to only add highly relevant semantic matches
                    # - If no matches found, use moderate threshold (0.26)
                    #   to find relevant results while filtering noise
                    
                    min_similarity = 0.28 if candidate_ids else 0.26
                    
                    photo_ids = await pipeline.search_similar_images(
                        request.query, 
                        k=50,
                        min_similarity=min_similarity
                    )
                    clip_ids = set(photo_ids)
                    
                    logging.info(f"CLIP search for '{request.query}': {len(clip_ids)} results above threshold {min_similarity}")
                    
                    if candidate_ids:
                        # Combine with existing results (union)
                        candidate_ids = candidate_ids | clip_ids
                    else:
                        candidate_ids = clip_ids
                except Exception as e:
                    logging.warning(f"CLIP search failed: {e}")
                    # If CLIP fails and we have no results, return empty
                    if not candidate_ids:
                        candidate_ids = set()
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
