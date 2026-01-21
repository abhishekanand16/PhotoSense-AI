from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PhotoResponse(BaseModel):
    id: int
    file_path: str
    date_taken: Optional[str] = None
    camera_model: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    created_at: str


class PersonResponse(BaseModel):
    id: int
    cluster_id: Optional[int] = None
    name: Optional[str] = None
    face_count: int = 0


class ObjectResponse(BaseModel):
    id: int
    photo_id: int
    category: str
    confidence: float
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int


class CategorySummaryResponse(BaseModel):
    category: str
    photo_count: int


class SceneResponse(BaseModel):
    id: int
    photo_id: int
    scene_label: str
    confidence: float


class SceneSummaryResponse(BaseModel):
    label: str
    photo_count: int
    avg_confidence: float


class ScanRequest(BaseModel):
    folder_path: str
    recursive: bool = True


class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    phase: Optional[str] = None


class GlobalScanStatusResponse(BaseModel):
    status: str
    total_photos: int
    processed_photos: int
    progress_percent: int  # 0-100
    message: str
    current_job_id: Optional[str] = None
    started_at: Optional[str] = None
    eta_seconds: Optional[int] = None
    error: Optional[str] = None


class UpdatePersonRequest(BaseModel):
    name: str


class MergePeopleRequest(BaseModel):
    source_person_id: int
    target_person_id: int


class MergeMultiplePeopleRequest(BaseModel):
    person_ids: List[int]
    target_person_id: int
    min_confidence: float = 0.5


class SearchRequest(BaseModel):
    query: Optional[str] = None
    person_id: Optional[int] = None
    category: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None


class StatisticsResponse(BaseModel):
    total_photos: int
    total_faces: int
    total_objects: int
    total_people: int
    labeled_faces: int
    total_locations: int = 0


class PetResponse(BaseModel):
    id: int
    cluster_id: Optional[int] = None
    name: Optional[str] = None
    species: Optional[str] = None
    detection_count: int = 0


class PetDetectionResponse(BaseModel):
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
    name: str


class MergePetsRequest(BaseModel):
    source_pet_id: int
    target_pet_id: int


class SimilarPetResponse(BaseModel):
    pet_detection_id: int
    photo_id: int
    similarity: float
    species: str
    confidence: float
    pet_id: Optional[int] = None


class LocationResponse(BaseModel):
    photo_id: int
    latitude: float
    longitude: float
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class PlaceResponse(BaseModel):
    name: str
    count: int
    lat: float
    lon: float
