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
