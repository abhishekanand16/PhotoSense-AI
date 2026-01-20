"""Places/Location API endpoints for map-based photo browsing."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.api.models import LocationResponse, PlaceResponse, PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore
from services.ml.utils.geocoder import reverse_geocode, format_place_name

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=List[PlaceResponse])
async def get_places(limit: int = Query(50, ge=1, le=200)):
    """
    Get top places with photo counts.
    
    Returns a list of places (city/region/country) sorted by photo count.
    Places without geocoded names are excluded.
    """
    store = SQLiteStore()
    try:
        places = store.get_top_places(limit=limit)
        return [
            PlaceResponse(
                name=place["name"],
                count=place["count"],
                lat=place["lat"],
                lon=place["lon"]
            )
            for place in places
            if place["name"] != "Unknown"  # Exclude ungeocode photos from top places
        ]
    except Exception as e:
        logging.error(f"Failed to get places: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/map", response_model=List[LocationResponse])
async def get_map_locations():
    """
    Get all photo locations for map display.
    
    Returns coordinates for all photos that have GPS data.
    Used to populate map markers/clusters.
    """
    store = SQLiteStore()
    try:
        locations = store.get_all_locations()
        return [
            LocationResponse(
                photo_id=loc["photo_id"],
                latitude=loc["latitude"],
                longitude=loc["longitude"],
                city=loc.get("city"),
                region=loc.get("region"),
                country=loc.get("country")
            )
            for loc in locations
        ]
    except Exception as e:
        logging.error(f"Failed to get map locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/photos", response_model=List[PhotoResponse])
async def get_photos_by_bbox(
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lon: float = Query(..., ge=-180, le=180),
):
    """
    Get photos within a geographic bounding box.
    
    Used when user clicks a map cluster or zooms to an area.
    """
    store = SQLiteStore()
    try:
        # Get photo IDs within bounding box
        photo_ids = store.get_photos_in_bbox(min_lat, max_lat, min_lon, max_lon)
        
        # Fetch full photo data
        photos = []
        for photo_id in photo_ids:
            photo = store.get_photo(photo_id)
            if photo:
                # Ensure created_at is a string
                if photo.get("created_at") and not isinstance(photo["created_at"], str):
                    photo["created_at"] = str(photo["created_at"])
                elif not photo.get("created_at"):
                    photo["created_at"] = ""
                photos.append(photo)
        
        # Sort by date taken (most recent first)
        photos.sort(key=lambda p: p.get("date_taken") or "", reverse=True)
        
        return photos
    except Exception as e:
        logging.error(f"Failed to get photos by bbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-name/{place_name}", response_model=List[PhotoResponse])
async def get_photos_by_place_name(place_name: str):
    """
    Get photos by place name (city, region, or country).
    
    Searches for exact and partial matches in geocoded location data.
    """
    store = SQLiteStore()
    try:
        photos = store.get_photos_by_place_name(place_name)
        return photos
    except Exception as e:
        logging.error(f"Failed to get photos by place name: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unknown", response_model=List[PhotoResponse])
async def get_photos_without_location():
    """
    Get photos without GPS location data.
    
    Returns photos in the "Unknown location" bucket.
    """
    store = SQLiteStore()
    try:
        # Get all photos
        all_photos = store.get_all_photos()
        
        # Get photos with location
        locations = store.get_all_locations()
        photo_ids_with_location = {loc["photo_id"] for loc in locations}
        
        # Filter to photos without location
        photos_without_location = [
            photo for photo in all_photos
            if photo["id"] not in photo_ids_with_location
        ]
        
        return photos_without_location
    except Exception as e:
        logging.error(f"Failed to get photos without location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/geocode/{photo_id}", response_model=LocationResponse)
async def geocode_photo(photo_id: int):
    """
    Lazy geocode a single photo's location.
    
    Triggers reverse geocoding for a photo that has GPS coordinates
    but hasn't been geocoded yet. This is called when viewing photo details.
    """
    store = SQLiteStore()
    try:
        # Get existing location
        location = store.get_location(photo_id)
        
        if not location:
            raise HTTPException(
                status_code=404,
                detail="Photo has no GPS coordinates"
            )
        
        # Check if already geocoded
        if location.get("city") or location.get("region") or location.get("country"):
            # Already geocoded, return existing data
            return LocationResponse(
                photo_id=photo_id,
                latitude=location["latitude"],
                longitude=location["longitude"],
                city=location.get("city"),
                region=location.get("region"),
                country=location.get("country")
            )
        
        # Perform reverse geocoding
        geocode_result = await reverse_geocode(
            location["latitude"],
            location["longitude"]
        )
        
        if geocode_result:
            # Update database with geocoded info
            store.update_location_geocode(
                photo_id=photo_id,
                city=geocode_result.get("city"),
                region=geocode_result.get("region"),
                country=geocode_result.get("country")
            )
            
            return LocationResponse(
                photo_id=photo_id,
                latitude=location["latitude"],
                longitude=location["longitude"],
                city=geocode_result.get("city"),
                region=geocode_result.get("region"),
                country=geocode_result.get("country")
            )
        else:
            # Geocoding failed, return raw coordinates
            return LocationResponse(
                photo_id=photo_id,
                latitude=location["latitude"],
                longitude=location["longitude"],
                city=None,
                region=None,
                country=None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to geocode photo {photo_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_location_stats():
    """
    Get location statistics.
    
    Returns counts of photos with/without location data.
    """
    store = SQLiteStore()
    try:
        all_photos = store.get_all_photos()
        locations = store.get_all_locations()
        
        # Count geocoded vs non-geocoded
        geocoded_count = sum(
            1 for loc in locations
            if loc.get("city") or loc.get("region") or loc.get("country")
        )
        
        return {
            "total_photos": len(all_photos),
            "photos_with_location": len(locations),
            "photos_without_location": len(all_photos) - len(locations),
            "geocoded": geocoded_count,
            "not_geocoded": len(locations) - geocoded_count,
        }
    except Exception as e:
        logging.error(f"Failed to get location stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional endpoint under /photos for getting single photo location
# This is registered in photos.py but defined here for organization
async def get_photo_location(photo_id: int) -> Optional[LocationResponse]:
    """
    Get location for a specific photo.
    
    Called from photo detail view. Triggers lazy geocoding if needed.
    """
    store = SQLiteStore()
    location = store.get_location(photo_id)
    
    if not location:
        return None
    
    # If not geocoded, trigger geocoding
    if not (location.get("city") or location.get("region") or location.get("country")):
        geocode_result = await reverse_geocode(
            location["latitude"],
            location["longitude"]
        )
        
        if geocode_result:
            store.update_location_geocode(
                photo_id=photo_id,
                city=geocode_result.get("city"),
                region=geocode_result.get("region"),
                country=geocode_result.get("country")
            )
            location.update(geocode_result)
    
    return LocationResponse(
        photo_id=photo_id,
        latitude=location["latitude"],
        longitude=location["longitude"],
        city=location.get("city"),
        region=location.get("region"),
        country=location.get("country")
    )
