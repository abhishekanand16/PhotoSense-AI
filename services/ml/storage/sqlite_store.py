"""SQLite database for metadata storage."""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


class SQLiteStore:
    """Manages SQLite database for photo metadata, faces, objects, and clusters."""

    # Class-level lock for write serialization
    _write_lock = threading.Lock()

    def __init__(self, db_path: str = "photosense.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _get_connection(self, readonly: bool = False):
        """Context manager for database connections with WAL mode."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        if readonly:
            conn.execute("PRAGMA query_only=ON")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _transaction(self):
        """Context manager for write transactions with locking."""
        with self._write_lock:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_schema(self) -> None:
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
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
        
        # Scenes table (store scene detection results)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                scene_label TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)

        # Locations table (store GPS and geocoded info)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photo_locations (
                photo_id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                city TEXT,
                region TEXT,
                country TEXT,
                has_location BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)

        # =====================================================================
        # PET IDENTITY TABLES (for pet recognition & grouping similar to faces)
        # =====================================================================
        
        # Pets table (like people - stores unique pet identities)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER,
                name TEXT,
                species TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pet detections table (like faces - stores individual pet detections)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pet_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                bbox_x INTEGER NOT NULL,
                bbox_y INTEGER NOT NULL,
                bbox_w INTEGER NOT NULL,
                bbox_h INTEGER NOT NULL,
                species TEXT NOT NULL,
                confidence REAL NOT NULL,
                embedding_id INTEGER,
                cluster_id INTEGER,
                pet_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
                FOREIGN KEY (pet_id) REFERENCES pets(id)
            )
        """)
        
        # Pet embeddings table (stores CLIP embeddings for pet identity)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pet_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pet_detection_id INTEGER UNIQUE NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pet_detection_id) REFERENCES pet_detections(id) ON DELETE CASCADE
            )
        """)

        # =====================================================================
        # CUSTOM USER TAGS TABLE
        # =====================================================================
        
        # Photo tags table (user-created custom tags)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photo_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
                UNIQUE(photo_id, tag)
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
        
        try:
            cursor.execute("PRAGMA table_info(scenes)")
            columns = [row[1] for row in cursor.fetchall()]
            if "photo_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_photo ON scenes(photo_id)")
            if "scene_label" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenes_label ON scenes(scene_label)")
        except sqlite3.OperationalError:
            pass

        # Pet-related indexes
        try:
            cursor.execute("PRAGMA table_info(pet_detections)")
            columns = [row[1] for row in cursor.fetchall()]
            if "photo_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pet_detections_photo ON pet_detections(photo_id)")
            if "pet_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pet_detections_pet ON pet_detections(pet_id)")
            if "cluster_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pet_detections_cluster ON pet_detections(cluster_id)")
            if "species" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pet_detections_species ON pet_detections(species)")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("PRAGMA table_info(pet_embeddings)")
            columns = [row[1] for row in cursor.fetchall()]
            if "pet_detection_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pet_embeddings_detection ON pet_embeddings(pet_detection_id)")
        except sqlite3.OperationalError:
            pass

        # Location-related indexes
        try:
            cursor.execute("PRAGMA table_info(photo_locations)")
            columns = [row[1] for row in cursor.fetchall()]
            if "latitude" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_lat ON photo_locations(latitude)")
            if "longitude" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_lon ON photo_locations(longitude)")
            if "city" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_city ON photo_locations(city)")
            if "country" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_country ON photo_locations(country)")
        except sqlite3.OperationalError:
            pass

        # Photo tags indexes
        try:
            cursor.execute("PRAGMA table_info(photo_tags)")
            columns = [row[1] for row in cursor.fetchall()]
            if "photo_id" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_photo_tags_photo ON photo_tags(photo_id)")
            if "tag" in columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_photo_tags_tag ON photo_tags(tag)")
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

    def add_face_with_embedding(
        self,
        photo_id: int,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        confidence: float,
        embedding: np.ndarray,
        cluster_id: Optional[int] = None,
        person_id: Optional[int] = None,
    ) -> int:
        """Add face and embedding atomically in single transaction. Returns face_id."""
        with self._transaction() as conn:
            cursor = conn.cursor()
            # 1. Insert face
            cursor.execute(
                """
                INSERT INTO faces (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, cluster_id, person_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, cluster_id, person_id),
            )
            face_id = cursor.lastrowid
            
            # 2. Store embedding
            embedding_bytes = embedding.tobytes()
            cursor.execute(
                "INSERT INTO embeddings (face_id, embedding) VALUES (?, ?)",
                (face_id, embedding_bytes),
            )
            embedding_id = cursor.lastrowid
            
            # 3. Update face with embedding_id reference
            cursor.execute("UPDATE faces SET embedding_id = ? WHERE id = ?", (embedding_id, face_id))
            
            return face_id

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
        """Get all objects of a category (exact match)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM objects WHERE category = ?", (category,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_objects_by_pattern(self, pattern: str) -> List[Dict]:
        """Get all objects matching a category pattern (LIKE search)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM objects WHERE category LIKE ?",
            (f"%{pattern}%",)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_scene(self, photo_id: int, scene_label: str, confidence: float) -> int:
        """Add a detected scene. Returns scene_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scenes (photo_id, scene_label, confidence)
            VALUES (?, ?, ?)
            """,
            (photo_id, scene_label, confidence),
        )
        scene_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return scene_id

    def get_scenes_for_photo(self, photo_id: int) -> List[Dict]:
        """Get all scenes for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM scenes WHERE photo_id = ? ORDER BY confidence DESC",
            (photo_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_photos_by_scene(self, scene_label: str) -> List[int]:
        """Get all photo IDs containing a specific scene."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT photo_id FROM scenes WHERE scene_label = ?",
            (scene_label,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def search_scenes_by_text(self, query: str, min_confidence: float = 0.5) -> List[Dict]:
        """
        Search scenes table using text matching (finds Florence-2 rich tags).
        
        This is the PRIMARY method for utilizing Florence-2 tags.
        Florence-2 generates descriptive tags like "crescent moon", "palm tree silhouette",
        "golden sunset over ocean" - this method finds them.
        
        Args:
            query: Search term (e.g., "moon" matches "crescent moon", "full moon")
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of dicts with photo_id, scene_label, confidence
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Split query into words for better matching
        words = query.lower().strip().split()
        
        if len(words) == 1:
            # Single word - use LIKE for partial match
            cursor.execute(
                """
                SELECT DISTINCT photo_id, scene_label, confidence 
                FROM scenes 
                WHERE LOWER(scene_label) LIKE ? AND confidence >= ?
                ORDER BY confidence DESC
                """,
                (f"%{words[0]}%", min_confidence)
            )
        else:
            # Multiple words - match any word
            placeholders = " OR ".join(["LOWER(scene_label) LIKE ?" for _ in words])
            params = [f"%{word}%" for word in words] + [min_confidence]
            cursor.execute(
                f"""
                SELECT DISTINCT photo_id, scene_label, confidence 
                FROM scenes 
                WHERE ({placeholders}) AND confidence >= ?
                ORDER BY confidence DESC
                """,
                params
            )
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_scene_labels(self) -> List[str]:
        """Get all unique scene labels."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT scene_label FROM scenes ORDER BY scene_label")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_scene_label_stats(self, prefix: Optional[str] = None) -> List[Dict]:
        """Get scene label stats with photo counts and average confidence."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        params = []
        query = """
            SELECT scene_label,
                   COUNT(DISTINCT photo_id) AS photo_count,
                   AVG(confidence) AS avg_confidence
            FROM scenes
        """

        if prefix:
            query += " WHERE scene_label LIKE ?"
            params.append(f"{prefix}%")

        query += " GROUP BY scene_label ORDER BY photo_count DESC, scene_label"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "label": row[0],
                "photo_count": row[1],
                "avg_confidence": float(row[2] or 0.0),
            }
            for row in rows
        ]

    def delete_scenes_for_photo(self, photo_id: int) -> None:
        """Delete all scenes for a photo (e.g., before re-detecting)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scenes WHERE photo_id = ?", (photo_id,))
        conn.commit()
        conn.close()

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
    
    def get_person_by_cluster_id(self, cluster_id: int) -> Optional[Dict]:
        """Get a person by cluster_id. Returns None if not found."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM people WHERE cluster_id = ? LIMIT 1", (cluster_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

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
        # Exclude 'person' and 'other' categories from objects count
        # 'person' is handled in People tab, 'other' is too generic to be useful
        cursor.execute("SELECT COUNT(*) FROM objects WHERE category NOT IN ('person', 'other')")
        stats["total_objects"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM people")
        stats["total_people"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT person_id) FROM faces WHERE person_id IS NOT NULL")
        stats["labeled_faces"] = cursor.fetchone()[0]
        # Count photos with GPS location data
        try:
            cursor.execute("SELECT COUNT(*) FROM photo_locations WHERE has_location = 1")
            stats["total_locations"] = cursor.fetchone()[0]
        except Exception:
            stats["total_locations"] = 0
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

    # =========================================================================
    # PET IDENTITY METHODS (parallel to face/people methods)
    # =========================================================================

    def add_pet_detection_with_embedding(
        self,
        photo_id: int,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        species: str,
        confidence: float,
        embedding: np.ndarray,
        cluster_id: Optional[int] = None,
        pet_id: Optional[int] = None,
    ) -> int:
        """Add pet detection and embedding atomically in single transaction. Returns pet_detection_id."""
        with self._transaction() as conn:
            cursor = conn.cursor()
            # 1. Insert pet detection
            cursor.execute(
                """
                INSERT INTO pet_detections (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, species, confidence, cluster_id, pet_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, species, confidence, cluster_id, pet_id),
            )
            pet_detection_id = cursor.lastrowid
            
            # 2. Store embedding
            embedding_bytes = embedding.tobytes()
            cursor.execute(
                "INSERT INTO pet_embeddings (pet_detection_id, embedding) VALUES (?, ?)",
                (pet_detection_id, embedding_bytes),
            )
            embedding_id = cursor.lastrowid
            
            # 3. Update detection with embedding_id reference
            cursor.execute("UPDATE pet_detections SET embedding_id = ? WHERE id = ?", (embedding_id, pet_detection_id))
            
            return pet_detection_id

    def add_pet_detection(
        self,
        photo_id: int,
        bbox_x: int,
        bbox_y: int,
        bbox_w: int,
        bbox_h: int,
        species: str,
        confidence: float,
        embedding_id: Optional[int] = None,
        cluster_id: Optional[int] = None,
        pet_id: Optional[int] = None,
    ) -> int:
        """Add a detected pet. Returns pet_detection_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pet_detections (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, species, confidence, embedding_id, cluster_id, pet_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (photo_id, bbox_x, bbox_y, bbox_w, bbox_h, species, confidence, embedding_id, cluster_id, pet_id),
        )
        pet_detection_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return pet_detection_id

    def get_pet_detections_for_photo(self, photo_id: int) -> List[Dict]:
        """Get all pet detections for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pet_detections WHERE photo_id = ?", (photo_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_pet_detection(self, pet_detection_id: int) -> Optional[Dict]:
        """Get pet detection by ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pet_detections WHERE id = ?", (pet_detection_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_pet_detection_embedding(self, pet_detection_id: int, embedding_id: int) -> None:
        """Update pet detection with embedding ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE pet_detections SET embedding_id = ? WHERE id = ?", (embedding_id, pet_detection_id))
        conn.commit()
        conn.close()

    def update_pet_detection_cluster(self, pet_detection_id: int, cluster_id: Optional[int]) -> None:
        """Update pet detection cluster assignment."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE pet_detections SET cluster_id = ? WHERE id = ?", (cluster_id, pet_detection_id))
        conn.commit()
        conn.close()

    def update_pet_detection_pet(self, pet_detection_id: int, pet_id: Optional[int]) -> None:
        """Update pet detection pet assignment."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE pet_detections SET pet_id = ? WHERE id = ?", (pet_id, pet_detection_id))
        conn.commit()
        conn.close()

    def get_pet_detections_for_pet(self, pet_id: int) -> List[Dict]:
        """Get all pet detections for a pet identity."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pet_detections WHERE pet_id = ?", (pet_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_pet_detections_by_species(self, species: str) -> List[Dict]:
        """Get all pet detections of a species."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pet_detections WHERE species = ?", (species,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def store_pet_embedding(self, pet_detection_id: int, embedding: np.ndarray) -> int:
        """Store pet embedding (CLIP 768-dim). Returns embedding_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        embedding_bytes = embedding.tobytes()
        cursor.execute(
            "INSERT OR REPLACE INTO pet_embeddings (pet_detection_id, embedding) VALUES (?, ?)",
            (pet_detection_id, embedding_bytes),
        )
        embedding_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return embedding_id

    def get_pet_embedding(self, pet_detection_id: int) -> Optional[np.ndarray]:
        """Retrieve embedding for a pet detection."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT embedding FROM pet_embeddings WHERE pet_detection_id = ?", (pet_detection_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        # Convert bytes back to numpy array (768-dim float32 for CLIP)
        embedding = np.frombuffer(row[0], dtype=np.float32)
        return embedding

    def get_all_pet_embeddings_with_detections(self) -> List[Tuple[int, np.ndarray]]:
        """Get all pet embeddings with pet_detection_ids. Returns list of (pet_detection_id, embedding)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT pet_detection_id, embedding FROM pet_embeddings")
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for pet_detection_id, embedding_bytes in rows:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            results.append((pet_detection_id, embedding))
        
        return results

    def create_pet(self, cluster_id: Optional[int] = None, name: Optional[str] = None, species: Optional[str] = None) -> int:
        """Create a pet identity entry. Returns pet_id."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO pets (cluster_id, name, species, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (cluster_id, name, species, now, now),
        )
        pet_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return pet_id

    def get_pet(self, pet_id: int) -> Optional[Dict]:
        """Get pet by ID."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pets WHERE id = ?", (pet_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_pet_by_cluster_id(self, cluster_id: int) -> Optional[Dict]:
        """Get a pet by cluster_id. Returns None if not found."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pets WHERE cluster_id = ? LIMIT 1", (cluster_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_pets(self) -> List[Dict]:
        """Get all pets."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pets ORDER BY name, id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_pet_name(self, pet_id: int, name: str) -> None:
        """Update pet name."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pets SET name = ?, updated_at = ? WHERE id = ?",
            (name, datetime.now().isoformat(), pet_id),
        )
        conn.commit()
        conn.close()

    def update_pet_species(self, pet_id: int, species: str) -> None:
        """Update pet species."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pets SET species = ?, updated_at = ? WHERE id = ?",
            (species, datetime.now().isoformat(), pet_id),
        )
        conn.commit()
        conn.close()

    def merge_pets(self, source_pet_id: int, target_pet_id: int) -> None:
        """Merge source pet into target pet."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("UPDATE pet_detections SET pet_id = ? WHERE pet_id = ?", (target_pet_id, source_pet_id))
        cursor.execute("DELETE FROM pets WHERE id = ?", (source_pet_id,))
        conn.commit()
        conn.close()

    def delete_pet(self, pet_id: int) -> bool:
        """Delete a pet and unassign all detections. Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE pet_detections SET pet_id = NULL WHERE pet_id = ?", (pet_id,))
            cursor.execute("DELETE FROM pets WHERE id = ?", (pet_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def delete_pet_detection(self, pet_detection_id: int) -> bool:
        """Delete a pet detection and its embedding. Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM pet_embeddings WHERE pet_detection_id = ?", (pet_detection_id,))
            cursor.execute("DELETE FROM pet_detections WHERE id = ?", (pet_detection_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def get_pet_detections_without_clusters(self) -> List[Dict]:
        """Get all pet detections that haven't been clustered yet."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pet_detections WHERE cluster_id IS NULL")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def count_pet_detections_without_clusters(self) -> int:
        """Count pet detections that haven't been clustered yet."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pet_detections WHERE cluster_id IS NULL")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_pet_detections_cluster(self, pet_detection_ids: List[int], cluster_id: Optional[int]) -> None:
        """Batch update cluster for multiple pet detections."""
        if not pet_detection_ids:
            return
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(pet_detection_ids))
        cursor.execute(f"UPDATE pet_detections SET cluster_id = ? WHERE id IN ({placeholders})", [cluster_id] + pet_detection_ids)
        conn.commit()
        conn.close()

    def update_pet_detections_pet(self, pet_detection_ids: List[int], pet_id: Optional[int]) -> None:
        """Batch update pet for multiple pet detections."""
        if not pet_detection_ids:
            return
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(pet_detection_ids))
        cursor.execute(f"UPDATE pet_detections SET pet_id = ? WHERE id IN ({placeholders})", [pet_id] + pet_detection_ids)
        conn.commit()
        conn.close()

    def get_photos_with_pets(self) -> List[int]:
        """Get all photo IDs that contain pet detections."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT photo_id FROM pet_detections")
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_pet_statistics(self) -> Dict:
        """Get pet-related statistics."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM pets")
        stats["total_pets"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pet_detections")
        stats["total_pet_detections"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT pet_id) FROM pet_detections WHERE pet_id IS NOT NULL")
        stats["assigned_pet_detections"] = cursor.fetchone()[0]
        cursor.execute("SELECT species, COUNT(*) FROM pet_detections GROUP BY species")
        stats["species_counts"] = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return stats

    # =========================================================================
    # LOCATION & PLACES METHODS
    # =========================================================================

    def add_location(
        self,
        photo_id: int,
        latitude: float,
        longitude: float,
        city: Optional[str] = None,
        region: Optional[str] = None,
        country: Optional[str] = None,
    ) -> None:
        """Add or update location for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO photo_locations (photo_id, latitude, longitude, city, region, country, has_location)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (photo_id, latitude, longitude, city, region, country),
        )
        conn.commit()
        conn.close()

    def get_location(self, photo_id: int) -> Optional[Dict]:
        """Get location for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM photo_locations WHERE photo_id = ?", (photo_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_location_geocode(
        self,
        photo_id: int,
        city: Optional[str],
        region: Optional[str],
        country: Optional[str],
    ) -> None:
        """Update geocoded info for a photo location."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE photo_locations 
            SET city = ?, region = ?, country = ? 
            WHERE photo_id = ?
            """,
            (city, region, country, photo_id),
        )
        conn.commit()
        conn.close()

    def get_all_locations(self) -> List[Dict]:
        """Get all photos with locations (for map clustering)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT photo_id, latitude, longitude, city, region, country 
            FROM photo_locations 
            WHERE has_location = 1
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_top_places(self, limit: int = 50) -> List[Dict]:
        """Get list of top places with photo counts."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Group by available location hierarchy (City > Region > Country)
        # We'll return distinct places. This is a heuristic grouping.
        # Prioritize City, then Region, then Country.
        cursor.execute(
            """
            SELECT 
                COALESCE(city, region, country, 'Unknown') as name,
                COUNT(*) as count,
                AVG(latitude) as lat,
                AVG(longitude) as lon
            FROM photo_locations 
            WHERE has_location = 1
            GROUP BY COALESCE(city, region, country, 'Unknown')
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_photos_in_bbox(self, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> List[int]:
        """Get photos within a bounding box."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT photo_id 
            FROM photo_locations 
            WHERE latitude BETWEEN ? AND ? 
            AND longitude BETWEEN ? AND ?
            """,
            (min_lat, max_lat, min_lon, max_lon),
        )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_photos_by_place_name(self, place_name: str) -> List[Dict]:
        """Get photos matching a place name (city, region, or country)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Search for exact match or partial match in city, region, country
        place_pattern = f"%{place_name}%"
        cursor.execute(
            """
            SELECT p.* FROM photos p
            INNER JOIN photo_locations pl ON p.id = pl.photo_id
            WHERE pl.city LIKE ? OR pl.region LIKE ? OR pl.country LIKE ?
            ORDER BY p.date_taken DESC, p.created_at DESC
            """,
            (place_pattern, place_pattern, place_pattern),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_locations_by_text(self, query: str) -> List[Dict]:
        """Search locations table by text matching (finds photos by place name)."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Split query into words for better matching
        words = query.lower().strip().split()
        
        if len(words) == 1:
            # Single word - use LIKE for partial match
            pattern = f"%{words[0]}%"
            cursor.execute(
                """
                SELECT photo_id, city, region, country, latitude, longitude 
                FROM photo_locations 
                WHERE LOWER(city) LIKE ? OR LOWER(region) LIKE ? OR LOWER(country) LIKE ?
                """,
                (pattern, pattern, pattern)
            )
        else:
            # Multiple words - match any word
            conditions = []
            params = []
            for word in words:
                pattern = f"%{word}%"
                conditions.append("(LOWER(city) LIKE ? OR LOWER(region) LIKE ? OR LOWER(country) LIKE ?)")
                params.extend([pattern, pattern, pattern])
            
            cursor.execute(
                f"""
                SELECT photo_id, city, region, country, latitude, longitude 
                FROM photo_locations 
                WHERE {' OR '.join(conditions)}
                """,
                params
            )
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_location_statistics(self) -> Dict:
        """Get location-related statistics."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        stats = {}
        
        # Count photos with location
        cursor.execute("SELECT COUNT(*) FROM photo_locations WHERE has_location = 1")
        stats["total_locations"] = cursor.fetchone()[0]
        
        # Count geocoded locations
        cursor.execute(
            """
            SELECT COUNT(*) FROM photo_locations 
            WHERE has_location = 1 AND (city IS NOT NULL OR region IS NOT NULL OR country IS NOT NULL)
            """
        )
        stats["geocoded_locations"] = cursor.fetchone()[0]
        
        # Count unique places (cities)
        cursor.execute("SELECT COUNT(DISTINCT city) FROM photo_locations WHERE city IS NOT NULL")
        stats["unique_cities"] = cursor.fetchone()[0]
        
        # Count unique countries
        cursor.execute("SELECT COUNT(DISTINCT country) FROM photo_locations WHERE country IS NOT NULL")
        stats["unique_countries"] = cursor.fetchone()[0]
        
        conn.close()
        return stats

    def delete_location(self, photo_id: int) -> bool:
        """Delete location for a photo. Returns True if deleted."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM photo_locations WHERE photo_id = ?", (photo_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def cleanup_orphaned_people(self) -> List[int]:
        """
        Find and delete people who have zero faces.
        Deletes ALL people with no faces, even if they have a name assigned.
        No empty placeholder people are kept.
        
        Returns list of deleted person IDs.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Find people with no faces
            cursor.execute("""
                SELECT p.id 
                FROM people p
                LEFT JOIN faces f ON f.person_id = p.id
                WHERE f.id IS NULL
            """)
            orphaned_person_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete orphaned people
            if orphaned_person_ids:
                placeholders = ','.join('?' * len(orphaned_person_ids))
                cursor.execute(f"DELETE FROM people WHERE id IN ({placeholders})", orphaned_person_ids)
                conn.commit()
            
            conn.close()
            return orphaned_person_ids
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def cleanup_orphaned_pets(self) -> List[int]:
        """
        Find and delete pets who have zero detections.
        Deletes ALL pets with no detections, even if they have a name assigned.
        No empty placeholder pets are kept.
        
        Returns list of deleted pet IDs.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Find pets with no detections
            cursor.execute("""
                SELECT p.id 
                FROM pets p
                LEFT JOIN pet_detections pd ON pd.pet_id = p.id
                WHERE pd.id IS NULL
            """)
            orphaned_pet_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete orphaned pets
            if orphaned_pet_ids:
                placeholders = ','.join('?' * len(orphaned_pet_ids))
                cursor.execute(f"DELETE FROM pets WHERE id IN ({placeholders})", orphaned_pet_ids)
                conn.commit()
            
            conn.close()
            return orphaned_pet_ids
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def cleanup_orphaned_objects(self) -> int:
        """
        Find and delete objects that reference non-existent photos.
        Returns count of deleted objects.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Delete objects where photo doesn't exist
            cursor.execute("""
                DELETE FROM objects 
                WHERE photo_id NOT IN (SELECT id FROM photos)
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def cleanup_orphaned_locations(self) -> int:
        """
        Find and delete photo_locations that reference non-existent photos.
        Returns count of deleted locations.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Delete locations where photo doesn't exist
            cursor.execute("""
                DELETE FROM photo_locations 
                WHERE photo_id NOT IN (SELECT id FROM photos)
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    def cleanup_orphaned_scenes(self) -> int:
        """
        Find and delete scenes that reference non-existent photos.
        Returns count of deleted scenes.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            # Delete scenes where photo doesn't exist
            cursor.execute("""
                DELETE FROM scenes 
                WHERE photo_id NOT IN (SELECT id FROM photos)
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    # =========================================================================
    # CUSTOM USER TAGS METHODS
    # =========================================================================

    def add_tag(self, photo_id: int, tag: str) -> int:
        """
        Add a custom tag to a photo. Returns tag_id.
        Tag is normalized (lowercase, trimmed).
        """
        # Normalize tag
        normalized_tag = tag.lower().strip()
        if not normalized_tag:
            raise ValueError("Tag cannot be empty")
        
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO photo_tags (photo_id, tag) VALUES (?, ?)",
                (photo_id, normalized_tag),
            )
            conn.commit()
            
            # Get the tag ID (either new or existing)
            cursor.execute(
                "SELECT id FROM photo_tags WHERE photo_id = ? AND tag = ?",
                (photo_id, normalized_tag),
            )
            row = cursor.fetchone()
            tag_id = row[0] if row else 0
            conn.close()
            return tag_id
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e

    def remove_tag(self, photo_id: int, tag: str) -> bool:
        """Remove a custom tag from a photo. Returns True if deleted."""
        normalized_tag = tag.lower().strip()
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM photo_tags WHERE photo_id = ? AND tag = ?",
            (photo_id, normalized_tag),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_tags_for_photo(self, photo_id: int) -> List[str]:
        """Get all custom tags for a photo."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tag FROM photo_tags WHERE photo_id = ? ORDER BY tag",
            (photo_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_photos_by_tag(self, tag: str) -> List[Dict]:
        """Get all photos with a specific tag."""
        normalized_tag = tag.lower().strip()
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.* FROM photos p
            INNER JOIN photo_tags pt ON p.id = pt.photo_id
            WHERE pt.tag = ?
            ORDER BY p.date_taken DESC, p.created_at DESC
            """,
            (normalized_tag,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_tags_with_counts(self) -> List[Dict]:
        """
        Get all unique tags with photo counts.
        Used for Objects > Custom section in the UI.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tag, COUNT(DISTINCT photo_id) as photo_count
            FROM photo_tags
            GROUP BY tag
            ORDER BY photo_count DESC, tag ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"tag": row[0], "photo_count": row[1]} for row in rows]

    def search_tags_by_text(self, query: str) -> List[Dict]:
        """
        Search custom tags by text matching.
        Returns list of dicts with photo_id, tag for search integration.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query_lower = query.lower().strip()
        
        # Search for exact match first, then partial
        cursor.execute(
            """
            SELECT photo_id, tag,
                   CASE 
                       WHEN tag = ? THEN 'exact'
                       WHEN tag LIKE ? THEN 'partial'
                       ELSE 'word'
                   END as match_type
            FROM photo_tags
            WHERE tag = ? OR tag LIKE ?
            """,
            (query_lower, f"%{query_lower}%", query_lower, f"%{query_lower}%"),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_tags_for_photo(self, photo_id: int) -> int:
        """Delete all tags for a photo. Returns count of deleted tags."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM photo_tags WHERE photo_id = ?", (photo_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count

    def cleanup_orphaned_tags(self) -> int:
        """
        Find and delete tags that reference non-existent photos.
        Returns count of deleted tags.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM photo_tags 
                WHERE photo_id NOT IN (SELECT id FROM photos)
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
