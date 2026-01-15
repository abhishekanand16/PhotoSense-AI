"""
Search module for PhotoSense-AI.

Provides search functionality for images by person, date, and camera model.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.db.database import Database

logger = logging.getLogger(__name__)


class ImageSearcher:
    """Image search functionality."""

    def __init__(self, db_path: str = "photosense.db"):
        """
        Initialize searcher with database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = Database(db_path)

    def search_by_person(self, person_name: str) -> List[Dict[str, Any]]:
        """
        Search images by person name.

        Args:
            person_name: Name of the person to search for

        Returns:
            List of image records containing this person
        """
        cursor = self.db.conn.cursor()

        # Search for person by name (case-insensitive)
        cursor.execute("""
            SELECT DISTINCT i.*
            FROM images i
            INNER JOIN faces f ON i.id = f.image_id
            INNER JOIN people p ON f.person_id = p.id
            WHERE LOWER(p.name) LIKE LOWER(?)
        """, (f"%{person_name}%",))

        results = [dict(row) for row in cursor.fetchall()]
        return results

    def search_by_date(
        self,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search images by date.

        Args:
            date: Exact date (YYYY-MM-DD)
            start_date: Start date for range search (YYYY-MM-DD)
            end_date: End date for range search (YYYY-MM-DD)

        Returns:
            List of image records matching the date criteria
        """
        cursor = self.db.conn.cursor()

        if date:
            # Exact date match
            cursor.execute("""
                SELECT * FROM images
                WHERE date_taken LIKE ?
            """, (f"{date}%",))
        elif start_date and end_date:
            # Date range
            cursor.execute("""
                SELECT * FROM images
                WHERE date_taken >= ? AND date_taken <= ?
                ORDER BY date_taken
            """, (start_date, end_date))
        elif start_date:
            # From start date onwards
            cursor.execute("""
                SELECT * FROM images
                WHERE date_taken >= ?
                ORDER BY date_taken
            """, (start_date,))
        elif end_date:
            # Up to end date
            cursor.execute("""
                SELECT * FROM images
                WHERE date_taken <= ?
                ORDER BY date_taken
            """, (end_date,))
        else:
            # No date criteria - return all
            cursor.execute("SELECT * FROM images ORDER BY date_taken")

        results = [dict(row) for row in cursor.fetchall()]
        return results

    def search_by_camera(self, camera_model: str) -> List[Dict[str, Any]]:
        """
        Search images by camera model.

        Args:
            camera_model: Camera model to search for (partial match)

        Returns:
            List of image records from this camera
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT * FROM images
            WHERE LOWER(camera_model) LIKE LOWER(?)
            ORDER BY date_taken
        """, (f"%{camera_model}%",))

        results = [dict(row) for row in cursor.fetchall()]
        return results

    def search_combined(
        self,
        person_name: Optional[str] = None,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        camera_model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search images with multiple criteria.

        Args:
            person_name: Person name filter
            date: Exact date filter
            start_date: Start date for range
            end_date: End date for range
            camera_model: Camera model filter

        Returns:
            List of image records matching all criteria
        """
        cursor = self.db.conn.cursor()

        # Build query dynamically based on provided filters
        query = "SELECT DISTINCT i.* FROM images i"
        conditions = []
        params = []

        # Join with faces/people if person filter is provided
        if person_name:
            query += " INNER JOIN faces f ON i.id = f.image_id INNER JOIN people p ON f.person_id = p.id"
            conditions.append("LOWER(p.name) LIKE LOWER(?)")
            params.append(f"%{person_name}%")

        # Add date conditions
        if date:
            conditions.append("i.date_taken LIKE ?")
            params.append(f"{date}%")
        elif start_date and end_date:
            conditions.append("i.date_taken >= ? AND i.date_taken <= ?")
            params.extend([start_date, end_date])
        elif start_date:
            conditions.append("i.date_taken >= ?")
            params.append(start_date)
        elif end_date:
            conditions.append("i.date_taken <= ?")
            params.append(end_date)

        # Add camera condition
        if camera_model:
            conditions.append("LOWER(i.camera_model) LIKE LOWER(?)")
            params.append(f"%{camera_model}%")

        # Combine conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY i.date_taken"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results

    def get_images_for_person(self, person_id: int) -> List[Dict[str, Any]]:
        """
        Get all images containing a specific person.

        Args:
            person_id: ID of the person

        Returns:
            List of image records
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT DISTINCT i.*
            FROM images i
            INNER JOIN faces f ON i.id = f.image_id
            WHERE f.person_id = ?
            ORDER BY i.date_taken
        """, (person_id,))

        results = [dict(row) for row in cursor.fetchall()]
        return results

    def get_faces_for_person(self, person_id: int) -> List[Dict[str, Any]]:
        """
        Get all faces for a specific person.

        Args:
            person_id: ID of the person

        Returns:
            List of face records
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            SELECT f.*, i.file_path as image_path
            FROM faces f
            INNER JOIN images i ON f.image_id = i.id
            WHERE f.person_id = ?
        """, (person_id,))

        results = [dict(row) for row in cursor.fetchall()]
        return results

    def close(self):
        """Close database connection."""
        self.db.close()
