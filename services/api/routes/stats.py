"""Statistics endpoints."""

from fastapi import APIRouter

from services.api.models import StatisticsResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatisticsResponse)
async def get_statistics():
    """Get database statistics."""
    store = SQLiteStore()
    stats = store.get_statistics()
    return StatisticsResponse(**stats)
