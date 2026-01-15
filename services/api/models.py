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


class UpdatePersonRequest(BaseModel):
    """Request to update person name."""

    name: str


class MergePeopleRequest(BaseModel):
    """Request to merge people."""

    source_person_id: int
    target_person_id: int


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
