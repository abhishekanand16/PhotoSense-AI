"""
Metadata extraction module for PhotoSense-AI.

Extracts EXIF and image metadata using Pillow.
"""

from PIL import Image
from PIL.ExifTags import TAGS
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def extract_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extract metadata from an image file.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary containing:
            - date_taken: ISO format date string or None
            - camera_model: Camera model string or None
            - width: Image width in pixels
            - height: Image height in pixels
            - file_size: File size in bytes
    """
    metadata = {
        'date_taken': None,
        'camera_model': None,
        'width': None,
        'height': None,
        'file_size': None,
    }

    try:
        path = Path(image_path)
        metadata['file_size'] = path.stat().st_size

        with Image.open(image_path) as img:
            # Get basic image dimensions
            metadata['width'], metadata['height'] = img.size

            # Try to extract EXIF data
            exif_data = img._getexif()

            if exif_data is not None:
                # Process EXIF tags
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)

                    # Extract date taken
                    if tag == 'DateTimeOriginal' or tag == 'DateTime':
                        try:
                            # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                            dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                            metadata['date_taken'] = dt.isoformat()
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse date from {image_path}: {value}")

                    # Extract camera model
                    if tag == 'Model':
                        metadata['camera_model'] = str(value).strip()

                    # Handle orientation (for future use)
                    if tag == 'Orientation':
                        # Could be used to auto-rotate images
                        pass

    except Exception as e:
        logger.error(f"Error extracting metadata from {image_path}: {e}")
        # Return partial metadata if available
        pass

    return metadata


def get_image_dimensions(image_path: str) -> tuple[Optional[int], Optional[int]]:
    """
    Get image dimensions without loading full EXIF data.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (width, height) or (None, None) on error
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Error getting dimensions from {image_path}: {e}")
        return None, None
