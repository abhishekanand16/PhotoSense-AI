"""
Image scanner module for PhotoSense-AI.

Recursively scans directories for image files.
"""

import os
from pathlib import Path
from typing import List, Set


# Supported image extensions
SUPPORTED_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}


def scan_directory(directory: str, recursive: bool = True) -> List[str]:
    """
    Scan a directory for image files.

    Args:
        directory: Path to directory to scan
        recursive: If True, scan subdirectories recursively

    Returns:
        List of absolute paths to image files
    """
    directory_path = Path(directory).resolve()

    if not directory_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    image_files: List[str] = []

    if recursive:
        # Recursive scan
        for ext in SUPPORTED_EXTENSIONS:
            image_files.extend(directory_path.rglob(f"*{ext}"))
    else:
        # Non-recursive scan
        for ext in SUPPORTED_EXTENSIONS:
            image_files.extend(directory_path.glob(f"*{ext}"))

    # Convert to absolute paths and sort
    image_files = sorted([str(f.absolute()) for f in image_files])

    return image_files


def is_image_file(file_path: str) -> bool:
    """
    Check if a file is a supported image format.

    Args:
        file_path: Path to file

    Returns:
        True if file is a supported image format
    """
    path = Path(file_path)
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
