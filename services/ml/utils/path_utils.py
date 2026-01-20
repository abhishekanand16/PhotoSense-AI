"""Path validation helpers used across API and ML pipeline.

These functions are security-sensitive; keep semantics stable.
"""

from __future__ import annotations

from pathlib import Path


def validate_photo_path(photo_path: str) -> Path:
    """
    Validate and normalize a photo path for safety.

    Prevents:
    - Path traversal attacks (../)
    - Symlink attacks
    - Non-file paths

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid or unsafe
    """
    try:
        path = Path(photo_path)

        # Resolve to absolute path (this also normalizes .. and .)
        resolved = path.resolve()

        # Check for symlink - only allow if it points to a regular file
        if path.is_symlink():
            target = resolved
            if not target.is_file():
                raise ValueError(f"Symlink does not point to a regular file: {photo_path}")

        # Must be a file (not directory, device, etc.)
        if not resolved.is_file():
            raise ValueError(f"Path is not a regular file: {photo_path}")

        # Check path doesn't contain null bytes (security)
        if "\x00" in str(resolved):
            raise ValueError(f"Path contains null bytes: {photo_path}")

        return resolved

    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid photo path '{photo_path}': {e}")


def validate_folder_path(folder_path: str) -> Path:
    """
    Validate folder path for safety.

    Prevents:
    - Path traversal attacks
    - Non-directory paths
    - Symlinks to sensitive locations

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid or unsafe
    """
    path = Path(folder_path)
    resolved = path.resolve()

    # Must be a directory
    if not resolved.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    # Check path doesn't contain null bytes
    if "\x00" in str(resolved):
        raise ValueError(f"Path contains null bytes: {folder_path}")

    return resolved

