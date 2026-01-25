# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Dict, Set

# Windows MAX_PATH limit (260 characters) - use extended path prefix to support longer paths
WINDOWS_MAX_PATH = 260


def _ensure_long_path_support(path: Path) -> Path:
    """
    On Windows, prepend \\\\?\\ prefix for long path support if needed.
    This allows paths longer than 260 characters.
    """
    if platform.system() != "Windows":
        return path
    
    path_str = str(path.resolve())
    
    # Already has long path prefix
    if path_str.startswith("\\\\?\\"):
        return path
    
    # Only add prefix for paths approaching the limit
    if len(path_str) > WINDOWS_MAX_PATH - 50:
        return Path(f"\\\\?\\{path_str}")
    
    return path


def get_app_data_dir() -> Path:
    """
    Get the platform-specific application data directory.
    
    Returns:
    - macOS: ~/Library/Application Support/PhotoSense-AI
    - Windows: %APPDATA%/PhotoSense-AI
    - Linux: ~/.local/share/PhotoSense-AI (or $XDG_DATA_HOME/PhotoSense-AI)
    
    Can be overridden with PHOTOSENSE_DATA_DIR environment variable.
    
    Directory is created if it doesn't exist.
    """
    if env_dir := os.environ.get("PHOTOSENSE_DATA_DIR"):
        app_dir = Path(env_dir).resolve()
    else:
        system = platform.system()
        
        if system == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            # Use APPDATA with proper fallback
            appdata = os.environ.get("APPDATA")
            if appdata:
                base = Path(appdata)
            else:
                base = Path.home() / "AppData" / "Roaming"
        else:  # Linux and others
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                base = Path(xdg_data)
            else:
                base = Path.home() / ".local" / "share"
        
        app_dir = base / "PhotoSense-AI"
    
    return app_dir


APP_NAME = "PhotoSense-AI"
APP_VERSION = "1.0.0"
DB_SCHEMA_VERSION = 1

APP_DATA_DIR = get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "photosense.db"
INDICES_DIR = APP_DATA_DIR / "indices"
CACHE_DIR = APP_DATA_DIR / "cache"
LOG_DIR = APP_DATA_DIR / "logs"
STATE_DIR = APP_DATA_DIR / "state"

INDICES_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

if env_db := os.environ.get("PHOTOSENSE_DB_PATH"):
    DB_PATH = Path(env_db).resolve()
if env_indices := os.environ.get("PHOTOSENSE_INDICES_DIR"):
    INDICES_DIR = Path(env_indices).resolve()
if env_cache := os.environ.get("PHOTOSENSE_CACHE_DIR"):
    CACHE_DIR = Path(env_cache).resolve()
if env_log := os.environ.get("PHOTOSENSE_LOG_DIR"):
    LOG_DIR = Path(env_log).resolve()
if env_state := os.environ.get("PHOTOSENSE_STATE_DIR"):
    STATE_DIR = Path(env_state).resolve()

SCAN_BATCH_SIZE = 8

IMAGE_CACHE_SIZES: Dict[str, int] = {
    "face": 1024,
    "ml": 768,
    "florence": 1024,
}

SCENE_FUSION_CONFIG = {
    "max_tags": 10,
    "places365_min_confidence": 0.30,
    "clip_min_confidence": 0.40,
    "florence_min_confidence": 0.70,
    "yolo_scene_implications": {
        "animal:dog": ["outdoor"],
        "animal:cat": ["indoor"],
        "animal:bird": ["outdoor", "nature"],
        "animal:horse": ["outdoor", "nature"],
        "vehicle:car": ["outdoor", "street"],
        "vehicle:boat": ["water", "outdoor"],
        "sports:surfboard": ["beach", "water"],
        "sports:skis": ["snow", "mountain"],
        "plant:potted plant": ["indoor", "garden"],
    },
    "generic_tags_filter": {
        "outdoor", "indoor", "photo", "image", "picture", "scene",
        "view", "background", "foreground", "object", "item", "thing",
        "stuff", "area", "place", "location"
    },
}

