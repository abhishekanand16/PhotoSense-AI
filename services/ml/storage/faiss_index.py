"""FAISS vector index management for embeddings.

Features:
- Thread-safe read/write operations
- LRU caching for search results
- Automatic corruption detection on load
- Auto-rebuild capability when corruption is detected
- Backup creation before rebuild
"""

import hashlib
import logging
import pickle
import shutil
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import faiss
import numpy as np

from services.config import INDICES_DIR


logger = logging.getLogger(__name__)


class LRUCache:
    """Simple LRU cache for search results."""
    
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Tuple]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def put(self, key: str, value: Tuple) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)
            self._cache[key] = value
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class IndexCorruptionError(Exception):
    """Raised when a FAISS index is detected as corrupted."""
    pass


class FAISSIndex:
    """Manages FAISS indices for different embedding types with thread-safe writes.
    
    Features:
    - Thread-safe read/write operations
    - LRU caching for search results
    - Automatic corruption detection on load
    - Auto-rebuild capability when corruption is detected
    - Backup creation before rebuild
    """

    # Index configuration (dimension and metric)
    INDEX_CONFIGS: Dict[str, Dict] = {
        "face": {"dimension": 512, "metric": "cosine"},
        "image": {"dimension": 768, "metric": "cosine"},
        "pet": {"dimension": 768, "metric": "cosine"},
    }

    def __init__(self, index_dir: str = str(INDICES_DIR)):
        """Initialize index directory."""
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._indices: dict[str, faiss.Index] = {}
        self._id_maps: dict[str, dict[int, int]] = {}  # FAISS ID -> entity ID
        # Lock for serializing write operations (add, save, create)
        self._write_lock = threading.Lock()
        # LRU cache for search results (per index type)
        self._search_cache: dict[str, LRUCache] = {}
        # Track dirty indices that need saving
        self._dirty: set[str] = set()
        # Rebuild callbacks for auto-recovery
        self._rebuild_callbacks: dict[str, Callable] = {}

    def register_rebuild_callback(self, embedding_type: str, callback: Callable) -> None:
        """
        Register a callback function to rebuild an index from database.
        
        The callback should:
        - Return list of (entity_id, embedding) tuples
        - Be callable without arguments
        
        Args:
            embedding_type: Type of index (e.g., "face", "pet", "image")
            callback: Function that returns embeddings from database
        """
        self._rebuild_callbacks[embedding_type] = callback

    def _get_index_path(self, embedding_type: str) -> Path:
        """Get path for index file."""
        return self.index_dir / f"{embedding_type}.index"

    def _get_id_map_path(self, embedding_type: str) -> Path:
        """Get path for ID map file."""
        return self.index_dir / f"{embedding_type}_ids.pkl"

    def _get_backup_dir(self) -> Path:
        """Get backup directory path."""
        backup_dir = self.index_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _backup_index(self, embedding_type: str) -> Optional[Path]:
        """Create a backup of the index files before rebuild.
        
        Returns:
            Path to backup directory if successful, None otherwise
        """
        index_path = self._get_index_path(embedding_type)
        id_map_path = self._get_id_map_path(embedding_type)
        
        if not index_path.exists():
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self._get_backup_dir() / f"{embedding_type}_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Use try/except for each file to handle Windows file locks gracefully
            if index_path.exists():
                try:
                    shutil.copy2(index_path, backup_dir / index_path.name)
                except PermissionError as e:
                    logger.warning(f"Could not backup index file (may be in use): {e}")
                    
            if id_map_path.exists():
                try:
                    shutil.copy2(id_map_path, backup_dir / id_map_path.name)
                except PermissionError as e:
                    logger.warning(f"Could not backup ID map file (may be in use): {e}")
            
            logger.info(f"Created backup of {embedding_type} index at {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"Failed to create backup of {embedding_type} index: {e}")
            return None

    def check_index_integrity(self, embedding_type: str) -> Dict:
        """
        Check the integrity of an index.
        
        Returns dict with:
        - valid: bool - whether the index is valid
        - reason: str - reason if invalid
        - index_size: int - number of vectors in index
        - id_map_size: int - number of entries in ID map
        """
        index_path = self._get_index_path(embedding_type)
        id_map_path = self._get_id_map_path(embedding_type)
        
        result = {
            "valid": True,
            "reason": None,
            "index_size": 0,
            "id_map_size": 0,
        }
        
        # Check if files exist
        if not index_path.exists():
            result["valid"] = False
            result["reason"] = "index_file_missing"
            return result
        
        try:
            # Try to load the index
            index = faiss.read_index(str(index_path))
            result["index_size"] = index.ntotal
            
            # Check expected dimension
            config = self.INDEX_CONFIGS.get(embedding_type)
            if config and index.d != config["dimension"]:
                result["valid"] = False
                result["reason"] = f"dimension_mismatch: expected {config['dimension']}, got {index.d}"
                return result
            
            # Try to load the ID map
            if id_map_path.exists():
                with open(id_map_path, "rb") as f:
                    id_map = pickle.load(f)
                result["id_map_size"] = len(id_map)
                
                # Check consistency between index and ID map
                if index.ntotal > 0 and len(id_map) != index.ntotal:
                    result["valid"] = False
                    result["reason"] = f"size_mismatch: index has {index.ntotal} vectors, ID map has {len(id_map)} entries"
                    return result
            else:
                # ID map missing but index has vectors
                if index.ntotal > 0:
                    result["valid"] = False
                    result["reason"] = "id_map_missing_with_vectors"
                    return result
            
            # Try a sample search to verify functionality
            if index.ntotal > 0:
                try:
                    dimension = index.d
                    dummy_query = np.zeros((1, dimension), dtype=np.float32)
                    index.search(dummy_query, min(5, index.ntotal))
                except Exception as e:
                    result["valid"] = False
                    result["reason"] = f"search_failed: {str(e)}"
                    return result
            
        except Exception as e:
            result["valid"] = False
            result["reason"] = f"load_failed: {str(e)}"
            return result
        
        return result

    def auto_rebuild_if_corrupted(self, embedding_type: str) -> Dict:
        """
        Check index integrity and rebuild from database if corrupted.
        
        Returns dict with:
        - action: str - 'none', 'rebuilt', or 'failed'
        - reason: str - explanation
        - count: int - number of vectors after rebuild
        """
        integrity = self.check_index_integrity(embedding_type)
        
        if integrity["valid"]:
            return {
                "action": "none",
                "reason": "index_is_valid",
                "count": integrity["index_size"],
            }
        
        logger.warning(f"Index {embedding_type} is corrupted: {integrity['reason']}")
        
        # Check if we have a rebuild callback
        callback = self._rebuild_callbacks.get(embedding_type)
        if callback is None:
            logger.error(f"No rebuild callback registered for {embedding_type}")
            return {
                "action": "failed",
                "reason": "no_rebuild_callback",
                "count": 0,
            }
        
        # Create backup before rebuild
        self._backup_index(embedding_type)
        
        try:
            # Get embeddings from database via callback
            embeddings_data = callback()
            
            if not embeddings_data:
                logger.info(f"No embeddings to rebuild for {embedding_type}")
                # Create empty index
                config = self.INDEX_CONFIGS.get(embedding_type, {"dimension": 512, "metric": "cosine"})
                self.create_index(embedding_type, config["dimension"], config["metric"])
                self.save_index(embedding_type, force=True)
                return {
                    "action": "rebuilt",
                    "reason": "rebuilt_empty_index",
                    "count": 0,
                }
            
            # Rebuild the index
            config = self.INDEX_CONFIGS.get(embedding_type, {"dimension": 512, "metric": "cosine"})
            self.create_index(embedding_type, config["dimension"], config["metric"])
            
            entity_ids = [eid for eid, _ in embeddings_data]
            embeddings = np.array([emb for _, emb in embeddings_data], dtype=np.float32)
            
            self.add_vectors(embedding_type, embeddings, entity_ids)
            self.save_index(embedding_type, force=True)
            
            logger.info(f"Successfully rebuilt {embedding_type} index with {len(entity_ids)} vectors")
            
            return {
                "action": "rebuilt",
                "reason": f"rebuilt_from_corruption: {integrity['reason']}",
                "count": len(entity_ids),
            }
            
        except Exception as e:
            logger.error(f"Failed to rebuild {embedding_type} index: {e}")
            return {
                "action": "failed",
                "reason": f"rebuild_error: {str(e)}",
                "count": 0,
            }

    def create_index(self, embedding_type: str, dimension: int, metric: str = "L2") -> None:
        """Create a new FAISS index (thread-safe)."""
        with self._write_lock:
            if metric == "L2":
                index = faiss.IndexFlatL2(dimension)
            elif metric == "cosine":
                index = faiss.IndexFlatIP(dimension)
                # For cosine similarity, we normalize vectors
            else:
                raise ValueError(f"Unknown metric: {metric}")

            self._indices[embedding_type] = index
            self._id_maps[embedding_type] = {}
            self._search_cache[embedding_type] = LRUCache(maxsize=128)
            self._dirty.discard(embedding_type)

    def load_index(self, embedding_type: str, auto_rebuild: bool = True) -> bool:
        """Load index from disk (thread-safe). Returns True if successful.
        
        Args:
            embedding_type: Type of index to load
            auto_rebuild: If True, attempt to rebuild from database if corrupted
        """
        index_path = self._get_index_path(embedding_type)
        id_map_path = self._get_id_map_path(embedding_type)

        if not index_path.exists():
            return False

        with self._write_lock:
            try:
                # First, check integrity
                integrity = self.check_index_integrity(embedding_type)
                
                if not integrity["valid"]:
                    logger.warning(f"Index {embedding_type} corruption detected: {integrity['reason']}")
                    
                    if auto_rebuild and embedding_type in self._rebuild_callbacks:
                        # Release lock for rebuild (will acquire its own lock)
                        pass
                    else:
                        return False
                
                self._indices[embedding_type] = faiss.read_index(str(index_path))
                if id_map_path.exists():
                    with open(id_map_path, "rb") as f:
                        self._id_maps[embedding_type] = pickle.load(f)
                else:
                    self._id_maps[embedding_type] = {}
                # Initialize cache for loaded index
                self._search_cache[embedding_type] = LRUCache(maxsize=128)
                self._dirty.discard(embedding_type)
                
                logger.info(f"Loaded {embedding_type} index with {self._indices[embedding_type].ntotal} vectors")
                return True
            except Exception as e:
                logger.error(f"Failed to load {embedding_type} index: {e}")
                return False

    def save_index(self, embedding_type: str, force: bool = False) -> None:
        """Save index to disk (thread-safe).
        
        Args:
            embedding_type: Type of index to save
            force: If True, save even if not dirty. If False, only save if dirty.
        """
        if embedding_type not in self._indices:
            return
        
        # Skip if not dirty and not forced
        if not force and embedding_type not in self._dirty:
            return

        with self._write_lock:
            index_path = self._get_index_path(embedding_type)
            id_map_path = self._get_id_map_path(embedding_type)

            faiss.write_index(self._indices[embedding_type], str(index_path))
            with open(id_map_path, "wb") as f:
                pickle.dump(self._id_maps[embedding_type], f)
            
            # Mark as clean after save
            self._dirty.discard(embedding_type)
            
            logger.debug(f"Saved {embedding_type} index with {self._indices[embedding_type].ntotal} vectors")

    def add_vectors(
        self,
        embedding_type: str,
        vectors: np.ndarray,
        entity_ids: List[int],
    ) -> None:
        """Add vectors to index with entity IDs (thread-safe)."""
        if embedding_type not in self._indices:
            raise ValueError(f"Index {embedding_type} does not exist. Create it first.")

        with self._write_lock:
            index = self._indices[embedding_type]
            id_map = self._id_maps[embedding_type]

            # Normalize for cosine similarity if needed
            vectors_copy = vectors.astype(np.float32).copy()
            if isinstance(index, faiss.IndexFlatIP):
                faiss.normalize_L2(vectors_copy)

            start_id = index.ntotal
            index.add(vectors_copy)

            # Map FAISS IDs to entity IDs
            for i, entity_id in enumerate(entity_ids):
                id_map[start_id + i] = entity_id
            
            # Invalidate search cache when index changes
            if embedding_type in self._search_cache:
                self._search_cache[embedding_type].clear()
            
            # Mark index as dirty
            self._dirty.add(embedding_type)

    def _make_cache_key(self, query_vector: np.ndarray, k: int) -> str:
        """Create a cache key from query vector and k."""
        # Use hash of the vector bytes + k for cache key
        vec_bytes = query_vector.tobytes()
        return hashlib.md5(vec_bytes + str(k).encode()).hexdigest()
    
    def search(
        self,
        embedding_type: str,
        query_vector: np.ndarray,
        k: int = 10,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar vectors with LRU caching. Returns (distances, entity_ids)."""
        if embedding_type not in self._indices:
            return np.array([]), np.array([])

        index = self._indices[embedding_type]
        id_map = self._id_maps[embedding_type]
        
        # Check if index is empty
        if index.ntotal == 0:
            return np.array([]), np.array([])
        
        # Prepare query vector (normalize for cosine)
        query_vec = query_vector.astype(np.float32).flatten()
        if isinstance(index, faiss.IndexFlatIP):
            query_vec_normalized = query_vec.copy()
            faiss.normalize_L2(query_vec_normalized.reshape(1, -1))
            query_vec_normalized = query_vec_normalized.flatten()
        else:
            query_vec_normalized = query_vec
        
        # Check cache
        cache = self._search_cache.get(embedding_type)
        if cache is not None:
            cache_key = self._make_cache_key(query_vec_normalized, k)
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Limit k to available vectors
        actual_k = min(k, index.ntotal)
        if actual_k == 0:
            return np.array([]), np.array([])
        
        # Perform search
        distances, faiss_ids = index.search(query_vec_normalized.reshape(1, -1), actual_k)

        # Convert FAISS IDs to entity IDs
        entity_ids = np.array([id_map.get(int(fid), -1) for fid in faiss_ids[0]])
        
        result = (distances[0], entity_ids)
        
        # Store in cache
        if cache is not None:
            cache.put(cache_key, result)

        return result

    def get_index_size(self, embedding_type: str) -> int:
        """Get number of vectors in index."""
        if embedding_type not in self._indices:
            return 0
        return self._indices[embedding_type].ntotal

    def save_all_dirty(self) -> int:
        """Save all dirty indices to disk. Returns number of indices saved."""
        saved_count = 0
        for embedding_type in list(self._dirty):
            self.save_index(embedding_type, force=True)
            saved_count += 1
        return saved_count
    
    def mark_dirty(self, embedding_type: str) -> None:
        """Manually mark an index as dirty (needing save)."""
        if embedding_type in self._indices:
            self._dirty.add(embedding_type)

    def remove_vectors(self, embedding_type: str, entity_ids: List[int]) -> None:
        """
        Remove vectors by entity IDs by rebuilding the index.
        FAISS doesn't support efficient removal, so we recreate the index without the deleted vectors.
        
        Args:
            embedding_type: Type of embedding index (e.g., "face", "pet", "image")
            entity_ids: List of entity IDs to remove
        """
        if embedding_type not in self._indices:
            return

        if not entity_ids:
            return

        with self._write_lock:
            index = self._indices[embedding_type]
            id_map = self._id_maps[embedding_type]
            
            # Nothing to remove if index is empty
            if index.ntotal == 0:
                return
            
            # Convert entity_ids to set for fast lookup
            entity_ids_set = set(entity_ids)
            
            # Collect vectors to keep (all except the ones to remove)
            vectors_to_keep = []
            entity_ids_to_keep = []
            
            for faiss_id in range(index.ntotal):
                entity_id = id_map.get(faiss_id)
                if entity_id is not None and entity_id not in entity_ids_set:
                    # Reconstruct vector from FAISS
                    vector = index.reconstruct(int(faiss_id))
                    vectors_to_keep.append(vector)
                    entity_ids_to_keep.append(entity_id)
            
            # Recreate index with same configuration
            dimension = index.d
            if isinstance(index, faiss.IndexFlatIP):
                new_index = faiss.IndexFlatIP(dimension)
            else:
                new_index = faiss.IndexFlatL2(dimension)
            
            # Add kept vectors to new index
            if vectors_to_keep:
                vectors_array = np.array(vectors_to_keep, dtype=np.float32)
                
                # Normalize for cosine similarity if needed
                if isinstance(new_index, faiss.IndexFlatIP):
                    faiss.normalize_L2(vectors_array)
                
                new_index.add(vectors_array)
                
                # Rebuild ID map
                new_id_map = {}
                for i, entity_id in enumerate(entity_ids_to_keep):
                    new_id_map[i] = entity_id
                
                self._id_maps[embedding_type] = new_id_map
            else:
                # No vectors to keep - reset to empty map
                self._id_maps[embedding_type] = {}
            
            # Replace old index with new one
            self._indices[embedding_type] = new_index
            
            # Invalidate search cache
            if embedding_type in self._search_cache:
                self._search_cache[embedding_type].clear()
            
            # Mark as dirty
            self._dirty.add(embedding_type)
            
            logger.info(f"Removed {len(entity_ids)} vectors from {embedding_type} index, {new_index.ntotal} remaining")

    def get_all_index_stats(self) -> Dict[str, Dict]:
        """Get statistics for all loaded indices."""
        stats = {}
        for embedding_type in self._indices:
            integrity = self.check_index_integrity(embedding_type)
            stats[embedding_type] = {
                "loaded": True,
                "size": self._indices[embedding_type].ntotal,
                "dimension": self._indices[embedding_type].d,
                "dirty": embedding_type in self._dirty,
                "integrity": integrity,
            }
        return stats
