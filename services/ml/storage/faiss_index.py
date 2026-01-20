"""FAISS vector index management for embeddings."""

import pickle
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np


class FAISSIndex:
    """Manages FAISS indices for different embedding types with thread-safe writes."""

    def __init__(self, index_dir: str = "data/indices"):
        """Initialize index directory."""
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._indices: dict[str, faiss.Index] = {}
        self._id_maps: dict[str, dict[int, int]] = {}  # FAISS ID -> entity ID
        # Lock for serializing write operations (add, save, create)
        self._write_lock = threading.Lock()

    def _get_index_path(self, embedding_type: str) -> Path:
        """Get path for index file."""
        return self.index_dir / f"{embedding_type}.index"

    def _get_id_map_path(self, embedding_type: str) -> Path:
        """Get path for ID map file."""
        return self.index_dir / f"{embedding_type}_ids.pkl"

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

    def load_index(self, embedding_type: str) -> bool:
        """Load index from disk (thread-safe). Returns True if successful."""
        index_path = self._get_index_path(embedding_type)
        id_map_path = self._get_id_map_path(embedding_type)

        if not index_path.exists():
            return False

        with self._write_lock:
            try:
                self._indices[embedding_type] = faiss.read_index(str(index_path))
                if id_map_path.exists():
                    with open(id_map_path, "rb") as f:
                        self._id_maps[embedding_type] = pickle.load(f)
                else:
                    self._id_maps[embedding_type] = {}
                return True
            except Exception:
                return False

    def save_index(self, embedding_type: str) -> None:
        """Save index to disk (thread-safe)."""
        if embedding_type not in self._indices:
            return

        with self._write_lock:
            index_path = self._get_index_path(embedding_type)
            id_map_path = self._get_id_map_path(embedding_type)

            faiss.write_index(self._indices[embedding_type], str(index_path))
            with open(id_map_path, "wb") as f:
                pickle.dump(self._id_maps[embedding_type], f)

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

    def search(
        self,
        embedding_type: str,
        query_vector: np.ndarray,
        k: int = 10,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar vectors. Returns (distances, entity_ids)."""
        if embedding_type not in self._indices:
            return np.array([]), np.array([])

        index = self._indices[embedding_type]
        id_map = self._id_maps[embedding_type]
        
        # Check if index is empty
        if index.ntotal == 0:
            return np.array([]), np.array([])

        # Normalize for cosine similarity if needed
        if isinstance(index, faiss.IndexFlatIP):
            query_vector = query_vector.copy()
            faiss.normalize_L2(query_vector.reshape(1, -1))
            query_vector = query_vector.flatten()

        query_vector = query_vector.astype(np.float32).reshape(1, -1)
        
        # Limit k to available vectors
        actual_k = min(k, index.ntotal)
        if actual_k == 0:
            return np.array([]), np.array([])
            
        distances, faiss_ids = index.search(query_vector, actual_k)

        # Convert FAISS IDs to entity IDs
        entity_ids = np.array([id_map.get(int(fid), -1) for fid in faiss_ids[0]])

        return distances[0], entity_ids

    def get_index_size(self, embedding_type: str) -> int:
        """Get number of vectors in index."""
        if embedding_type not in self._indices:
            return 0
        return self._indices[embedding_type].ntotal

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
                metric = "cosine"
            else:
                new_index = faiss.IndexFlatL2(dimension)
                metric = "L2"
            
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
