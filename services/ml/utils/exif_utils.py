"""Utility functions for photo processing."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_decimal_from_dms(dms, ref) -> float:
    """Convert DMS (Degrees, Minutes, Seconds) to decimal degrees."""
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]
    
    decimal = float(degrees) + (float(minutes) / 60.0) + (float(seconds) / 3600.0)
    
    if ref in ['S', 'W']:
        decimal = -decimal
        
    return decimal


def extract_exif_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extract EXIF metadata from an image file.
    
    Returns a dictionary with:
    - date_taken: ISO format date string or None
    - camera_model: Camera make and model or None
    - width: Image width in pixels
    - height: Image height in pixels
    - file_size: File size in bytes
    - latitude: GPS latitude in decimal degrees or None
    - longitude: GPS longitude in decimal degrees or None
    """
    metadata = {
        "date_taken": None,
        "camera_model": None,
        "width": None,
        "height": None,
        "file_size": None,
        "latitude": None,
        "longitude": None,
    }
    
    try:
        # Get file size using pathlib
        file_path = Path(image_path)
        file_size = file_path.stat().st_size
        metadata["file_size"] = file_size
        
        # Open image and get dimensions
        with Image.open(image_path) as img:
            metadata["width"] = img.width
            metadata["height"] = img.height
            
            # Extract EXIF data
            exif_data = img.getexif()
            if exif_data is None:
                return metadata
            
            # Parse EXIF tags
            exif_dict = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_dict[tag] = value
            
            # Extract date taken
            # Try multiple date fields (DateTime, DateTimeOriginal, DateTimeDigitized)
            date_fields = ["DateTime", "DateTimeOriginal", "DateTimeDigitized"]
            for field in date_fields:
                if field in exif_dict and exif_dict[field]:
                    try:
                        # Parse EXIF date format: "YYYY:MM:DD HH:MM:SS"
                        date_str = exif_dict[field]
                        if isinstance(date_str, str):
                            dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                            metadata["date_taken"] = dt.isoformat()
                            break
                    except (ValueError, TypeError):
                        continue
            
            # Extract camera model
            make = exif_dict.get("Make", "")
            model = exif_dict.get("Model", "")
            if make or model:
                camera_parts = [part for part in [make, model] if part]
                metadata["camera_model"] = " ".join(camera_parts) if camera_parts else None
            
            # Extract GPS data
            try:
                # 0x8825 is the GPS IFD (Image File Directory) tag
                gps_info = img.getexif().get_ifd(0x8825)
                
                if gps_info:
                    gps_dict = {GPSTAGS.get(t, t): gps_info[t] for t in gps_info}
                    
                    if 'GPSLatitude' in gps_dict and 'GPSLatitudeRef' in gps_dict and \
                       'GPSLongitude' in gps_dict and 'GPSLongitudeRef' in gps_dict:
                        
                        lat = get_decimal_from_dms(gps_dict['GPSLatitude'], gps_dict['GPSLatitudeRef'])
                        lon = get_decimal_from_dms(gps_dict['GPSLongitude'], gps_dict['GPSLongitudeRef'])
                        
                        metadata["latitude"] = lat
                        metadata["longitude"] = lon
            except Exception:
                # GPS extraction failed, safe to ignore
                pass
            
    except Exception as e:
        # If extraction fails, return what we have (at least dimensions and file size)
        pass
    
    return metadata