CLUSTERING_CONFIG = {
    "min_confidence": 0.6,
    "eps": 0.5,
    "min_samples": 2,
    "keep_single_face_clusters": True,
    "exclude_low_confidence_from_clustering": True,
    "auto_recluster_threshold": 50,
}

PET_CLUSTERING_CONFIG = {
    "min_confidence": 0.4,
    "eps": 0.4,
    "min_samples": 2,
    "keep_single_detection_clusters": False,
    "auto_recluster_threshold": 20,
}

SEARCH_MIN_CONFIDENCE = {
    "florence_tag": 0.35,
    "scene_tag": 0.25,
    "object": 0.50,
    "pet": 0.45,
    "clip_similarity": 0.25,
}

SEARCH_SCORE_WEIGHTS = {
    "custom_tag_exact": 15.0,
    "custom_tag_partial": 10.0,
    "florence_exact": 10.0,
    "florence_partial": 6.0,
    "location_exact": 8.0,
    "location_partial": 5.0,
    "scene_exact": 4.0,
    "object_match": 4.0,
    "pet_match": 4.0,
    "clip_semantic": 3.0,
}

SEARCH_SOURCE_WEIGHTS = {
    "person": 1.0,
    "location": 0.9,
    "florence": 0.8,
    "object": 0.6,
    "pet": 0.6,
    "clip": 0.4,
}

SEARCH_MATCH_MULTIPLIERS = {
    "exact": 1.0,
    "partial": 0.75,
    "word": 0.5,
    "fuzzy": 0.25,
}

SEARCH_GENERIC_TAGS: Set[str] = {
    "photo", "image", "picture", "person", "people", "outdoor", "outdoors",
    "object", "thing", "nature", "scene", "view", "background", "foreground",
    "day", "daytime", "area", "place", "shot", "snapshot",
}

SEARCH_SCENE_KEYWORDS: Set[str] = {
    "sunset", "sunrise", "beach", "mountain", "forest", "ocean", "sea", "lake",
    "river", "sky", "cloud", "clouds", "snow", "rain", "night", "evening",
    "morning", "tree", "trees", "flower", "flowers", "garden", "park", "city",
    "street", "building", "architecture", "landscape", "waterfall", "desert",
    "moon", "stars", "rainbow", "aurora",
}

SEARCH_OBJECT_KEYWORDS: Set[str] = {
    "car", "bicycle", "bike", "motorcycle", "bus", "truck", "boat", "plane",
    "chair", "table", "laptop", "phone", "computer", "tv", "television",
    "book", "bottle", "cup", "glass", "bag", "umbrella", "clock", "vase",
}

SEARCH_PET_KEYWORDS: Set[str] = {
    "dog", "cat", "bird", "horse", "puppy", "kitten", "pet", "animal",
    "dogs", "cats", "birds", "horses", "puppies", "kittens", "pets", "animals",
}

SEARCH_LOCATION_INDICATORS: Set[str] = {
    "in", "at", "from", "near", "around",
}

# Person name indicators for intent detection
SEARCH_PERSON_INDICATORS: Set[str] = {
    "person", "people", "who", "name", "named",
}

