# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
from typing import List, Dict, Set, Tuple

from fastapi import APIRouter, HTTPException

from services.api.models import PhotoResponse, SearchRequest
from services.ml.storage.sqlite_store import SQLiteStore
from services.config import (
    SEARCH_CLOTHING_KEYWORDS,
    SEARCH_COLOR_KEYWORDS,
    SEARCH_GENERIC_TAGS,
    SEARCH_LOCATION_INDICATORS,
    SEARCH_MATCH_MULTIPLIERS,
    SEARCH_MIN_CONFIDENCE,
    SEARCH_OBJECT_KEYWORDS,
    SEARCH_PERSON_INDICATORS,
    SEARCH_PET_KEYWORDS,
    SEARCH_SCENE_KEYWORDS,
    SEARCH_SCORE_WEIGHTS,
    SEARCH_SOURCE_WEIGHTS,
    SEARCH_SYNONYMS,
)

router = APIRouter(prefix="/search", tags=["search"])

def detect_query_intent(query: str) -> Dict[str, float]:
    """
    Detect query intent using simple keyword rules.
    Returns boost multipliers for each source type.
    
    Intent types:
    - person: boost face/person matches (especially for named people)
    - location: boost location matches  
    - scene: boost Florence scene tags
    - object: boost YOLO object matches
    - pet: boost pet detections
    - clothing: boost Florence (has clothing descriptions)
    - color: boost CLIP (great for color understanding)
    """
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())
    
    boosts = {
        "person": 1.0,
        "location": 1.0,
        "florence": 1.0,
        "object": 1.0,
        "pet": 1.0,
        "clip": 1.0,
    }
    
    # Check for person-related indicators
    person_indicators = query_words & SEARCH_PERSON_INDICATORS
    if person_indicators:
        boosts["person"] = 1.5
    
    # Check for person name pattern (capitalized word not in common keywords)
    # Simple heuristic: if query has capitalized words that aren't scene/object keywords
    words = query.split()
    potential_names = [w for w in words if len(w) > 1 and w[0].isupper() 
                       and w.lower() not in SEARCH_SCENE_KEYWORDS 
                       and w.lower() not in SEARCH_OBJECT_KEYWORDS 
                       and w.lower() not in SEARCH_PET_KEYWORDS
                       and w.lower() not in SEARCH_LOCATION_INDICATORS
                       and w.lower() not in SEARCH_PERSON_INDICATORS
                       and w.lower() not in SEARCH_CLOTHING_KEYWORDS
                       and w.lower() not in SEARCH_COLOR_KEYWORDS]
    if potential_names:
        boosts["person"] = 1.8  # Strong boost for potential person names
    
    # Check for location indicators (words like "in", "at", "from" followed by capitalized word)
    if any(ind in query_lower for ind in SEARCH_LOCATION_INDICATORS):
        boosts["location"] = 1.3
    
    # Check for scene keywords
    scene_matches = query_words & SEARCH_SCENE_KEYWORDS
    if scene_matches:
        boosts["florence"] = 1.3
        boosts["clip"] = 1.2  # CLIP good for visual scenes
    
    # Check for object keywords
    object_matches = query_words & SEARCH_OBJECT_KEYWORDS
    if object_matches:
        boosts["object"] = 1.3
    
    # Check for pet keywords
    pet_matches = query_words & SEARCH_PET_KEYWORDS
    if pet_matches:
        boosts["pet"] = 1.4
        boosts["object"] = 0.8  # Reduce object boost when looking for pets
    
    # Check for clothing keywords
    # Florence-2 captions often describe clothing (e.g., "person wearing red dress")
    clothing_matches = query_words & SEARCH_CLOTHING_KEYWORDS
    if clothing_matches:
        boosts["florence"] *= 1.5  # Florence is great at describing clothing
        boosts["clip"] *= 1.3      # CLIP understands visual clothing concepts
    
    # Check for color keywords
    # CLIP is excellent at understanding colors
    color_matches = query_words & SEARCH_COLOR_KEYWORDS
    if color_matches:
        boosts["florence"] *= 1.4  # Florence captions often include colors
        boosts["clip"] *= 1.5      # CLIP is excellent at color understanding
    
    # Check for combined clothing + color queries (e.g., "red dress", "blue shirt")
    if clothing_matches and color_matches:
        # Both present - strong boost for both sources
        boosts["florence"] *= 1.2  # Additional boost for combined query
        boosts["clip"] *= 1.2
    
    return boosts


