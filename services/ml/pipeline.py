"""Main ML pipeline orchestrator."""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

from services.ml.detectors.face_detector import FaceDetector
from services.ml.detectors.object_detector import ObjectDetector
from services.ml.embeddings.face_embedding import FaceEmbedder
from services.ml.embeddings.image_embedding import ImageEmbedder
from services.ml.storage.faiss_index import FAISSIndex
from services.ml.storage.sqlite_store import SQLiteStore
from services.ml.utils import extract_exif_metadata


class MLPipeline:
    """Orchestrates ML processing: detection, embedding, clustering."""

    def __init__(
        self,
        db_path: str = "photosense.db",
        index_dir: str = "data/indices",
        cache_dir: str = "data/cache",
    ):
        """Initialize ML pipeline."""
        self.store = SQLiteStore(db_path)
        self.index = FAISSIndex(index_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize models (lazy loading)
        self.face_detector = FaceDetector()
        self.object_detector = ObjectDetector()
        self.face_embedder = FaceEmbedder()
        self.image_embedder = ImageEmbedder()

        # Load or create indices
        self._init_indices()

    def _init_indices(self) -> None:
        """Initialize FAISS indices."""
        # Face embeddings: 512 dim, cosine similarity
        if not self.index.load_index("face"):
            self.index.create_index("face", dimension=512, metric="cosine")
            self.index.save_index("face")

        # Image embeddings: 512 dim, cosine similarity
        if not self.index.load_index("image"):
            self.index.create_index("image", dimension=512, metric="cosine")
            self.index.save_index("image")

    async def import_photo(self, photo_path: str) -> Dict:
        """Import a photo with metadata only (no face/object detection).
        
        This is Phase 1 of the import process - fast import that allows photos
        to appear in the dashboard immediately, grouped by date.
        """
        # Extract EXIF metadata first
        metadata = extract_exif_metadata(photo_path)
        
        photo_id = self.store.add_photo(
            file_path=photo_path,
            date_taken=metadata.get("date_taken"),
            camera_model=metadata.get("camera_model"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            file_size=metadata.get("file_size"),
        )

        if photo_id is None:
            # Photo already exists - get existing photo and update metadata if needed
            existing_photo = self.store.get_photo_by_path(photo_path)
            if existing_photo:
                photo_id = existing_photo["id"]
                # Update metadata if any fields are missing
                needs_update = False
                update_data = {}
                
                if not existing_photo.get("date_taken") and metadata.get("date_taken"):
                    update_data["date_taken"] = metadata.get("date_taken")
                    needs_update = True
                if not existing_photo.get("camera_model") and metadata.get("camera_model"):
                    update_data["camera_model"] = metadata.get("camera_model")
                    needs_update = True
                if not existing_photo.get("width") and metadata.get("width"):
                    update_data["width"] = metadata.get("width")
                    needs_update = True
                if not existing_photo.get("height") and metadata.get("height"):
                    update_data["height"] = metadata.get("height")
                    needs_update = True
                if not existing_photo.get("file_size") and metadata.get("file_size"):
                    update_data["file_size"] = metadata.get("file_size")
                    needs_update = True
                
                if needs_update:
                    self.store.update_photo_metadata(photo_id=photo_id, **update_data)
                
                return {"status": "exists", "photo_id": photo_id, "updated": needs_update}
            else:
                return {"status": "skipped", "reason": "duplicate"}

        return {
            "status": "imported",
            "photo_id": photo_id,
            "date_taken": metadata.get("date_taken"),
        }

    async def process_photo_ml(self, photo_id: int, photo_path: str) -> Dict:
        """Process ML features for an already-imported photo (Phase 2).
        
        This performs face detection, object detection, and embedding generation.
        Should be called after import_photo for each photo.
        """
        results = {
            "photo_id": photo_id,
            "faces": [],
            "objects": [],
            "image_embedding_id": None,
        }

        # Load image
        image = cv2.imread(photo_path)
        if image is None:
            return {"status": "error", "reason": "invalid_image"}

        # Detect faces
        face_detections = self.face_detector.detect(photo_path)
        for x, y, w, h, conf in face_detections:
            face_id = self.store.add_face(
                photo_id=photo_id,
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                confidence=conf,
            )

            # Crop and embed face
            face_crop = image[y : y + h, x : x + w]
            embedding = self.face_embedder.embed(face_crop)

            # Add to FAISS index
            self.index.add_vectors("face", embedding.reshape(1, -1), [face_id])
            self.index.save_index("face")

            # Update face with embedding reference
            self.store.update_face_embedding(face_id, face_id)

            results["faces"].append(face_id)

        # Detect objects
        object_detections = self.object_detector.detect(photo_path)
        for x, y, w, h, category, conf in object_detections:
            object_id = self.store.add_object(
                photo_id=photo_id,
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                category=category,
                confidence=conf,
            )
            results["objects"].append(object_id)

        # Generate image embedding
        image_embedding = self.image_embedder.embed(photo_path)
        self.index.add_vectors("image", image_embedding.reshape(1, -1), [photo_id])
        self.index.save_index("image")
        results["image_embedding_id"] = photo_id

        return results

    async def process_photo(self, photo_path: str) -> Dict:
        """Process a single photo: detect, embed, index."""
        # Extract EXIF metadata first
        metadata = extract_exif_metadata(photo_path)
        
        photo_id = self.store.add_photo(
            file_path=photo_path,
            date_taken=metadata.get("date_taken"),
            camera_model=metadata.get("camera_model"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            file_size=metadata.get("file_size"),
        )

        if photo_id is None:
            # Photo already exists - get existing photo and update metadata if needed
            existing_photo = self.store.get_photo_by_path(photo_path)
            if existing_photo:
                photo_id = existing_photo["id"]
                # Update metadata if any fields are missing
                needs_update = False
                update_data = {}
                
                if not existing_photo.get("date_taken") and metadata.get("date_taken"):
                    update_data["date_taken"] = metadata.get("date_taken")
                    needs_update = True
                if not existing_photo.get("camera_model") and metadata.get("camera_model"):
                    update_data["camera_model"] = metadata.get("camera_model")
                    needs_update = True
                if not existing_photo.get("width") and metadata.get("width"):
                    update_data["width"] = metadata.get("width")
                    needs_update = True
                if not existing_photo.get("height") and metadata.get("height"):
                    update_data["height"] = metadata.get("height")
                    needs_update = True
                if not existing_photo.get("file_size") and metadata.get("file_size"):
                    update_data["file_size"] = metadata.get("file_size")
                    needs_update = True
                
                if needs_update:
                    self.store.update_photo_metadata(photo_id=photo_id, **update_data)
            else:
                return {"status": "skipped", "reason": "duplicate"}

        results = {
            "photo_id": photo_id,
            "faces": [],
            "objects": [],
            "image_embedding_id": None,
        }

        # Load image
        image = cv2.imread(photo_path)
        if image is None:
            return {"status": "error", "reason": "invalid_image"}

        # Detect faces
        face_detections = self.face_detector.detect(photo_path)
        for x, y, w, h, conf in face_detections:
            face_id = self.store.add_face(
                photo_id=photo_id,
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                confidence=conf,
            )

            # Crop and embed face
            face_crop = image[y : y + h, x : x + w]
            embedding = self.face_embedder.embed(face_crop)

            # Add to FAISS index
            self.index.add_vectors("face", embedding.reshape(1, -1), [face_id])
            self.index.save_index("face")

            # Update face with embedding reference
            self.store.update_face_embedding(face_id, face_id)  # Using face_id as embedding_id

            results["faces"].append(face_id)

        # Detect objects
        object_detections = self.object_detector.detect(photo_path)
        for x, y, w, h, category, conf in object_detections:
            object_id = self.store.add_object(
                photo_id=photo_id,
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                category=category,
                confidence=conf,
            )
            results["objects"].append(object_id)

        # Generate image embedding
        image_embedding = self.image_embedder.embed(photo_path)
        self.index.add_vectors("image", image_embedding.reshape(1, -1), [photo_id])
        self.index.save_index("image")
        results["image_embedding_id"] = photo_id

        return results

    async def cluster_faces(self, eps: float = 0.5, min_samples: int = 3) -> Dict:
        """Cluster faces using DBSCAN."""
        # Get all faces with embeddings from photos
        photos = self.store.get_all_photos()
        all_embeddings = []
        all_face_ids = []

        for photo in photos:
            faces = self.store.get_faces_for_photo(photo["id"])
            for face in faces:
                if face.get("embedding_id"):
                    face_id = face["id"]
                    # Retrieve embedding from FAISS index
                    # Note: This is a simplified approach - in production, you'd want to store
                    # embeddings separately for efficient retrieval
                    embedding_id = face["embedding_id"]
                    # For now, we'll need to reconstruct embeddings from the index
                    # This is a limitation - ideally embeddings should be stored separately
                    all_face_ids.append(face_id)

        if len(all_face_ids) < min_samples:
            return {"clusters": 0, "faces_clustered": 0}

        # Get embeddings from index (simplified - would need to store embeddings)
        # For now, use a placeholder clustering approach
        # In production, retrieve actual embeddings from storage

        # Create clusters
        # embeddings_array = np.array(all_embeddings)
        # clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(embeddings_array)

        # Assign clusters
        # for face_id, cluster_id in zip(all_face_ids, clustering.labels_):
        #     if cluster_id >= 0:  # Not noise
        #         self.store.update_face_cluster(face_id, int(cluster_id))

        # Create person entries for clusters
        # unique_clusters = set(clustering.labels_) - {-1}
        # for cluster_id in unique_clusters:
        #     person_id = self.store.create_person(cluster_id=int(cluster_id))
        #     # Update faces with person_id
        #     cluster_faces = [fid for fid, cid in zip(all_face_ids, clustering.labels_) if cid == cluster_id]
        #     for face_id in cluster_faces:
        #         self.store.update_face_person(face_id, person_id)

        return {"clusters": 0, "faces_clustered": 0}  # Placeholder - requires embedding storage refactor

    async def search_similar_images(self, query_text: str, k: int = 10) -> List[int]:
        """Search for similar images using text query."""
        query_embedding = self.image_embedder.embed_text(query_text)
        distances, photo_ids = self.index.search("image", query_embedding, k=k)
        return [int(pid) for pid in photo_ids if pid >= 0]

    async def search_similar_faces(self, face_id: int, k: int = 10) -> List[int]:
        """Search for similar faces."""
        # Retrieve face embedding (simplified - would need proper storage)
        # For now, placeholder
        return []
