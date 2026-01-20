"""Pydantic models for API requests/responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PhotoResponse(BaseModel):
    """Photo metadata response."""

    id: int
    file_path: str
    date_taken: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    created_at: str


class PersonResponse(BaseModel):
    """Person/cluster response."""

    id: int
    cluster_id: Optional[int] = None
    name: Optional[str] = None
    face_count: int = 0


class ObjectResponse(BaseModel):
    """Object detection response."""

    id: int
    photo_id: int
    category: str
    confidence: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int


class CategorySummaryResponse(BaseModel):
    """Summary of object categories with photo counts."""

    category: str
    photo_count: int


class SceneResponse(BaseModel):
    """Scene detection response."""

    id: int
    photo_id: int
    scene_label: str
    confidence: float


class SceneSummaryResponse(BaseModel):
    """Summary of scene labels with photo counts."""

    label: str
    photo_count: int
    avg_confidence: float


class ScanRequest(BaseModel):
    """Request to scan a folder."""

    folder_path: str
    recursive: bool = True


class ScanResponse(BaseModel):
    """Scan operation response."""

    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Background job status."""

    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    phase: Optional[str] = None  # "import", "scanning", or "complete"


class GlobalScanStatusResponse(BaseModel):
    """Global scan status for progress tracking."""

    status: str  # idle | scanning | indexing | done | paused
    total_photos: int
    scanned_photos: int
    progress_percent: int  # 0-100
    message: str
    current_job_id: Optional[str] = None


class UpdatePersonRequest(BaseModel):
    """Request to update person name."""

    name: str


class MergePeopleRequest(BaseModel):
    """Request to merge people."""

    source_person_id: int
    target_person_id: int


class MergeMultiplePeopleRequest(BaseModel):
    """Request to merge multiple people into one."""

    person_ids: List[int]  # IDs of people to merge (will be merged into target)
    target_person_id: int  # The person to merge all others into
    min_confidence: float = 0.5  # Minimum face confidence to include in merge


class SearchRequest(BaseModel):
    """Search request."""

    query: Optional[str] = None
    person_id: Optional[int] = None
    category: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None


class StatisticsResponse(BaseModel):
    """Database statistics."""

    total_photos: int
    total_faces: int
    total_objects: int
    total_people: int
    labeled_faces: int
    total_locations: int = 0


# =========================================================================
# PET MODELS (parallel to people models)
# =========================================================================

class PetResponse(BaseModel):
    """Pet identity response."""

    id: int
    cluster_id: Optional[int] = None
    name: Optional[str] = None
    species: Optional[str] = None
    detection_count: int = 0


class PetDetectionResponse(BaseModel):
    """Pet detection response."""

    id: int
    photo_id: int
    species: str
    confidence: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    pet_id: Optional[int] = None


class UpdatePetRequest(BaseModel):
    """Request to update pet name."""

    name: str


class MergePetsRequest(BaseModel):
    """Request to merge pets."""

    source_pet_id: int
    target_pet_id: int


class SimilarPetResponse(BaseModel):
    """Similar pet search result."""

    pet_detection_id: int
    photo_id: int
    similarity: float
    species: str
    confidence: float
    pet_id: Optional[int] = None


# =========================================================================
# LOCATION/PLACES MODELS
# =========================================================================

class LocationResponse(BaseModel):
    """Photo location response."""

    photo_id: int
    latitude: float
    longitude: float
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class PlaceResponse(BaseModel):
    """Place with photo count response."""

    name: str
    count: int
    lat: float
    lon: float