def has_tag_overlap(query: str, tags: List[str]) -> bool:
    """
    Check if query has meaningful word overlap with any tags.
    Used to filter CLIP-only results without tag relevance.
    """
    if not tags:
        return False
    
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())
    
    # Remove generic words from query for overlap check
    meaningful_query_words = query_words - SEARCH_GENERIC_TAGS - SEARCH_LOCATION_INDICATORS
    if not meaningful_query_words:
        meaningful_query_words = query_words  # Fall back to all words
    
    for tag in tags:
        tag_lower = tag.lower()
        tag_words = set(tag_lower.split())
        
        # Check for word overlap
        if meaningful_query_words & tag_words:
            return True
        
        # Check if any query word is substring of tag
        for qw in meaningful_query_words:
            if len(qw) >= 3 and qw in tag_lower:
                return True
    
    return False


def is_generic_only_match(matched_tags: List[str]) -> bool:
    """
    Check if all matched tags are generic (should be down-ranked).
    """
    if not matched_tags:
        return False
    
    for tag in matched_tags:
        tag_words = set(tag.lower().split())
        # If any word in the tag is NOT generic, it's not a generic-only match
        if tag_words - SEARCH_GENERIC_TAGS:
            return False
    
    return True


def expand_query_with_synonyms(query: str) -> List[str]:
    """
    Expand query with synonyms for better partial matching.
    
    For example:
    - "half moon" -> ["half moon", "crescent moon", "quarter moon", "gibbous moon"]
    - "waxing moon" -> ["waxing moon", "waxing crescent", "waxing gibbous"]
    
    Returns list of search terms to use (original query + synonyms).
    """
    query_lower = query.lower().strip()
    
    # Start with original query
    search_terms = [query_lower]
    
    # Check for exact synonym matches first
    if query_lower in SEARCH_SYNONYMS:
        search_terms.extend(SEARCH_SYNONYMS[query_lower])
    
    # Check for partial synonym matches (e.g., "blue moon" matches "moon")
    for key, synonyms in SEARCH_SYNONYMS.items():
        # If query contains the key as a substring, add synonyms
        if key in query_lower and key != query_lower:
            search_terms.extend(synonyms)
        # If key contains the query as a substring, add synonyms
        elif query_lower in key and key != query_lower:
            search_terms.extend(synonyms)
    
    # Deduplicate while preserving order
    seen = set()
    unique_terms = []
    for term in search_terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
    
    return unique_terms


def search_by_people_name(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """
    Search for photos containing named people.
    
    Searches the people table for names matching the query,
    then finds all photos containing those people.
    
    Examples:
    - "John" matches photos with "John", "John Doe", "Johnny"
    - "Sarah Smith" matches photos with "Sarah Smith"
    """
    results = {}
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())
    
    # Search for people matching the query
    people_matches = store.search_people_by_name(query)
    
    for person in people_matches:
        person_id = person["id"]
        person_name = person["name"]
        match_type = person["match_type"]
        
        # Get all photos containing this person
        photo_ids = store.get_photo_ids_for_person(person_id)
        
        for photo_id in photo_ids:
            if photo_id not in results:
                results[photo_id] = {
                    "person_matches": [],
                    "matched_tags": [],
                    "match_type": None,
                    "best_score": 0.0,
                    "has_exact_match": False,
                }
            
            # Calculate match score
            if match_type == "exact":
                score = 1.0
            elif match_type == "partial":
                score = 0.8
            else:
                score = 0.6
            
            results[photo_id]["person_matches"].append({
                "person_id": person_id,
                "name": person_name,
                "match_type": match_type,
                "score": score,
            })
            results[photo_id]["matched_tags"].append(person_name)
            
            if match_type == "exact":
                results[photo_id]["has_exact_match"] = True
            
            if score > results[photo_id]["best_score"]:
                results[photo_id]["best_score"] = score
                results[photo_id]["match_type"] = match_type
    
    return results


