"""
Database module for PhotoSense-AI.

Handles SQLite database initialization, schema creation, and data persistence.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    """SQLite database manager for PhotoSense-AI."""

    def __init__(self, db_path: str = "photosense.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialize database connection and create tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database schema if tables don't exist."""
        cursor = self.conn.cursor()

        # Images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                date_taken TEXT,
                camera_model TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Faces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                face_path TEXT,
                embedding_path TEXT,
                bbox_x INTEGER,
                bbox_y INTEGER,
                bbox_width INTEGER,
                bbox_height INTEGER,
                confidence REAL,
                person_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (image_id) REFERENCES images(id),
                FOREIGN KEY (person_id) REFERENCES people(id)
            )
        """)

        # People table (clusters)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER,
                name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def add_image(
        self,
        file_path: str,
        date_taken: Optional[str] = None,
        camera_model: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> int:
        """
        Add an image record to the database.

        Args:
            file_path: Full path to the image file
            date_taken: Date taken from EXIF (ISO format string)
            camera_model: Camera model from EXIF
            width: Image width in pixels
            height: Image height in pixels
            file_size: File size in bytes

        Returns:
            ID of the inserted image record
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO images 
            (file_path, date_taken, camera_model, width, height, file_size, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (file_path, date_taken, camera_model, width, height, file_size, now, now))

        # Get the ID (either newly inserted or existing)
        cursor.execute("SELECT id FROM images WHERE file_path = ?", (file_path,))
        result = cursor.fetchone()
        self.conn.commit()

        return result[0] if result else None

    def add_face(
        self,
        image_id: int,
        face_path: Optional[str] = None,
        embedding_path: Optional[str] = None,
        bbox_x: Optional[int] = None,
        bbox_y: Optional[int] = None,
        bbox_width: Optional[int] = None,
        bbox_height: Optional[int] = None,
        confidence: Optional[float] = None,
        person_id: Optional[int] = None,
    ) -> int:
        """
        Add a face record to the database.

        Args:
            image_id: ID of the parent image
            face_path: Path to cropped face image
            embedding_path: Path to face embedding file
            bbox_x: Bounding box x coordinate
            bbox_y: Bounding box y coordinate
            bbox_width: Bounding box width
            bbox_height: Bounding box height
            confidence: Detection confidence score
            person_id: ID of the person (cluster) this face belongs to

        Returns:
            ID of the inserted face record
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO faces 
            (image_id, face_path, embedding_path, bbox_x, bbox_y, bbox_width, bbox_height, confidence, person_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (image_id, face_path, embedding_path, bbox_x, bbox_y, bbox_width, bbox_height, confidence, person_id, now))

        face_id = cursor.lastrowid
        self.conn.commit()

        return face_id

    def add_person(self, cluster_id: int, name: Optional[str] = None) -> int:
        """
        Add a person record (cluster) to the database.

        Args:
            cluster_id: Cluster ID from DBSCAN
            name: Human-readable name for this person

        Returns:
            ID of the inserted person record
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO people (cluster_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (cluster_id, name, now, now))

        person_id = cursor.lastrowid
        self.conn.commit()

        return person_id

    def update_face_person(self, face_id: int, person_id: Optional[int]):
        """
        Update the person_id for a face record.

        Args:
            face_id: ID of the face record
            person_id: ID of the person (cluster) to assign
        """
        cursor = self.conn.cursor()
        cursor.execute("UPDATE faces SET person_id = ? WHERE id = ?", (person_id, face_id))
        self.conn.commit()

    def update_person_name(self, person_id: int, name: str):
        """
        Update the name for a person record.

        Args:
            person_id: ID of the person record
            name: New name for this person
        """
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE people SET name = ?, updated_at = ? WHERE id = ?",
            (name, now, person_id)
        )
        self.conn.commit()

    def get_all_images(self) -> List[Dict[str, Any]]:
        """Get all image records."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM images")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_faces(self) -> List[Dict[str, Any]]:
        """Get all face records."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM faces")
        return [dict(row) for row in cursor.fetchall()]

    def get_faces_without_embeddings(self) -> List[Dict[str, Any]]:
        """Get all face records that don't have embeddings yet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE embedding_path IS NULL")
        return [dict(row) for row in cursor.fetchall()]

    def get_faces_without_person(self) -> List[Dict[str, Any]]:
        """Get all face records that haven't been assigned to a person yet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE person_id IS NULL AND embedding_path IS NOT NULL")
        return [dict(row) for row in cursor.fetchall()]

    def get_all_people(self) -> List[Dict[str, Any]]:
        """Get all person records."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM people")
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
