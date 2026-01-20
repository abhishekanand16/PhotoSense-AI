"""Reverse geocoding service using OpenStreetMap Nominatim API.

This module provides lazy reverse geocoding for photo locations:
- Uses free Nominatim API (no API key required)
- Rate-limited to 1 request/second per Nominatim usage policy
- Results are cached in the database
- Graceful failure handling (raw coords are always stored)
"""

import asyncio
import logging
import time
from typing import Dict, Optional

import aiohttp

# Nominatim API endpoint
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# Rate limiting: 1 request per second (Nominatim policy)
_last_request_time = 0.0
_rate_limit_lock = asyncio.Lock()

# User-Agent is required by Nominatim
USER_AGENT = "PhotoSense-AI/1.0 (Desktop Photo Management App)"


async def _rate_limit() -> None:
    """Enforce rate limiting for Nominatim API calls."""
    global _last_request_time
    
    async with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time
        
        if elapsed < 1.0:
            # Wait to respect rate limit
            wait_time = 1.0 - elapsed
            await asyncio.sleep(wait_time)
        
        _last_request_time = time.time()


async def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Optional[str]]]:
    """
    Reverse geocode coordinates to city, region, country.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        Dictionary with keys: city, region, country
        Values may be None if not found
        Returns None if geocoding completely fails
    """
    # Validate coordinates
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        logging.warning(f"Invalid coordinates: lat={lat}, lon={lon}")
        return None
    
    # Enforce rate limiting
    await _rate_limit()
    
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "zoom": 14,  # City-level detail
    }
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en",  # English results
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                NOMINATIM_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logging.warning(f"Nominatim returned status {response.status}")
                    return None
                
                data = await response.json()
                
                if "error" in data:
                    logging.warning(f"Nominatim error: {data['error']}")
                    return None
                
                address = data.get("address", {})
                
                # Extract location components with fallbacks
                result = {
                    "city": _extract_city(address),
                    "region": _extract_region(address),
                    "country": address.get("country"),
                }
                
                logging.info(f"Geocoded ({lat}, {lon}) -> {result}")
                return result
                
    except asyncio.TimeoutError:
        logging.warning(f"Nominatim timeout for ({lat}, {lon})")
        return None
    except aiohttp.ClientError as e:
        logging.warning(f"Nominatim request failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected geocoding error: {e}")
        return None


def _extract_city(address: Dict) -> Optional[str]:
    """
    Extract city name from Nominatim address with fallbacks.
    
    Nominatim may return city under different keys depending on location.
    """
    # Priority order for city-level names
    city_keys = [
        "city",
        "town",
        "village",
        "municipality",
        "suburb",
        "neighbourhood",
        "hamlet",
        "locality",
    ]
    
    for key in city_keys:
        if key in address and address[key]:
            return address[key]
    
    return None


def _extract_region(address: Dict) -> Optional[str]:
    """
    Extract region/state name from Nominatim address with fallbacks.
    """
    # Priority order for region-level names
    region_keys = [
        "state",
        "province",
        "region",
        "county",
        "state_district",
    ]
    
    for key in region_keys:
        if key in address and address[key]:
            return address[key]
    
    return None


def format_place_name(city: Optional[str], region: Optional[str], country: Optional[str]) -> str:
    """
    Format location components into a human-readable place name.
    
    Examples:
        - "Bangalore, Karnataka, India"
        - "Cubbon Park, Bangalore" (if region matches city)
        - "Unknown" (if all components are None)
    """
    parts = []
    
    if city:
        parts.append(city)
    if region and region != city:  # Avoid "Bangalore, Bangalore"
        parts.append(region)
    if country and (not region or region != country):  # Avoid "India, India"
        parts.append(country)
    
    return ", ".join(parts) if parts else "Unknown"


# Synchronous wrapper for non-async contexts
def reverse_geocode_sync(lat: float, lon: float) -> Optional[Dict[str, Optional[str]]]:
    """
    Synchronous wrapper for reverse_geocode.
    Creates an event loop if one doesn't exist.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(reverse_geocode(lat, lon))
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(reverse_geocode(lat, lon))
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(reverse_geocode(lat, lon))