def search_by_florence_tags(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """
    PRIMARY SEARCH: Use Florence-2 rich tags stored in scenes table.
    
    Florence-2 generates descriptive tags like:
    - "crescent moon over city skyline"
    - "golden sunset reflecting on water"
    - "person walking on beach"
    
    This searches those tags directly with confidence threshold pruning.
    Now includes synonym expansion for better partial matching
    (e.g., "half moon" also searches for "crescent moon", "quarter moon").
    """
    results = {}
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())
    
    # Expand query with synonyms for better partial matching
    search_terms = expand_query_with_synonyms(query)
    
    # Search for each term and combine results
    all_scene_matches = []
    for term in search_terms:
        scene_matches = store.search_scenes_by_text(
            term, 
            min_confidence=0.1  # Get all matches, filter by threshold below
        )
        all_scene_matches.extend(scene_matches)
    
    # Deduplicate matches by (photo_id, scene_label)
    seen = set()
    unique_matches = []
    for match in all_scene_matches:
        key = (match["photo_id"], match["scene_label"])
        if key not in seen:
            seen.add(key)
            unique_matches.append(match)
    
    for match in unique_matches:
        photo_id = match["photo_id"]
        tag = match["scene_label"].lower()
        confidence = match["confidence"]
        
        # Apply confidence threshold pruning
        if confidence < SEARCH_MIN_CONFIDENCE["florence_tag"]:
            continue
        
        if photo_id not in results:
            results[photo_id] = {
                "florence_matches": [],
                "matched_tags": [],  # For tag overlap checking
                "match_type": None,
                "best_confidence": 0.0,
                "has_exact_match": False,
            }
        
        # Determine match quality - check against original query and all search terms
        if query_lower == tag:
            match_type = "exact"
        elif query_lower in tag:
            match_type = "partial"
        elif any(term in tag for term in search_terms if term != query_lower):
            # Synonym match - treat as partial
            match_type = "partial"
        elif query_words & set(tag.split()):
            match_type = "word"
        else:
            match_type = "fuzzy"
        
        results[photo_id]["florence_matches"].append({
            "tag": match["scene_label"],
            "confidence": confidence,
            "match_type": match_type,
        })
        results[photo_id]["matched_tags"].append(match["scene_label"])
        
        if match_type == "exact":
            results[photo_id]["has_exact_match"] = True
        
        if confidence > results[photo_id]["best_confidence"]:
            results[photo_id]["best_confidence"] = confidence
            results[photo_id]["match_type"] = match_type
    
    return results


def search_by_objects(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """Search YOLO detected objects with confidence threshold pruning."""
    results = {}
    query_lower = query.lower().strip()
    
    # Get objects matching the query pattern
    objects = store.get_objects_by_pattern(query_lower)
    
    for obj in objects:
        # Apply stricter confidence threshold
        if obj["confidence"] < SEARCH_MIN_CONFIDENCE["object"]:
            continue
            
        photo_id = obj["photo_id"]
        if photo_id not in results:
            results[photo_id] = {
                "object_matches": [],
                "matched_tags": [],  # For tag overlap checking
                "best_confidence": 0.0,
            }
        
        results[photo_id]["object_matches"].append({
            "category": obj["category"],
            "confidence": obj["confidence"],
        })
        results[photo_id]["matched_tags"].append(obj["category"])
        
        if obj["confidence"] > results[photo_id]["best_confidence"]:
            results[photo_id]["best_confidence"] = obj["confidence"]
    
    return results


def search_by_pets(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """Search pet detections with confidence threshold pruning."""
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
            # Apply stricter confidence threshold
            if det["confidence"] < SEARCH_MIN_CONFIDENCE["pet"]:
                continue
                
            photo_id = det["photo_id"]
            if photo_id not in results:
                results[photo_id] = {
                    "pet_matches": [],
                    "matched_tags": [],  # For tag overlap checking
                    "best_confidence": 0.0,
                }
            
            results[photo_id]["pet_matches"].append({
                "species": det["species"],
                "confidence": det["confidence"],
            })
            results[photo_id]["matched_tags"].append(det["species"])
            
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
                "matched_tags": [],  # For tag overlap checking
                "match_type": None,
                "best_score": 0.0,
                "has_exact_match": False,
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
                "score": score,
            })
            results[photo_id]["matched_tags"].append(matched_field)
            
            if match_type == "exact":
                results[photo_id]["has_exact_match"] = True
            
            if score > results[photo_id]["best_score"]:
                results[photo_id]["best_score"] = score
                results[photo_id]["match_type"] = match_type
    
    return results


