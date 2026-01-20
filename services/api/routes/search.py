"""Search endpoints - Florence-2 powered semantic search."""

from typing import List, Dict, Set, Tuple
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse, SearchRequest
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/search", tags=["search"])

# ==============================================================================
# SEARCH CONFIGURATION
# ==============================================================================

# Minimum confidence thresholds (lowered for better recall)
MIN_CONFIDENCE = {
    "florence_tag": 0.30,    # Florence-2 generated tags - lowered to catch more
    "scene_tag": 0.20,       # Places365/CLIP scene tags  
    "object": 0.40,          # YOLO objects
    "pet": 0.35,             # Pet detections
    "clip_similarity": 0.20, # CLIP semantic search - lowered for fallback
}

# Scoring weights (Florence-2 is primary source)
SCORE_WEIGHTS = {
    "florence_exact": 10.0,    # Exact Florence-2 tag match (e.g., "moon" = "moon")
    "florence_partial": 6.0,   # Partial match (e.g., "moon" in "crescent moon")
    "scene_exact": 4.0,        # Exact scene tag match
    "object_match": 4.0,       # YOLO object match
    "pet_match": 4.0,          # Pet detection match
    "clip_semantic": 3.0,      # CLIP similarity score - increased importance
    "location_exact": 8.0,     # Exact location match (e.g., "Bangalore" = "Bangalore")
    "location_partial": 5.0,   # Partial location match (e.g., "goa" in "Goa, India")
}


