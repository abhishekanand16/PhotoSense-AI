from fastapi import APIRouter

from services.api.models import StatisticsResponse
from services.ml.storage.sqlite_store import SQLiteStore

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatisticsResponse)
async def get_statistics():
    try:
        store = SQLiteStore(readonly=True)
        stats = store.get_statistics()
        return StatisticsResponse(**stats)
    except FileNotFoundError:
        return StatisticsResponse(
            total_photos=0,
            total_faces=0,
            total_objects=0,
            total_people=0,
            labeled_faces=0,
            total_locations=0,
        )