def search_by_custom_tags(store: SQLiteStore, query: str) -> Dict[int, Dict]:
    """
    Search user-created custom tags.
    
    Custom tags have the HIGHEST priority because they represent
    explicit user intent and organization. A user tagging a photo
    "family vacation" means that's exactly what the photo is about.
    
    Returns dict mapping photo_id to match info.
    """
    results = {}
    query_lower = query.lower().strip()
    
    # Search custom tags
    tag_matches = store.search_tags_by_text(query_lower)
    
    for match in tag_matches:
        photo_id = match["photo_id"]
        tag = match["tag"]
        match_type = match["match_type"]  # 'exact', 'partial', or 'word'
        
        if photo_id not in results:
            results[photo_id] = {
                "tag_matches": [],
                "match_type": None,
                "best_score": 0.0
            }
        
        # Determine score based on match type
        if match_type == "exact":
            score = 1.0
        elif match_type == "partial":
            score = 0.8
        else:
            score = 0.6
        
        results[photo_id]["tag_matches"].append({
            "tag": tag,
            "match_type": match_type,
            "score": score
        })
        
        if score > results[photo_id]["best_score"]:
            results[photo_id]["best_score"] = score
            results[photo_id]["match_type"] = match_type
    
    return results


async def search_by_clip(pipeline, query: str, existing_ids: Set[int]) -> Dict[int, float]:
    """
    CLIP semantic search - supporting signal only.
    
    CLIP understands visual concepts that tags might miss:
    - "moon" - understands round bright object in night sky
    - "sunset" - understands orange/red sky colors
    - "beach" - understands sand + water combination
    
    NOTE: CLIP-only results are filtered unless they have tag overlap with query.
    """
    results = {}
    
    # Use consistent threshold
    min_sim = SEARCH_MIN_CONFIDENCE["clip_similarity"]
    
    try:
        clip_results = await pipeline.search_similar_images(
            query,
            k=50,
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
    location_data: Dict = None,
    custom_tag_data: Dict = None,
    person_data: Dict = None,
    intent_boosts: Dict[str, float] = None,
    query: str = "",
) -> Tuple[float, Dict]:
    """
    Calculate final relevance score using source-aware weighted scoring.
    
    Scoring rules:
    1. Exact tag match > semantic similarity
    2. Multi-signal match > single-signal match
    3. Penalize results matching via ONE weak signal only
    4. Apply intent boosts based on query type
    
    Priority:
    1. Custom user tags (HIGHEST - explicit user intent)
    2. Named people matches (HIGH - user assigned names)
    3. Florence-2 exact/partial matches (high weight)
    4. Location matches (high weight for place-based searches)
    5. Object/Pet detections  
    6. CLIP semantic similarity (important for visual concepts)
    Returns:
        Tuple of (score, match_info dict for debugging)
    """
    if intent_boosts is None:
        intent_boosts = {k: 1.0 for k in SEARCH_SOURCE_WEIGHTS}
    
    score = 0.0
    source_scores = {}  # Track per-source contributions
    matched_sources = []  # Track which sources matched
    all_matched_tags = []  # Collect all matched tags for generic check
    has_exact_match = False
    
    # Custom user tags (HIGHEST PRIORITY)
    if custom_tag_data and custom_tag_data.get("tag_matches"):
        for match in custom_tag_data.get("tag_matches", []):
            if match["match_type"] == "exact":
                score += SEARCH_SCORE_WEIGHTS["custom_tag_exact"] * match["score"]
            else:
                score += SEARCH_SCORE_WEIGHTS["custom_tag_partial"] * match["score"]
    
    # ==================================================================
    # Named people matches (HIGH PRIORITY - user assigned names)
    # ==================================================================
    if person_data and person_data.get("person_matches"):
        person_score = 0.0
        for match in person_data.get("person_matches", []):
            multiplier = SEARCH_MATCH_MULTIPLIERS.get(match["match_type"], 0.25)
            person_score += match["score"] * multiplier
        
        # Apply source weight and intent boost
        person_score *= SEARCH_SOURCE_WEIGHTS["person"] * intent_boosts.get("person", 1.0)
        source_scores["person"] = person_score
        matched_sources.append("person")
        all_matched_tags.extend(person_data.get("matched_tags", []))
        
        if person_data.get("has_exact_match"):
            has_exact_match = True
    
    # Florence-2 tag matches (PRIMARY)
    # ==================================================================
    # Florence-2 tag matches (weight: 0.8)
    # ==================================================================
    if florence_data and florence_data.get("florence_matches"):
        florence_score = 0.0
        for match in florence_data.get("florence_matches", []):
            multiplier = SEARCH_MATCH_MULTIPLIERS.get(match["match_type"], 0.25)
            florence_score += match["confidence"] * multiplier
        
        # Apply source weight and intent boost
        florence_score *= SEARCH_SOURCE_WEIGHTS["florence"] * intent_boosts.get("florence", 1.0)
        source_scores["florence"] = florence_score
        matched_sources.append("florence")
        all_matched_tags.extend(florence_data.get("matched_tags", []))
        
        if florence_data.get("has_exact_match"):
            has_exact_match = True
    
    # ==================================================================
    # Location matches (weight: 0.9)
    # ==================================================================
    if location_data and location_data.get("location_matches"):
        location_score = 0.0
        for match in location_data.get("location_matches", []):
            multiplier = SEARCH_MATCH_MULTIPLIERS.get(match["match_type"], 0.25)
            location_score += match["score"] * multiplier
        
        # Apply source weight and intent boost
        location_score *= SEARCH_SOURCE_WEIGHTS["location"] * intent_boosts.get("location", 1.0)
        source_scores["location"] = location_score
        matched_sources.append("location")
        all_matched_tags.extend(location_data.get("matched_tags", []))
        
        if location_data.get("has_exact_match"):
            has_exact_match = True
    
    # ==================================================================
    # Object matches (weight: 0.6)
    # ==================================================================
    if object_data and object_data.get("object_matches"):
        object_score = 0.0
        for match in object_data.get("object_matches", []):
            object_score += match["confidence"]
        
        # Apply source weight and intent boost
        object_score *= SEARCH_SOURCE_WEIGHTS["object"] * intent_boosts.get("object", 1.0)
        source_scores["object"] = object_score
        matched_sources.append("object")
        all_matched_tags.extend(object_data.get("matched_tags", []))
    
    # ==================================================================
    # Pet matches (weight: 0.6)
    # ==================================================================
    if pet_data and pet_data.get("pet_matches"):
        pet_score = 0.0
        for match in pet_data.get("pet_matches", []):
            pet_score += match["confidence"]
        
        # Apply source weight and intent boost
        pet_score *= SEARCH_SOURCE_WEIGHTS["pet"] * intent_boosts.get("pet", 1.0)
        source_scores["pet"] = pet_score
        matched_sources.append("pet")
        all_matched_tags.extend(pet_data.get("matched_tags", []))
    
    # ==================================================================
    # CLIP similarity (weight: 0.4 - supporting only)
    # ==================================================================
    if clip_similarity > 0:
        clip_score = clip_similarity * SEARCH_SOURCE_WEIGHTS["clip"] * intent_boosts.get("clip", 1.0)
        source_scores["clip"] = clip_score
        matched_sources.append("clip")
    
    # ==================================================================
    # Combine scores with bonuses and penalties
    # ==================================================================
    
    # Base score: weighted sum of all sources
    score = sum(source_scores.values())
    
    # BONUS: Multi-signal match (more than one source agrees)
    num_tag_sources = len([s for s in matched_sources if s != "clip"])
    if num_tag_sources >= 2:
        score *= 1.3  # 30% bonus for multi-signal agreement
    elif num_tag_sources >= 3:
        score *= 1.5  # 50% bonus for 3+ sources
    
    # BONUS: Exact tag match
    if has_exact_match:
        score *= 1.2  # 20% bonus for exact match
    
    # BONUS: CLIP confirms tag match (cross-validation)
    if "clip" in matched_sources and num_tag_sources > 0:
        score *= 1.1  # 10% bonus for CLIP confirmation
    
    # PENALTY: Single weak signal only
    if len(matched_sources) == 1:
        single_source = matched_sources[0]
        if single_source == "clip":
            # CLIP-only match - heavily penalized
            score *= 0.3
        elif single_source in ["object", "pet"]:
            # Single object/pet match - moderately penalized
            score *= 0.6
    
    # PENALTY: Generic tag only match
    if all_matched_tags and is_generic_only_match(all_matched_tags):
        score *= 0.4  # 60% penalty for generic-only matches
    
    match_info = {
        "sources": matched_sources,
        "source_scores": source_scores,
        "has_exact_match": has_exact_match,
        "num_tag_sources": num_tag_sources,
        "is_generic_only": is_generic_only_match(all_matched_tags) if all_matched_tags else False,
    }
    
    return score, match_info


