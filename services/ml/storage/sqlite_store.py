"""SQLite database for metadata storage."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


class SQLiteStore:
    """Manages SQLite database for photo metadata, faces, objects, and clusters."""

    def __init__(self, db_path: str = "photosense.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()

        # Photos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                date_taken TEXT,
                camera_model TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Faces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_w INTEGER NOT NULL,
                bbox_h INTEGER NOT NULL,
                confidence REAL NOT NULL,
                embedding_id INTEGER,
                cluster_id INTEGER,
                person_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id),
                FOREIGN KEY (person_id) REFERENCES people(id)
            )
        """)

        # Objects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_w INTEGER NOT NULL,
                bbox_h INTEGER NOT NULL,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id)
            )
        """)

        # People table (clusters with labels)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER,
                name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Feedback table (for learning)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id INTEGER,
                action TEXT NOT NULL,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (face_id) REFERENCES faces(id)
            )
        """)
        
        # Embeddings table (store face embeddings as blobs for retrieval)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id INTEGER UNIQUE NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (face_id) REFERENCES faces(id) ON DELETE CASCADE
            )
        """)

        # Create indexes only if the tables and columns exist
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_path ON photos(file_path)")
        except sqlite3.OperationalError:
            pass  # Index might already exist or table structure issue
        
        # Check if faces table has photo_id column before creating index
        try:
            cursor.execute("PRAGMA table_info(faces)")
            columns = [row[1] for row in cursor.fetchall()]
            if "photo_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_photo ON faces(photo_id)")
            if "person_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_person ON faces(person_id)")
            if "cluster_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_cluster ON faces(cluster_id)")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("PRAGMA table_info(objects)")
            columns = [row[1] for row in cursor.fetchall()]
            if "photo_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_objects_photo ON objects(photo_id)")
            if "category" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_objects_category ON objects(category)")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("PRAGMA table_info(embeddings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "face_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_face ON embeddings(face_id)")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    def add_photo(
        self,
        file_path: str,
        date_taken: Optional[str] = None,
        camera_model: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> Optional[int]:
        """Add a photo to the database. Returns photo_id or None if duplicate."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO photos (file_path, date_taken, camera_model, width, height, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (file_path, date_taken, camera_model, width, height, file_size),
            )
            conn.commit()
            cursor.execute("SELECT id FROM photos WHERE file_path = ?", (file_path,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_photo(self, photo_id: int) -> Optional[Dict]:
        """Get photo by ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM photos WHERE id = ?", (photo_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_photo_by_path(self, file_path: str) -> Optional[Dict]:
        """Get photo by file path."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM photos WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_photo_metadata(
        self,
        photo_id: int,
        date_taken: Optional[str] = None,
        camera_model: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        file_size: Optional[int] = None,
    ) -> None:
        """Update photo metadata. Only updates fields that are not None."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if date_taken is not None:
            updates.append("date_taken = ?")
            values.append(date_taken)
        if camera_model is not None:
            updates.append("camera_model = ?")
            values.append(camera_model)
        if width is not None:
            updates.append("width = ?")
            values.append(width)
        if height is not None:
            updates.append("height = ?")
            values.append(height)
        if file_size is not None:
            updates.append("file_size = ?")
            values.append(file_size)
        
        if updates:
            values.append(photo_id)
            query = f"UPDATE photos SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()

    def get_all_photos(self) -> List[Dict]:
        """Get all photos."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM photos ORDER BY date_taken DESC, created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_face(
        self,
        photo_id: int,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        confidence: float,
        embedding_id: Optional[int] = None,
        cluster_id: Optional[int] = None,
        person_id: Optional[int] = None,
    ) -> int:
        """Add a detected face. Returns face_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)  # Increased timeout to avoid locks
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO faces (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, embedding_id, cluster_id, person_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, embedding_id, cluster_id, person_id),
        )
        face_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return face_id

    def get_faces_for_photo(self, photo_id: int) -> List[Dict]:
        """Get all faces for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE photo_id = ?", (photo_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_face_embedding(self, face_id: int, embedding_id: int) -> None:
        """Update face with embedding ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE faces SET embedding_id = ? WHERE id = ?", (embedding_id, face_id))
        conn.commit()
        conn.close()

    def update_face_cluster(self, face_id: int, cluster_id: int) -> None:
        """Update face cluster assignment."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE faces SET cluster_id = ? WHERE id = ?", (cluster_id, face_id))
        conn.commit()
        conn.close()

    def update_face_person(self, face_id: int, person_id: Optional[int]) -> None:
        """Update face person assignment."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE faces SET person_id = ? WHERE id = ?", (person_id, face_id))
        conn.commit()
        conn.close()

    def get_faces_for_person(self, person_id: int) -> List[Dict]:
        """Get all faces for a person."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE person_id = ?", (person_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_object(
        self,
        photo_id: int,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        category: str,
        confidence: float,
    ) -> int:
        """Add a detected object. Returns object_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO objects (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, category, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, category, confidence),
        )
        object_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return object_id

    def get_objects_for_photo(self, photo_id: int) -> List[Dict]:
        """Get all objects for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM objects WHERE photo_id = ?", (photo_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_objects_by_category(self, category: str) -> List[Dict]:
        """Get all objects of a category."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM objects WHERE category = ?", (category,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_person(self, cluster_id: Optional[int] = None, name: Optional[str] = None) -> int:
        """Create a person entry. Returns person_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO people (cluster_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (cluster_id, name, now, now),
        )
        person_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return person_id

    def get_all_people(self) -> List[Dict]:
        """Get all people."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM people ORDER BY name, id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_person_name(self, person_id: int, name: str) -> None:
        """Update person name."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE people SET name = ?, updated_at = ? WHERE id = ?",
            (name, datetime.now().isoformat(), person_id),
        )
        conn.commit()
        conn.close()

    def merge_people(self, source_person_id: int, target_person_id: int) -> None:
        """Merge source person into target person."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE faces SET person_id = ? WHERE person_id = ?", (target_person_id, source_person_id))
        cursor.execute("DELETE FROM people WHERE id = ?", (source_person_id,))
        conn.commit()
        conn.close()

    def add_feedback(self, face_id: int, action: str, data: Optional[str] = None) -> int:
        """Add user feedback. Returns feedback_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (face_id, action, data) VALUES (?, ?, ?)",
            (face_id, action, data),
        )
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return feedback_id

    def delete_photo(self, photo_id: int) -> bool:
        """Delete a photo and all related data (faces, objects, feedback). Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # First, get all face IDs for this photo to delete related feedback
            cursor.execute("SELECT id FROM faces WHERE photo_id = ?", (photo_id,))
            face_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete feedback for faces of this photo
            if face_ids:
                placeholders = ','.join('?' * len(face_ids))
                cursor.execute(f"DELETE FROM feedback WHERE face_id IN ({placeholders})", face_ids)
            
            # Delete faces for this photo
            cursor.execute("DELETE FROM faces WHERE photo_id = ?", (photo_id,))
            
            # Delete objects for this photo
            cursor.execute("DELETE FROM objects WHERE photo_id = ?", (photo_id,))
            
            # Delete the photo itself
            cursor.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
            
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def get_statistics(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM photos")
        stats["total_photos"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM faces")
        stats["total_faces"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM objects")
        stats["total_objects"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM people")
        stats["total_people"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT person_id) FROM faces WHERE person_id IS NOT NULL")
        stats["labeled_faces"] = cursor.fetchone()[0]
        conn.close()
        return stats
    
    def store_embedding(self, face_id: int, embedding: np.ndarray) -> int:
        """Store face embedding. Returns embedding_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        # Convert numpy array to bytes
        embedding_bytes = embedding.tobytes()
        cursor.execute(
            "INSERT OR REPLACE INTO embeddings (face_id, embedding) VALUES (?, ?)",
            (face_id, embedding_bytes),
        )
        embedding_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return embedding_id
    
    def get_embedding(self, face_id: int) -> Optional[np.ndarray]:
        """Retrieve embedding for a face."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT embedding FROM embeddings WHERE face_id = ?", (face_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        # Convert bytes back to numpy array (512-dim float32)
        embedding = np.frombuffer(row[0], dtype=np.float32)
        return embedding
    
    def get_all_embeddings_with_faces(self) -> List[Tuple[int, np.ndarray]]:
        """Get all face embeddings with face_ids. Returns list of (face_id, embedding)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT face_id, embedding FROM embeddings")
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for face_id, embedding_bytes in rows:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            results.append((face_id, embedding))
        
        return results
    
    def delete_face(self, face_id: int) -> bool:
        """Delete a face and its embedding. Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Delete feedback for this face
            cursor.execute("DELETE FROM feedback WHERE face_id = ?", (face_id,))
            # Delete embedding
            cursor.execute("DELETE FROM embeddings WHERE face_id = ?", (face_id,))
            # Delete face
            cursor.execute("DELETE FROM faces WHERE id = ?", (face_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def delete_person(self, person_id: int) -> bool:
        """Delete a person and unassign all faces. Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Unassign faces from this person
            cursor.execute("UPDATE faces SET person_id = NULL WHERE person_id = ?", (person_id,))
            # Delete person
            cursor.execute("DELETE FROM people WHERE id = ?", (person_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def get_person(self, person_id: int) -> Optional[Dict]:
        """Get person by ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_faces_cluster(self, face_ids: List[int], cluster_id: int) -> None:
        """Batch update cluster for multiple faces."""
        if not face_ids:
            return
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(face_ids))
        cursor.execute(f"UPDATE faces SET cluster_id = ? WHERE id IN ({placeholders})", [cluster_id] + face_ids)
        conn.commit()
        conn.close()
    
    def update_faces_person(self, face_ids: List[int], person_id: Optional[int]) -> None:
        """Batch update person for multiple faces."""
        if not face_ids:
            return
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(face_ids))
        cursor.execute(f"UPDATE faces SET person_id = ? WHERE id IN ({placeholders})", [person_id] + face_ids)
        conn.commit()
        conn.close()
    
    def get_face(self, face_id: int) -> Optional[Dict]:
        """Get face by ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE id = ?", (face_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_faces_without_clusters(self) -> List[Dict]:
        """Get all faces that haven't been clustered yet."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM faces WHERE cluster_id IS NULL")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def count_faces_without_clusters(self) -> int:
        """Count faces that haven't been clustered yet."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM faces WHERE cluster_id IS NULL")
        count = cursor.fetchone()[0]
        conn.close()
        return count
