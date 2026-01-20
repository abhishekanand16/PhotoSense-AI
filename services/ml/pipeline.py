"""
Main ML pipeline orchestrator for PhotoSense-AI.

Production-grade face recognition pipeline with:
- InsightFace (RetinaFace + ArcFace) for detection and embedding
- DBSCAN clustering for identity grouping
- FAISS for similarity search
- SQLite for metadata and embedding storage

Design decisions:
1. Confidence threshold: 0.6 (balances recall vs precision)
2. Clustering: DBSCAN with eps=0.5, min_samples=2 (allows pairs)
3. Single-face clusters: Kept (better to split than merge incorrectly)
4. Low-confidence faces: Excluded from clustering (manual review)
5. Noise faces: Unassigned, available for user correction
6. Face alignment: Handled automatically by InsightFace
7. Embeddings: Stored in SQLite (retrieval) + FAISS (similarity)
8. Reclustering: Can be triggered manually or automatically after N new faces

Consistency guarantees:
- Embeddings stored in both SQLite and FAISS (rebuild_faiss_index if diverge)
- Face deletion removes from DB but requires FAISS rebuild
- Clustering is idempotent (can rerun safely)
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from sklearn.cluster import DBSCAN

from services.ml.detectors.face_detector import FaceDetector
from services.ml.detectors.object_detector import ObjectDetector
from services.ml.detectors.scene_detector import SceneDetector  # Places365 - now installed!
from services.ml.detectors.clip_scene_detector import CLIPSceneDetector  # CLIP zero-shot scenes
from services.ml.detectors.florence_detector import FlorenceDetector  # Florence-2 vision-language
from services.ml.embeddings.face_embedding import FaceEmbedder
from services.ml.embeddings.image_embedding import ImageEmbedder
from services.ml.storage.faiss_index import FAISSIndex
from services.ml.storage.sqlite_store import SQLiteStore
from services.ml.utils import extract_exif_metadata


# Scene fusion configuration
SCENE_FUSION_CONFIG = {
    # Maximum number of final scene tags per image
    "max_tags": 8,
    # Minimum confidence for Places365 tags
    "places365_min_confidence": 0.15,
    # Minimum confidence for CLIP tags
    "clip_min_confidence": 0.25,
    # Minimum confidence for Florence-2 tags
    "florence_min_confidence": 0.60,
    # YOLO object categories that imply scene tags
    "yolo_scene_implications": {
        "animal:dog": ["outdoor"],
        "animal:cat": ["indoor"],
        "animal:bird": ["outdoor", "nature"],
        "animal:horse": ["outdoor", "nature"],
        "vehicle:car": ["outdoor", "street"],
        "vehicle:boat": ["water", "outdoor"],
        "sports:surfboard": ["beach", "water"],
        "sports:skis": ["snow", "mountain"],
        "plant:potted plant": ["indoor", "garden"],
    },
}


# Clustering configuration (industry-aligned defaults)
# These values are based on Google Photos / Apple Photos behavior
CLUSTERING_CONFIG = {
    # Minimum confidence to include face in clustering
    # 0.6 = reasonable threshold to avoid false positives
    "min_confidence": 0.6,
    
    # DBSCAN epsilon (distance threshold)
    # 0.5 = ~50% similarity required for same cluster
    # Lower = stricter (fewer false positives, more splits)
    # Higher = looser (more false positives, fewer splits)
    "eps": 0.5,
    
    # Minimum samples to form a cluster
    # 2 = allow pairs (reasonable for face clustering)
    # 1 = every face becomes a cluster (too aggressive)
    # 3+ = require more evidence (may miss valid identities)
    "min_samples": 2,
    
    # How to handle single-face clusters:
    # - Keep them as separate people (user can merge later)
    # - Rationale: Better to split than merge incorrectly
    "keep_single_face_clusters": True,
    
    # How to handle low-confidence faces:
    # - Exclude from clustering (don't create bad clusters)
    # - They remain unassigned for manual review
    "exclude_low_confidence_from_clustering": True,
    
    # Automatic reclustering triggers:
    # - Recluster when N new faces added (incremental clustering)
    # - Set to None to disable automatic reclustering
    "auto_recluster_threshold": 50,
}


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
        self.scene_detector = SceneDetector()  # Places365
        self.clip_scene_detector = CLIPSceneDetector()  # CLIP zero-shot
        self.florence_detector = FlorenceDetector()  # Florence-2 vision-language
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

        # Image embeddings: 768 dim (CLIP-Large), cosine similarity
        if not self.index.load_index("image"):
            self.index.create_index("image", dimension=768, metric="cosine")
            self.index.save_index("image")

        # Pet embeddings: 768 dim (CLIP-Large), cosine similarity
        # Separate index for pet identity clustering and similarity search
        if not self.index.load_index("pet"):
            self.index.create_index("pet", dimension=768, metric="cosine")
            self.index.save_index("pet")

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
        
        This performs face detection, object detection, pet detection, and embedding generation.
        Uses efficient detect_with_embeddings to do detection + embedding in one pass.
        """
        import logging
        
        results = {
            "photo_id": photo_id,
            "faces": [],
            "objects": [],
            "pets": [],
            "image_embedding_id": None,
        }

        # Check if file exists
        from pathlib import Path
        if not Path(photo_path).exists():
            return {"status": "error", "reason": "file_not_found"}

        # Detect faces AND generate embeddings in one pass (more efficient)
        face_detections = self.face_detector.detect_with_embeddings(photo_path)
        
        for face_data in face_detections:
            x, y, w, h = face_data['bbox']
            conf = face_data['confidence']
            embedding = face_data['embedding']
            
            # Store face in DB
            face_id = self.store.add_face(
                photo_id=photo_id,
                bbox_x=x,
                bbox_y=y,
                bbox_w=w,
                bbox_h=h,
                confidence=conf,
                embedding_id=None,  # Will update after storing embedding
            )

            # Store embedding in SQLite for retrieval
            self.store.store_embedding(face_id, embedding)
            
            # Update face with embedding reference
            self.store.update_face_embedding(face_id, face_id)

            # Add to FAISS index for similarity search
            self.index.add_vectors("face", embedding.reshape(1, -1), [face_id])

            results["faces"].append(face_id)

        # Save FAISS index after batch of faces
        if results["faces"]:
            self.index.save_index("face")

        # Detect objects
        try:
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
        except Exception as e:
            # Object detection is optional - don't fail if it errors
            logging.warning(f"Object detection failed for {photo_path}: {e}")

        # =====================================================================
        # PET DETECTION & EMBEDDING (for pet identity grouping)
        # =====================================================================
        try:
            # Detect animals using YOLO
            animal_detections = self.object_detector.detect_animals(photo_path, min_confidence=0.4)
            
            if animal_detections:
                # Load image for cropping
                img = cv2.imread(photo_path)
                if img is not None:
                    img_height, img_width = img.shape[:2]
                    
                    for x, y, w, h, species, conf in animal_detections:
                        # Add padding to crop (20% on each side)
                        padding = 0.2
                        pad_x = int(w * padding)
                        pad_y = int(h * padding)
                        
                        crop_x1 = max(0, x - pad_x)
                        crop_y1 = max(0, y - pad_y)
                        crop_x2 = min(img_width, x + w + pad_x)
                        crop_y2 = min(img_height, y + h + pad_y)
                        
                        # Crop pet region
                        pet_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
                        
                        # Skip tiny crops
                        if pet_crop.shape[0] < 32 or pet_crop.shape[1] < 32:
                            continue
                        
                        # Generate CLIP embedding for pet identity
                        pet_embedding = self.image_embedder.embed_crop(pet_crop)
                        
                        # Skip if embedding failed (zero vector)
                        if np.allclose(pet_embedding, 0):
                            continue
                        
                        # Store pet detection in DB
                        pet_detection_id = self.store.add_pet_detection(
                            photo_id=photo_id,
                            bbox_x=x,
                            bbox_y=y,
                            bbox_w=w,
                            bbox_h=h,
                            species=species,
                            confidence=conf,
                        )
                        
                        # Store embedding in SQLite
                        self.store.store_pet_embedding(pet_detection_id, pet_embedding)
                        
                        # Update detection with embedding reference
                        self.store.update_pet_detection_embedding(pet_detection_id, pet_detection_id)
                        
                        # Add to FAISS index for similarity search
                        self.index.add_vectors("pet", pet_embedding.reshape(1, -1), [pet_detection_id])
                        
                        results["pets"].append(pet_detection_id)
                    
                    # Save FAISS index after batch of pets
                    if results["pets"]:
                        self.index.save_index("pet")
                        
        except Exception as e:
            logging.warning(f"Pet detection failed for {photo_path}: {e}")

        # Generate image embedding (for semantic search)
        try:
            image_embedding = self.image_embedder.embed(photo_path)
            self.index.add_vectors("image", image_embedding.reshape(1, -1), [photo_id])
            self.index.save_index("image")
            results["image_embedding_id"] = photo_id
        except Exception as e:
            # Image embedding is optional
            logging.warning(f"Image embedding failed for {photo_path}: {e}")

        # =====================================================================
        # FUSED SCENE DETECTION (Places365 + CLIP + Florence-2 + YOLO evidence)
        # Industry-grade scene tagging similar to Google Photos / EYE
        # =====================================================================
        results["scenes"] = []
        try:
            fused_tags = self._detect_scenes_fused(photo_path, results.get("objects", []))
            
            # Store fused tags (deduplicated, capped)
            stored_tags = set()
            for tag, confidence, source in fused_tags:
                if tag not in stored_tags:
                    self.store.add_scene(
                        photo_id=photo_id,
                        scene_label=tag,
                        confidence=confidence
                    )
                    stored_tags.add(tag)
                    results["scenes"].append(tag)
            
            logging.info(f"Fused scene tags for {photo_path}: {results['scenes']}")
            
        except Exception as e:
            logging.warning(f"Scene detection failed for {photo_path}: {e}")
            results["scenes"] = []

        return results
    
    def _detect_scenes_fused(
        self, 
        image_path: str, 
        object_ids: List[int]
    ) -> List[Tuple[str, float, str]]:
        """
        Fused scene detection combining Places365, CLIP, Florence-2, and YOLO evidence.
        
        Args:
            image_path: Path to image
            object_ids: List of object IDs detected in this image
            
        Returns:
            List of (tag, confidence, source) tuples, sorted by confidence
            source is one of: 'places365', 'clip', 'florence', 'yolo'
        """
        import logging
        
        all_tags = []  # (tag, confidence, source)
        seen_tags = set()
        
        # =====================================================================
        # 1. Places365 Scene Detection
        # =====================================================================
        try:
            # Get simplified category tags
            places_tags = self.scene_detector.get_all_scene_tags(image_path)
            for tag in places_tags:
                if tag not in seen_tags:
                    all_tags.append((tag, 0.8, 'places365'))  # High confidence for categorical match
                    seen_tags.add(tag)
            
            # Get detailed detections with confidence
            detailed = self.scene_detector.detect(image_path, top_k=10)
            for scene_label, confidence in detailed:
                if confidence >= SCENE_FUSION_CONFIG["places365_min_confidence"]:
                    # Extract base tag from detailed label (e.g., "sky/sunset" -> "sunset")
                    parts = scene_label.split('/')
                    for part in parts:
                        clean_tag = part.lower().replace('_', ' ').strip()
                        if clean_tag and clean_tag not in seen_tags and len(clean_tag) > 2:
                            all_tags.append((clean_tag, confidence, 'places365'))
                            seen_tags.add(clean_tag)
        except Exception as e:
            logging.warning(f"Places365 scene detection failed: {e}")
        
        # =====================================================================
        # 2. CLIP Zero-Shot Scene Detection
        # =====================================================================
        try:
            clip_detections = self.clip_scene_detector.detect(image_path)
            for tag, confidence in clip_detections:
                if confidence >= SCENE_FUSION_CONFIG["clip_min_confidence"]:
                    if tag not in seen_tags:
                        all_tags.append((tag, confidence, 'clip'))
                        seen_tags.add(tag)
        except Exception as e:
            logging.warning(f"CLIP scene detection failed: {e}")
        
        # =====================================================================
        # 3. Florence-2 Vision-Language Tags
        # =====================================================================
        try:
            florence_detections = self.florence_detector.get_scene_tags(image_path)
            for tag, confidence in florence_detections:
                if confidence >= SCENE_FUSION_CONFIG["florence_min_confidence"]:
                    if tag not in seen_tags:
                        all_tags.append((tag, confidence, 'florence'))
                        seen_tags.add(tag)
        except Exception as e:
            logging.warning(f"Florence-2 scene detection failed: {e}")
        
        # =====================================================================
        # 4. YOLO Object Evidence -> Scene Implications
        # =====================================================================
        try:
            yolo_implications = SCENE_FUSION_CONFIG["yolo_scene_implications"]
            
            for obj_id in object_ids:
                obj = self.store.get_objects_for_photo(obj_id)
                # obj is a list, we need to check if any object implies a scene
                # Actually, object_ids here are object IDs, so we need to look them up differently
                pass
            
            # Instead, look up objects for the photo directly from results
            # The object_ids passed are already the IDs of detected objects
            for obj_id in object_ids:
                # Get the object's category from the objects table
                import sqlite3
                conn = sqlite3.connect(self.store.db_path, timeout=30)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT category FROM objects WHERE id = ?", (obj_id,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    category = row['category']
                    # Check if this category implies any scene tags
                    for pattern, implied_tags in yolo_implications.items():
                        if pattern in category:
                            for tag in implied_tags:
                                if tag not in seen_tags:
                                    all_tags.append((tag, 0.6, 'yolo'))  # Medium confidence
                                    seen_tags.add(tag)
        except Exception as e:
            logging.warning(f"YOLO scene implication failed: {e}")
        
        # =====================================================================
        # 5. Fusion: Sort by confidence, cap at max_tags
        # =====================================================================
        all_tags.sort(key=lambda x: x[1], reverse=True)
        
        max_tags = SCENE_FUSION_CONFIG["max_tags"]
        return all_tags[:max_tags]

    async def process_photo(self, photo_path: str) -> Dict:
        """
        Process a single photo: import metadata + ML processing.
        This is a convenience method that combines import_photo + process_photo_ml.
        """
        # Phase 1: Import with metadata
        import_result = await self.import_photo(photo_path)
        
        if import_result.get("status") == "skipped":
            return import_result
        
        photo_id = import_result.get("photo_id")
        if photo_id is None:
            return {"status": "error", "reason": "import_failed"}
        
        # Phase 2: ML processing
        ml_result = await self.process_photo_ml(photo_id, photo_path)
        
        return ml_result

    async def cluster_faces(
        self, 
        eps: float = None,
        min_samples: int = None,
        min_confidence: float = None
    ) -> Dict:
        """
        Cluster faces using DBSCAN with cosine distance.
        
        Edge case handling:
        1. Low-confidence faces: Excluded from clustering, remain unassigned
        2. Single-face clusters: Kept as separate people (user can merge)
        3. Noise faces: Unassigned, available for manual review
        4. Duplicate clusters: DBSCAN handles naturally via epsilon threshold
        
        Returns dict with clustering statistics.
        """
        import logging
        
        # Use config defaults if not specified
        eps = eps or CLUSTERING_CONFIG["eps"]
        min_samples = min_samples or CLUSTERING_CONFIG["min_samples"]
        min_confidence = min_confidence or CLUSTERING_CONFIG["min_confidence"]
        
        # Get all embeddings from database
        embeddings_data = self.store.get_all_embeddings_with_faces()
        
        if len(embeddings_data) < min_samples:
            logging.info(f"Not enough faces for clustering: {len(embeddings_data)} < {min_samples}")
            return {
                "status": "insufficient_data",
                "clusters": 0,
                "faces_clustered": 0,
                "noise": 0,
                "low_confidence": 0,
                "total": len(embeddings_data)
            }

        # Filter by confidence (EDGE CASE: exclude low-confidence faces)
        filtered_data = []
        low_confidence_count = 0
        
        for face_id, embedding in embeddings_data:
            face = self.store.get_face(face_id)
            if not face:
                continue
                
            if face.get('confidence', 0) >= min_confidence:
                filtered_data.append((face_id, embedding))
            else:
                low_confidence_count += 1
                # Clear assignments for low-confidence faces
                self.store.update_face_cluster(face_id, None)
                self.store.update_face_person(face_id, None)
        
        if len(filtered_data) < min_samples:
            logging.info(f"Not enough high-confidence faces: {len(filtered_data)} < {min_samples}")
            return {
                "status": "insufficient_confidence",
                "clusters": 0,
                "faces_clustered": 0,
                "noise": 0,
                "low_confidence": low_confidence_count,
                "total": len(embeddings_data)
            }

        # Extract face_ids and embeddings
        all_face_ids = [fid for fid, _ in filtered_data]
        all_embeddings = np.array([emb for _, emb in filtered_data])

        # Cluster using DBSCAN with cosine distance
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine", n_jobs=-1).fit(all_embeddings)
        
        labels = clustering.labels_
        unique_clusters = set(labels) - {-1}  # Exclude noise
        
        logging.info(f"Clustering complete: {len(unique_clusters)} clusters, {len(all_face_ids)} faces")

        # Assign cluster IDs to faces
        for face_id, cluster_label in zip(all_face_ids, labels):
            if cluster_label >= 0:  # Not noise
                self.store.update_face_cluster(face_id, int(cluster_label))
            else:
                # EDGE CASE: Noise - clear cluster assignment
                self.store.update_face_cluster(face_id, -1)

        # Create person entries for each cluster
        # EDGE CASE: Single-face clusters are OK (keep_single_face_clusters=True)
        # IMPORTANT: Reuse existing people with same cluster_id to avoid duplicates
        cluster_to_person = {}
        single_face_clusters = 0
        new_people_created = 0
        existing_people_reused = 0
        
        for cluster_label in unique_clusters:
            # Count faces in this cluster
            cluster_face_count = sum(1 for label in labels if label == cluster_label)
            
            if cluster_face_count == 1:
                single_face_clusters += 1
            
            # Check if person with this cluster_id already exists
            existing_person = self.store.get_person_by_cluster_id(int(cluster_label))
            
            if existing_person:
                # Reuse existing person to avoid duplicates
                person_id = existing_person['id']
                existing_people_reused += 1
                logging.info(f"Reusing existing person {person_id} for cluster {cluster_label}")
            else:
                # Create new person (even for single-face clusters)
                # Rationale: Better to split than incorrectly merge
                person_id = self.store.create_person(
                    cluster_id=int(cluster_label),
                    name=None  # No default name - let UI assign
                )
                new_people_created += 1
                logging.info(f"Created new person {person_id} for cluster {cluster_label}")
            
            cluster_to_person[cluster_label] = person_id

        # Assign faces to people based on clusters
        for face_id, cluster_label in zip(all_face_ids, labels):
            if cluster_label >= 0:  # Not noise
                person_id = cluster_to_person[cluster_label]
                self.store.update_face_person(face_id, person_id)
            else:
                # EDGE CASE: Noise - unassign person
                self.store.update_face_person(face_id, None)

        # Statistics
        noise_count = sum(1 for label in labels if label == -1)
        faces_clustered = len(all_face_ids) - noise_count

        return {
            "status": "success",
            "clusters": len(unique_clusters),
            "faces_clustered": faces_clustered,
            "noise": noise_count,
            "low_confidence": low_confidence_count,
            "single_face_clusters": single_face_clusters,
            "new_people_created": new_people_created,
            "existing_people_reused": existing_people_reused,
            "total_processed": len(all_face_ids),
            "total_faces": len(embeddings_data)
        }

    async def search_similar_images(self, query_text: str, k: int = 10) -> List[int]:
        """Search for similar images using text query."""
        query_embedding = self.image_embedder.embed_text(query_text)
        distances, photo_ids = self.index.search("image", query_embedding, k=k)
        return [int(pid) for pid in photo_ids if pid >= 0]

    async def search_similar_faces(self, face_id: int, k: int = 10) -> List[Dict]:
        """
        Search for similar faces using FAISS k-NN search.
        Returns list of similar faces with similarity scores.
        """
        # Retrieve embedding for query face
        embedding = self.store.get_embedding(face_id)
        if embedding is None:
            return []

        # Search FAISS index
        distances, similar_face_ids = self.index.search("face", embedding, k=k + 1)  # +1 to exclude self
        
        # Build results with metadata
        results = []
        for distance, similar_face_id in zip(distances, similar_face_ids):
            if similar_face_id < 0 or similar_face_id == face_id:
                continue  # Skip invalid or self
            
            face = self.store.get_face(int(similar_face_id))
            if face:
                # Convert distance to similarity score (0-1, higher = more similar)
                # For cosine distance: similarity = 1 - distance
                similarity = max(0.0, 1.0 - float(distance))
                
                results.append({
                    'face_id': int(similar_face_id),
                    'photo_id': face['photo_id'],
                    'similarity': similarity,
                    'confidence': face['confidence'],
                    'person_id': face.get('person_id')
                })
        
        return results[:k]  # Return exactly k results
    
    async def rebuild_faiss_index(self) -> Dict:
        """
        Rebuild FAISS index from all embeddings in database.
        Useful after deletions or corruption.
        """
        import logging
        
        # Get all embeddings
        embeddings_data = self.store.get_all_embeddings_with_faces()
        
        if len(embeddings_data) == 0:
            logging.info("No embeddings to index")
            return {"status": "empty", "count": 0}

        # Recreate face index
        self.index.create_index("face", dimension=512, metric="cosine")
        
        # Add all embeddings
        face_ids = [fid for fid, _ in embeddings_data]
        embeddings = np.array([emb for _, emb in embeddings_data])
        
        self.index.add_vectors("face", embeddings, face_ids)
        self.index.save_index("face")
        
        logging.info(f"FAISS index rebuilt with {len(face_ids)} embeddings")
        
        return {"status": "success", "count": len(face_ids)}
    
    async def delete_face(self, face_id: int) -> Dict:
        """
        Delete a face from database and FAISS index.
        Note: FAISS doesn't support efficient removal, so we mark as deleted
        and rebuild index periodically.
        """
        # Delete from database (includes embedding)
        deleted = self.store.delete_face(face_id)
        
        if not deleted:
            return {"status": "not_found"}
        
        # For FAISS, we'd need to rebuild the index
        # In production, track deletions and rebuild periodically
        # For now, just mark as deleted in DB
        
        return {"status": "deleted", "face_id": face_id}
    
    async def should_auto_recluster(self) -> bool:
        """
        Check if automatic reclustering should be triggered.
        Returns True if there are enough new unclustered faces.
        """
        threshold = CLUSTERING_CONFIG.get("auto_recluster_threshold")
        if threshold is None:
            return False
        
        unclustered = self.store.get_faces_without_clusters()
        return len(unclustered) >= threshold
    
    async def recluster_person_faces(self, person_id: int, eps: float = 0.5, min_samples: int = 2) -> Dict:
        """
        Re-cluster faces for a specific person.
        Useful when merging people or correcting clusters.
        """
        # Get all faces for this person
        faces = self.store.get_faces_for_person(person_id)
        
        if len(faces) < min_samples:
            return {"status": "insufficient_faces", "count": len(faces)}
        
        # Get embeddings for these faces
        face_ids = []
        embeddings_list = []
        
        for face in faces:
            embedding = self.store.get_embedding(face['id'])
            if embedding is not None:
                face_ids.append(face['id'])
                embeddings_list.append(embedding)
        
        if len(embeddings_list) < min_samples:
            return {"status": "insufficient_embeddings", "count": len(embeddings_list)}
        
        embeddings = np.array(embeddings_list)
        
        # Run clustering
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit(embeddings)
        
        # Create new person entries for sub-clusters
        unique_clusters = set(clustering.labels_) - {-1}
        
        for cluster_label in unique_clusters:
            # Faces in this cluster
            cluster_face_ids = [fid for fid, label in zip(face_ids, clustering.labels_) if label == cluster_label]
            
            # If this is the main cluster, keep in original person
            # Otherwise, create new person
            if cluster_label == 0 and len(cluster_face_ids) > len(face_ids) // 2:
                # Main cluster - keep in original person
                self.store.update_faces_person(cluster_face_ids, person_id)
            else:
                # Split cluster - create new person
                new_person_id = self.store.create_person(name=f"Split from Person {person_id}")
                self.store.update_faces_person(cluster_face_ids, new_person_id)
        
        # Handle noise
        noise_face_ids = [fid for fid, label in zip(face_ids, clustering.labels_) if label == -1]
        if noise_face_ids:
            self.store.update_faces_person(noise_face_ids, None)
        
        return {
            "status": "reclustered",
            "original_person": person_id,
            "new_clusters": len(unique_clusters),
            "noise": len(noise_face_ids)
        }

    # =========================================================================
    # PET CLUSTERING METHODS (parallel to face clustering)
    # =========================================================================

    # Pet clustering configuration (similar to face clustering)
    PET_CLUSTERING_CONFIG = {
        "min_confidence": 0.4,  # Lower threshold for pets
        "eps": 0.4,  # Tighter clustering for pet identity (CLIP embeddings)
        "min_samples": 2,  # Allow pairs
        "keep_single_detection_clusters": False,  # Single-occurrence pets remain Unknown
        "auto_recluster_threshold": 20,  # Fewer pets than faces typically
    }

    async def cluster_pets(
        self,
        eps: float = None,
        min_samples: int = None,
        min_confidence: float = None
    ) -> Dict:
        """
        Cluster pet detections using DBSCAN with cosine distance.
        Creates pet identities similar to how face clustering creates people.
        
        Edge case handling:
        1. Single-detection pets: Remain "Unknown" (unlike faces)
        2. Low-confidence detections: Excluded from clustering
        3. Species-aware: Cluster within species (a dog can't cluster with a cat)
        """
        import logging
        
        # Use config defaults if not specified
        eps = eps or self.PET_CLUSTERING_CONFIG["eps"]
        min_samples = min_samples or self.PET_CLUSTERING_CONFIG["min_samples"]
        min_confidence = min_confidence or self.PET_CLUSTERING_CONFIG["min_confidence"]
        
        # Get all pet embeddings from database
        embeddings_data = self.store.get_all_pet_embeddings_with_detections()
        
        if len(embeddings_data) < min_samples:
            logging.info(f"Not enough pet detections for clustering: {len(embeddings_data)} < {min_samples}")
            return {
                "status": "insufficient_data",
                "clusters": 0,
                "pets_clustered": 0,
                "noise": 0,
                "total": len(embeddings_data)
            }

        # Filter by confidence and group by species
        species_groups = {}  # species -> [(detection_id, embedding)]
        low_confidence_count = 0
        
        for detection_id, embedding in embeddings_data:
            detection = self.store.get_pet_detection(detection_id)
            if not detection:
                continue
            
            if detection.get('confidence', 0) < min_confidence:
                low_confidence_count += 1
                # Clear assignments for low-confidence detections
                self.store.update_pet_detection_cluster(detection_id, None)
                self.store.update_pet_detection_pet(detection_id, None)
                continue
            
            species = detection.get('species', 'unknown')
            if species not in species_groups:
                species_groups[species] = []
            species_groups[species].append((detection_id, embedding))

        total_clustered = 0
        total_noise = 0
        total_clusters = 0
        new_pets_created = 0
        existing_pets_reused = 0

        # Cluster each species separately
        for species, detections in species_groups.items():
            if len(detections) < min_samples:
                # Not enough detections of this species - mark as noise
                for detection_id, _ in detections:
                    self.store.update_pet_detection_cluster(detection_id, -1)
                    self.store.update_pet_detection_pet(detection_id, None)
                total_noise += len(detections)
                continue
            
            detection_ids = [d[0] for d in detections]
            embeddings = np.array([d[1] for d in detections])
            
            # Cluster using DBSCAN with cosine distance
            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine", n_jobs=-1).fit(embeddings)
            
            labels = clustering.labels_
            unique_clusters = set(labels) - {-1}
            
            logging.info(f"Pet clustering for {species}: {len(unique_clusters)} clusters from {len(detection_ids)} detections")

            # Use species-specific cluster offset to avoid collision
            cluster_offset = total_clusters

            # Assign cluster IDs to detections
            for detection_id, cluster_label in zip(detection_ids, labels):
                if cluster_label >= 0:
                    # Use offset to make cluster_id unique across species
                    global_cluster_id = cluster_offset + cluster_label
                    self.store.update_pet_detection_cluster(detection_id, global_cluster_id)
                else:
                    self.store.update_pet_detection_cluster(detection_id, -1)

            # Create pet entries for each cluster
            for cluster_label in unique_clusters:
                cluster_detection_count = sum(1 for label in labels if label == cluster_label)
                
                # Skip single-detection clusters (remain Unknown)
                if cluster_detection_count == 1 and not self.PET_CLUSTERING_CONFIG["keep_single_detection_clusters"]:
                    # Mark as noise
                    for detection_id, label in zip(detection_ids, labels):
                        if label == cluster_label:
                            self.store.update_pet_detection_cluster(detection_id, -1)
                            self.store.update_pet_detection_pet(detection_id, None)
                    total_noise += 1
                    continue
                
                global_cluster_id = cluster_offset + cluster_label
                
                # Check if pet with this cluster_id already exists
                existing_pet = self.store.get_pet_by_cluster_id(global_cluster_id)
                
                if existing_pet:
                    pet_id = existing_pet['id']
                    existing_pets_reused += 1
                else:
                    # Create new pet identity
                    pet_id = self.store.create_pet(
                        cluster_id=global_cluster_id,
                        name=None,  # User can name later
                        species=species
                    )
                    new_pets_created += 1
                    logging.info(f"Created new pet {pet_id} (species={species}) for cluster {global_cluster_id}")

                # Assign detections to pet
                for detection_id, label in zip(detection_ids, labels):
                    if label == cluster_label:
                        self.store.update_pet_detection_pet(detection_id, pet_id)
                        total_clustered += 1

            # Count noise for this species
            species_noise = sum(1 for label in labels if label == -1)
            total_noise += species_noise
            
            # Handle noise detections
            for detection_id, label in zip(detection_ids, labels):
                if label == -1:
                    self.store.update_pet_detection_pet(detection_id, None)

            total_clusters += len(unique_clusters)

        return {
            "status": "success",
            "clusters": total_clusters,
            "pets_clustered": total_clustered,
            "noise": total_noise,
            "low_confidence": low_confidence_count,
            "new_pets_created": new_pets_created,
            "existing_pets_reused": existing_pets_reused,
            "total_detections": len(embeddings_data),
            "species_processed": list(species_groups.keys())
        }

    async def search_similar_pets(self, pet_detection_id: int, k: int = 10) -> List[Dict]:
        """
        Search for similar pet detections using FAISS k-NN search.
        Returns list of similar pet detections with similarity scores.
        """
        # Retrieve embedding for query pet detection
        embedding = self.store.get_pet_embedding(pet_detection_id)
        if embedding is None:
            return []

        # Search FAISS index
        distances, similar_ids = self.index.search("pet", embedding, k=k + 1)  # +1 to exclude self
        
        # Build results with metadata
        results = []
        for distance, similar_id in zip(distances, similar_ids):
            if similar_id < 0 or similar_id == pet_detection_id:
                continue
            
            detection = self.store.get_pet_detection(int(similar_id))
            if detection:
                # Convert distance to similarity (for cosine: similarity = 1 - distance)
                similarity = max(0.0, 1.0 - float(distance))
                
                results.append({
                    'pet_detection_id': int(similar_id),
                    'photo_id': detection['photo_id'],
                    'similarity': similarity,
                    'species': detection['species'],
                    'confidence': detection['confidence'],
                    'pet_id': detection.get('pet_id')
                })
        
        return results[:k]

    async def rebuild_pet_faiss_index(self) -> Dict:
        """
        Rebuild pet FAISS index from all pet embeddings in database.
        """
        import logging
        
        embeddings_data = self.store.get_all_pet_embeddings_with_detections()
        
        if len(embeddings_data) == 0:
            logging.info("No pet embeddings to index")
            return {"status": "empty", "count": 0}

        # Recreate pet index
        self.index.create_index("pet", dimension=768, metric="cosine")
        
        detection_ids = [did for did, _ in embeddings_data]
        embeddings = np.array([emb for _, emb in embeddings_data])
        
        self.index.add_vectors("pet", embeddings, detection_ids)
        self.index.save_index("pet")
        
        logging.info(f"Pet FAISS index rebuilt with {len(detection_ids)} embeddings")
        
        return {"status": "success", "count": len(detection_ids)}

    async def should_auto_recluster_pets(self) -> bool:
        """
        Check if automatic pet reclustering should be triggered.
        """
        threshold = self.PET_CLUSTERING_CONFIG.get("auto_recluster_threshold")
        if threshold is None:
            return False
        
        unclustered = self.store.count_pet_detections_without_clusters()
        return unclustered >= threshold
