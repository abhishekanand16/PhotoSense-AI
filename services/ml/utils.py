"""Utility functions for photo processing."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PIL import Image
from PIL.ExifTags import TAGS


def extract_exif_metadata(image_path: str) -> Dict[str, Optional[str]]:
    """
    Extract EXIF metadata from an image file.
    
    Returns a dictionary with:
    - date_taken: ISO format date string or None
    - camera_model: Camera make and model or None
    - width: Image width in pixels
    - height: Image height in pixels
    - file_size: File size in bytes
    """
    metadata = {
        "date_taken": None,
        "camera_model": None,
        "width": None,
        "height": None,
        "file_size": None,
    }
    
    try:
        # Get file size
        file_size = os.path.getsize(image_path)
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
            
    except Exception as e:
        # If extraction fails, return what we have (at least dimensions and file size)
        pass
    
    return metadata