# Search term synonyms for partial matching (query -> list of search terms)
# These expand the user's query to find more relevant results
SEARCH_SYNONYMS: Dict[str, list] = {
    # Moon phases - expand to common Florence-2 labels
    "moon": ["moon", "crescent moon", "full moon", "half moon", "lunar", "moonlight", "moonrise", "moonset"],
    "half moon": ["half moon", "crescent moon", "quarter moon", "gibbous moon"],
    "waxing moon": ["waxing moon", "waxing crescent", "waxing gibbous", "crescent moon"],
    "waning moon": ["waning moon", "waning crescent", "waning gibbous", "crescent moon"],
    "full moon": ["full moon", "bright moon", "moon"],
    "new moon": ["new moon", "dark moon", "moonless"],
    "crescent moon": ["crescent moon", "crescent", "waxing crescent", "waning crescent"],
    "gibbous moon": ["gibbous moon", "gibbous", "waxing gibbous", "waning gibbous"],
    
    # Weather/sky conditions
    "cloudy": ["cloudy", "clouds", "overcast", "cloud"],
    "sunny": ["sunny", "sunshine", "bright sky", "clear sky"],
    "rainy": ["rainy", "rain", "raining", "wet"],
    "stormy": ["stormy", "storm", "thunderstorm", "lightning"],
    
    # Time of day
    "golden hour": ["golden hour", "sunset", "sunrise", "golden light"],
    "blue hour": ["blue hour", "twilight", "dusk", "dawn"],
    "night": ["night", "nighttime", "night sky", "dark"],
    "evening": ["evening", "dusk", "sunset", "twilight"],
    
    # Clothing - expand to common terms Florence-2 might use
    "dress": ["dress", "gown", "frock", "outfit", "wearing dress", "long dress", "short dress"],
    "shirt": ["shirt", "blouse", "top", "t-shirt", "tee", "polo", "button-up", "wearing shirt"],
    "pants": ["pants", "trousers", "jeans", "slacks", "leggings", "wearing pants"],
    "jacket": ["jacket", "coat", "blazer", "hoodie", "sweater", "cardigan", "wearing jacket"],
    "suit": ["suit", "formal wear", "business attire", "tuxedo", "blazer", "wearing suit"],
    "skirt": ["skirt", "mini skirt", "long skirt", "wearing skirt"],
    "shorts": ["shorts", "short pants", "wearing shorts"],
    "casual": ["casual", "t-shirt", "jeans", "relaxed", "casual wear", "casual outfit"],
    "formal": ["formal", "suit", "dress", "gown", "elegant", "formal wear", "formal attire"],
    "sportswear": ["sportswear", "athletic", "gym clothes", "workout", "sports outfit"],
    "swimwear": ["swimwear", "swimsuit", "bikini", "swimming", "beach wear"],
    
    # Colors - expand to variations and shades
    "red": ["red", "crimson", "scarlet", "maroon", "burgundy", "ruby", "cherry"],
    "blue": ["blue", "navy", "azure", "cobalt", "turquoise", "cyan", "sky blue", "royal blue"],
    "green": ["green", "emerald", "olive", "lime", "teal", "mint", "forest green"],
    "yellow": ["yellow", "gold", "golden", "amber", "mustard", "lemon"],
    "black": ["black", "dark", "ebony", "charcoal", "jet black"],
    "white": ["white", "ivory", "cream", "bright", "snow white", "off-white"],
    "pink": ["pink", "rose", "magenta", "fuchsia", "salmon", "coral pink"],
    "purple": ["purple", "violet", "lavender", "plum", "magenta", "lilac"],
    "orange": ["orange", "tangerine", "coral", "peach", "apricot", "rust"],
    "brown": ["brown", "tan", "beige", "chocolate", "bronze", "caramel", "coffee"],
    "gray": ["gray", "grey", "silver", "charcoal", "slate", "ash"],
    "grey": ["gray", "grey", "silver", "charcoal", "slate", "ash"],
    
    # Combined clothing + color terms
    "red dress": ["red dress", "crimson dress", "scarlet dress", "wearing red"],
    "blue shirt": ["blue shirt", "navy shirt", "wearing blue"],
    "black suit": ["black suit", "dark suit", "formal black"],
    "white dress": ["white dress", "ivory dress", "cream dress", "wedding dress"],
}

# Clothing-related keywords for intent detection
SEARCH_CLOTHING_KEYWORDS: Set[str] = {
    "dress", "shirt", "pants", "jacket", "coat", "suit", "jeans", "skirt",
    "blouse", "sweater", "hoodie", "shorts", "top", "outfit", "clothes",
    "clothing", "attire", "casual", "formal", "wearing", "wore", "worn",
    "t-shirt", "tee", "blazer", "cardigan", "leggings", "sportswear",
    "swimwear", "swimsuit", "bikini", "uniform", "costume",
}

# Color keywords for intent detection
SEARCH_COLOR_KEYWORDS: Set[str] = {
    "red", "blue", "green", "yellow", "black", "white", "pink", "purple",
    "orange", "brown", "gray", "grey", "silver", "gold", "golden", "navy",
    "turquoise", "teal", "maroon", "burgundy", "beige", "tan", "cream",
    "coral", "violet", "lavender", "crimson", "scarlet", "colorful",
}