def search_by_florence_tags(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """
    PRIMARY SEARCH: Use Florence-2 rich tags stored in scenes table.
    
    Florence-2 generates descriptive tags like:
    - "crescent moon over city skyline"
    - "golden sunset reflecting on water"
    - "person walking on beach"
    
    This searches those tags directly.
    """
    results = {}
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    
    # Search scenes table (contains Florence-2 tags)
    # Use very low threshold - we'll score by confidence later
    scene_matches = store.search_scenes_by_text(
        query, 
        min_confidence=0.1  # Get all matches, score later
    )
    
    for match in scene_matches:
        photo_id = match["photo_id"]
        tag = match["scene_label"].lower()
        confidence = match["confidence"]
        
        if photo_id not in results:
            results[photo_id] = {
                "florence_matches": [],
                "match_type": None,
                "best_confidence": 0.0
            }
        
        # Determine match quality
        if query_lower == tag:
            # Exact match: "moon" == "moon"
            match_type = "exact"
            score_multiplier = 1.0
        elif query_lower in tag:
            # Query is substring: "moon" in "crescent moon"
            match_type = "partial"
            score_multiplier = 0.9
        elif any(word in tag for word in query_words):
            # Word match: "sunset" in "beautiful sunset over ocean"
            match_type = "word"
            score_multiplier = 0.7
        else:
            match_type = "fuzzy"
            score_multiplier = 0.5
        
        results[photo_id]["florence_matches"].append({
            "tag": match["scene_label"],
            "confidence": confidence,
            "match_type": match_type,
            "score": confidence * score_multiplier
        })
        
        if confidence > results[photo_id]["best_confidence"]:
            results[photo_id]["best_confidence"] = confidence
            results[photo_id]["match_type"] = match_type
    
    return results


def search_by_objects(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """Search YOLO detected objects."""
    results = {}
    query_lower = query.lower().strip()
    
    # Get objects matching the query pattern
    objects = store.get_objects_by_pattern(query_lower)
    
    for obj in objects:
        if obj["confidence"] < 0.3:  # Lower threshold, score later
            continue
            
        photo_id = obj["photo_id"]
        if photo_id not in results:
            results[photo_id] = {
                "object_matches": [],
                "best_confidence": 0.0
            }
        
        results[photo_id]["object_matches"].append({
            "category": obj["category"],
            "confidence": obj["confidence"]
        })
        
        if obj["confidence"] > results[photo_id]["best_confidence"]:
            results[photo_id]["best_confidence"] = obj["confidence"]
    
    return results


def search_by_pets(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """Search pet detections."""
    results = {}
    query_lower = query.lower().strip()
    
    # Map query to pet species
    pet_mappings = {
        "dog": ["dog"],
        "puppy": ["dog"],
        "cat": ["cat"],
        "kitten": ["cat"],
        "bird": ["bird"],
        "horse": ["horse"],
        "pet": ["dog", "cat", "bird"],
        "animal": ["dog", "cat", "bird", "horse"],
    }
    
    species_to_search = set()
    for keyword, species_list in pet_mappings.items():
        if keyword in query_lower:
            species_to_search.update(species_list)
    
    for species in species_to_search:
        detections = store.get_pet_detections_by_species(species)
        for det in detections:
            if det["confidence"] < 0.3:  # Lower threshold
                continue
                
            photo_id = det["photo_id"]
            if photo_id not in results:
                results[photo_id] = {
                    "pet_matches": [],
                    "best_confidence": 0.0
                }
            
            results[photo_id]["pet_matches"].append({
                "species": det["species"],
                "confidence": det["confidence"]
            })
            
            if det["confidence"] > results[photo_id]["best_confidence"]:
                results[photo_id]["best_confidence"] = det["confidence"]
    
    return results


def search_by_location(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """
    Search photos by location name (city, region, country).
    
    Matches place names like:
    - "Bangalore" -> photos in Bangalore
    - "Goa" -> photos in Goa
    - "India" -> photos in India
    - "Beach Goa" -> handled separately (scene + location combination)
    """
    results = {}
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    
    # Search locations table
    location_matches = store.search_locations_by_text(query)
    
    for match in location_matches:
        photo_id = match["photo_id"]
        city = (match.get("city") or "").lower()
        region = (match.get("region") or "").lower()
        country = (match.get("country") or "").lower()
        
        if photo_id not in results:
            results[photo_id] = {
                "location_matches": [],
                "match_type": None,
                "best_score": 0.0
            }
        
        # Determine match quality
        matched_field = None
        match_type = "partial"
        
        # Check for exact matches first
        for word in query_words:
            if word == city or word == region or word == country:
                match_type = "exact"
                if word == city:
                    matched_field = match.get("city")
                elif word == region:
                    matched_field = match.get("region")
                else:
                    matched_field = match.get("country")
                break
            elif word in city or word in region or word in country:
                match_type = "partial"
                if word in city:
                    matched_field = match.get("city")
                elif word in region:
                    matched_field = match.get("region")
                else:
                    matched_field = match.get("country")
        
        if matched_field:
            score = 1.0 if match_type == "exact" else 0.7
            results[photo_id]["location_matches"].append({
                "place": matched_field,
                "match_type": match_type,
                "score": score
            })
            
            if score > results[photo_id]["best_score"]:
                results[photo_id]["best_score"] = score
                results[photo_id]["match_type"] = match_type
    
    return results


async def search_by_clip(pipeline, query: str, existing_ids: Set[int]) -> Dict[int, float]:
    """
    CLIP semantic search - ALWAYS run for visual understanding.
    
    CLIP understands visual concepts that tags might miss:
    - "moon" - understands round bright object in night sky
    - "sunset" - understands orange/red sky colors
    - "beach" - understands sand + water combination
    """
    results = {}
    
    # Always use lower threshold - CLIP is important for visual queries
    min_sim = 0.18 if not existing_ids else MIN_CONFIDENCE["clip_similarity"]
    
    try:
        clip_results = await pipeline.search_similar_images(
            query,
            k=50,  # Get more results
            min_similarity=min_sim,
            return_scores=True
        )
        
        for photo_id, similarity in clip_results:
            results[photo_id] = similarity
            
    except Exception as e:
        import logging
        logging.warning(f"CLIP search failed: {e}")
    
    return results


def calculate_final_score(
    photo_id: int,
    florence_data: Dict,
    object_data: Dict,
    pet_data: Dict,
    clip_similarity: float,
    location_data: Dict = None
) -> float:
    """
    Calculate final relevance score combining all sources.
    
    Priority:
    1. Florence-2 exact/partial matches (highest weight)
    2. Location matches (high weight for place-based searches)
    3. Object/Pet detections  
    4. CLIP semantic similarity (important for visual concepts)
    """
    score = 0.0
    has_tag_match = False
    
    # Florence-2 tag matches (PRIMARY)
    if florence_data and florence_data.get("florence_matches"):
        has_tag_match = True
        for match in florence_data.get("florence_matches", []):
            if match["match_type"] == "exact":
                score += SCORE_WEIGHTS["florence_exact"] * match["confidence"]
            elif match["match_type"] == "partial":
                score += SCORE_WEIGHTS["florence_partial"] * match["confidence"]
            else:
                score += SCORE_WEIGHTS["florence_partial"] * 0.5 * match["confidence"]
    
    # Location matches (HIGH WEIGHT for place-based searches)
    if location_data and location_data.get("location_matches"):
        has_tag_match = True
        for match in location_data.get("location_matches", []):
            if match["match_type"] == "exact":
                score += SCORE_WEIGHTS["location_exact"] * match["score"]
            else:
                score += SCORE_WEIGHTS["location_partial"] * match["score"]
    
    # Object matches
    if object_data and object_data.get("object_matches"):
        has_tag_match = True
        for match in object_data.get("object_matches", []):
            score += SCORE_WEIGHTS["object_match"] * match["confidence"]
    
    # Pet matches
    if pet_data and pet_data.get("pet_matches"):
        has_tag_match = True
        for match in pet_data.get("pet_matches", []):
            score += SCORE_WEIGHTS["pet_match"] * match["confidence"]
    
    # CLIP semantic similarity - IMPORTANT for visual queries
    if clip_similarity > 0:
        # Scale CLIP score (similarity is 0-1, we want meaningful contribution)
        clip_score = SCORE_WEIGHTS["clip_semantic"] * clip_similarity * 5.0
        
        # Bonus if CLIP confirms tag match
        if has_tag_match:
            clip_score *= 1.5  # Confirmation bonus
        
        score += clip_score
    
    # CLIP-only results are still valid (just lower ranked)
    # Don't penalize too harshly - CLIP understands visual concepts
    if not has_tag_match and clip_similarity > 0:
        # Pure CLIP match - still valid but less confident
        score = clip_similarity * SCORE_WEIGHTS["clip_semantic"] * 3.0
    
    return score


@router.post("", response_model=List[PhotoResponse])
async def search_photos(request: SearchRequest):
    """
    Search photos using Florence-2 tags as primary source.
    
    Search priority:
    1. Florence-2 rich tags (exact and partial matches)
    2. Location names (city, region, country)
    3. YOLO object detections
    4. Pet detections  
    5. CLIP semantic similarity (fallback)
    """
    import logging
    
    store = SQLiteStore()
    from services.ml.pipeline import MLPipeline
    pipeline = MLPipeline()

    try:
        if not request.query:
            # No query - return all photos by date
            all_photos = store.get_all_photos()
            return all_photos

        query = request.query.strip()
        logging.info(f"Search query: '{query}'")
        
        # ==================================================================
        # STEP 1: Search Florence-2 tags (PRIMARY SOURCE)
        # ==================================================================
        florence_results = search_by_florence_tags(store, query)
        logging.info(f"Florence-2 matches: {len(florence_results)} photos")
        
        # ==================================================================
        # STEP 2: Search by location names
        # ==================================================================
        location_results = search_by_location(store, query)
        logging.info(f"Location matches: {len(location_results)} photos")
        
        # ==================================================================
        # STEP 3: Search YOLO objects
        # ==================================================================
        object_results = search_by_objects(store, query)
        logging.info(f"Object matches: {len(object_results)} photos")
        
        # ==================================================================
        # STEP 4: Search pet detections (if relevant)
        # ==================================================================
        pet_keywords = ["dog", "cat", "bird", "horse", "pet", "puppy", "kitten", "animal"]
        pet_results = {}
        if any(kw in query.lower() for kw in pet_keywords):
            pet_results = search_by_pets(store, query)
            logging.info(f"Pet matches: {len(pet_results)} photos")
        
        # Collect all candidate photo IDs
        candidate_ids = (
            set(florence_results.keys()) | 
            set(location_results.keys()) |
            set(object_results.keys()) | 
            set(pet_results.keys())
        )
        
        # ==================================================================
        # STEP 5: CLIP semantic search (fallback or enhancement)
        # ==================================================================
        clip_results = await search_by_clip(pipeline, query, candidate_ids)
        logging.info(f"CLIP matches: {len(clip_results)} photos")
        
        # Add CLIP-only results to candidates
        candidate_ids.update(clip_results.keys())
        
        # ==================================================================
        # STEP 6: Calculate scores and rank
        # ==================================================================
        scored_photos = []
        
        for photo_id in candidate_ids:
            photo = store.get_photo(photo_id)
            if not photo:
                continue
            
            florence_data = florence_results.get(photo_id)
            location_data = location_results.get(photo_id)
            object_data = object_results.get(photo_id)
            pet_data = pet_results.get(photo_id)
            clip_sim = clip_results.get(photo_id, 0.0)
            
            score = calculate_final_score(
                photo_id=photo_id,
                florence_data=florence_data,
                object_data=object_data,
                pet_data=pet_data,
                clip_similarity=clip_sim,
                location_data=location_data
            )
            
            # Only filter out if score is effectively zero
            if score < 0.1:
                continue
            
            scored_photos.append((score, photo))
            
            # Log what matched for debugging
            matches = []
            if florence_data and florence_data.get("florence_matches"):
                matches.append(f"florence:{len(florence_data['florence_matches'])}")
            if location_data and location_data.get("location_matches"):
                matches.append(f"location:{len(location_data['location_matches'])}")
            if object_data and object_data.get("object_matches"):
                matches.append(f"objects:{len(object_data['object_matches'])}")
            if pet_data and pet_data.get("pet_matches"):
                matches.append(f"pets:{len(pet_data['pet_matches'])}")
            if clip_sim > 0:
                matches.append(f"clip:{clip_sim:.2f}")
            logging.info(f"Photo {photo_id}: score={score:.2f} [{', '.join(matches)}]")
        
        # Sort by score (highest first)
        scored_photos.sort(key=lambda x: x[0], reverse=True)
        results = [photo for _, photo in scored_photos]
        
        logging.info(f"Returning {len(results)} ranked results")
        
        # ==================================================================
        # STEP 6: Apply filters (person, category, date)
        # ==================================================================
        if request.person_id:
            faces = store.get_faces_for_person(request.person_id)
            person_photo_ids = {face["photo_id"] for face in faces}
            results = [p for p in results if p["id"] in person_photo_ids]
        
        if request.category:
            objects = store.get_objects_by_category(request.category)
            category_photo_ids = {obj["photo_id"] for obj in objects}
            results = [p for p in results if p["id"] in category_photo_ids]
        
        if request.date_start or request.date_end:
            filtered = []
            for photo in results:
                date_taken = photo.get("date_taken")
                if date_taken:
                    if request.date_start and date_taken < request.date_start:
                        continue
                    if request.date_end and date_taken > request.date_end:
                        continue
                filtered.append(photo)
            results = filtered
        
        return results

    except Exception as e:
        logging.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