@router.post("", response_model=List[PhotoResponse])
async def search_photos(request: SearchRequest):
    """
    Search photos using multiple sources with intelligent scoring.
    
    Search priority (highest to lowest):
    1. Custom user tags (explicit user intent)
    2. Florence-2 rich tags (exact and partial matches)
    3. Location names (city, region, country)
    4. YOLO object detections
    5. Pet detections  
    6. CLIP semantic similarity (fallback)
    Relevance rules:
    - Hard filter: CLIP-only results must have tag overlap with query
    - Source-aware weighted scoring with intent boosts
    - Multi-signal matches ranked higher than single-signal
    - Generic tags suppressed
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
        logging.debug(f"Search query: '{query}'")
        
        # ==================================================================
        # STEP 0: Detect query intent for boosting
        # ==================================================================
        intent_boosts = detect_query_intent(query)
        logging.debug(f"Intent boosts: {intent_boosts}")
        
        # ==================================================================
        # STEP 1: Search custom user tags (HIGHEST PRIORITY)
        # ==================================================================
        custom_tag_results = search_by_custom_tags(store, query)
        logging.debug(f"Custom tag matches: {len(custom_tag_results)} photos")
        
        # ==================================================================
        # STEP 1.5: Search named people (HIGH PRIORITY)
        # ==================================================================
        person_results = search_by_people_name(store, query)
        logging.debug(f"Person name matches: {len(person_results)} photos")
        
        # ==================================================================
        # STEP 2: Search Florence-2 tags (PRIMARY SOURCE)
        # ==================================================================
        florence_results = search_by_florence_tags(store, query)
        logging.debug(f"Florence-2 matches: {len(florence_results)} photos")
        
        # ==================================================================
        # STEP 3: Search by location names
        # ==================================================================
        location_results = search_by_location(store, query)
        logging.debug(f"Location matches: {len(location_results)} photos")
        
        # ==================================================================
        # STEP 4: Search YOLO objects
        # ==================================================================
        object_results = search_by_objects(store, query)
        logging.debug(f"Object matches: {len(object_results)} photos")
        
        # ==================================================================
        # STEP 5: Search pet detections (if relevant)
        # ==================================================================
        pet_results = {}
        if any(kw in query.lower() for kw in SEARCH_PET_KEYWORDS):
            pet_results = search_by_pets(store, query)
            logging.debug(f"Pet matches: {len(pet_results)} photos")
        
        tag_candidate_ids = (
            set(custom_tag_results.keys()) |
            set(person_results.keys()) |
            set(florence_results.keys()) | 
            set(location_results.keys()) |
            set(object_results.keys()) | 
            set(pet_results.keys())
        )
        
        # ==================================================================
        # STEP 6: CLIP semantic search (supporting signal)
        # ==================================================================
        clip_results = await search_by_clip(pipeline, query, tag_candidate_ids)
        logging.debug(f"CLIP matches: {len(clip_results)} photos")
        
        # ==================================================================
        # STEP 5.5: HARD FILTER - Apply tag overlap check for CLIP-only results
        # ==================================================================
        # Filter CLIP-only results: only keep if they have tag overlap
        clip_only_ids = set(clip_results.keys()) - tag_candidate_ids
        filtered_clip_only = 0
        
        for clip_id in list(clip_only_ids):
            # For CLIP-only results, check if CLIP similarity is high enough
            # and the photo has ANY tags that overlap with query
            # Since these photos have no tag matches, we need to be strict
            clip_sim = clip_results[clip_id]
            
            # Get photo's existing tags from DB for overlap check
            # (This is a stricter check - CLIP-only must still have some relevance)
            photo_scenes = store.get_scenes_for_photo(clip_id) if hasattr(store, 'get_scenes_for_photo') else []
            photo_tags = [s.get("scene_label", "") for s in photo_scenes] if photo_scenes else []
            
            # If no tag overlap and CLIP similarity is not exceptionally high, filter out
            if not has_tag_overlap(query, photo_tags) and clip_sim < 0.35:
                del clip_results[clip_id]
                filtered_clip_only += 1
        
        logging.debug(f"Filtered {filtered_clip_only} CLIP-only results without tag overlap")
        
        # Final candidate set
        candidate_ids = tag_candidate_ids | set(clip_results.keys())
        
        # ==================================================================
        # STEP 7: Calculate scores and rank with source-aware weighting
        # ==================================================================
        scored_photos = []
        
        for photo_id in candidate_ids:
            photo = store.get_photo(photo_id)
            if not photo:
                continue
            
            custom_tag_data = custom_tag_results.get(photo_id)
            person_data = person_results.get(photo_id)
            florence_data = florence_results.get(photo_id)
            location_data = location_results.get(photo_id)
            object_data = object_results.get(photo_id)
            pet_data = pet_results.get(photo_id)
            clip_sim = clip_results.get(photo_id, 0.0)
            
            score, match_info = calculate_final_score(
                photo_id=photo_id,
                florence_data=florence_data,
                object_data=object_data,
                pet_data=pet_data,
                clip_similarity=clip_sim,
                location_data=location_data,
                custom_tag_data=custom_tag_data,
                person_data=person_data,
                intent_boosts=intent_boosts,
                query=query,
            )
            
            # Filter out very low scores
            if score < 0.05:
                continue
            
            scored_photos.append((score, photo, match_info))
            
            # Log what matched for debugging
            matches = []
            if custom_tag_data and custom_tag_data.get("tag_matches"):
                matches.append(f"custom_tags:{len(custom_tag_data['tag_matches'])}")
            if person_data and person_data.get("person_matches"):
                matches.append(f"people:{len(person_data['person_matches'])}")
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
            logging.debug(f"Photo {photo_id}: score={score:.2f} [{', '.join(matches)}]")
            sources_str = ",".join(match_info["sources"])
            logging.debug(
                f"Photo {photo_id}: score={score:.3f} "
                f"[sources:{sources_str}] "
                f"[exact:{match_info['has_exact_match']}] "
                f"[generic:{match_info['is_generic_only']}]"
            )
        
        # Sort by score (highest first)
        scored_photos.sort(key=lambda x: x[0], reverse=True)
        results = [photo for _, photo, _ in scored_photos]
        
        logging.debug(f"Returning {len(results)} ranked results")
        
        # ==================================================================
        # STEP 7: Apply filters (person, category, date)
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
