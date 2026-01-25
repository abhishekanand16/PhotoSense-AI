# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
import asyncio
import os
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
from services.ml.utils.path_utils import validate_photo_path
from services.ml.utils import extract_exif_metadata
from services.config import (
    CACHE_DIR,
    CLUSTERING_CONFIG,
    DB_PATH,
    INDICES_DIR,
    PET_CLUSTERING_CONFIG,
    SCENE_FUSION_CONFIG,
)


class MLPipeline:

    def __init__(
        self,
        db_path: str = str(DB_PATH),
        index_dir: str = str(INDICES_DIR),
        cache_dir: str = str(CACHE_DIR),
    ):
        self.store = SQLiteStore(db_path)
        self.index = FAISSIndex(index_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Essential models - load immediately (lightweight)
        self._face_detector = FaceDetector()
        self._object_detector = ObjectDetector()
        self._face_embedder = FaceEmbedder()
        
        # Deferred models - load on first use (heavyweight)
        self._scene_detector: Optional[SceneDetector] = None
        self._clip_scene_detector: Optional[CLIPSceneDetector] = None
        self._florence_detector: Optional[FlorenceDetector] = None
        self._image_embedder: Optional[ImageEmbedder] = None

        # Load or create indices
        self._init_indices()
    
    # =========================================================================
    # LAZY LOADING PROPERTIES - Load heavy models on first access
    # =========================================================================
    
    @property
    def face_detector(self) -> FaceDetector:
        return self._face_detector
    
    @property
    def object_detector(self) -> ObjectDetector:
        return self._object_detector
    
    @property
    def face_embedder(self) -> FaceEmbedder:
        return self._face_embedder
    
    @property
    def scene_detector(self) -> SceneDetector:
        if self._scene_detector is None:
            self._scene_detector = SceneDetector()
        return self._scene_detector
    
    @property
    def clip_scene_detector(self) -> CLIPSceneDetector:
        if self._clip_scene_detector is None:
            self._clip_scene_detector = CLIPSceneDetector()
        return self._clip_scene_detector
    
    @property
    def florence_detector(self) -> FlorenceDetector:
        if self._florence_detector is None:
            self._florence_detector = FlorenceDetector()
        return self._florence_detector
    
    @property
    def image_embedder(self) -> ImageEmbedder:
        if self._image_embedder is None:
            self._image_embedder = ImageEmbedder()
        return self._image_embedder

    def _init_indices(self) -> None:
        """Initialize FAISS indices with auto-rebuild support."""
        import logging
        
        # Register rebuild callbacks for auto-recovery from corruption
        self.index.register_rebuild_callback("face", self._get_face_embeddings_for_rebuild)
        self.index.register_rebuild_callback("pet", self._get_pet_embeddings_for_rebuild)
        # Note: image index rebuild requires re-processing photos, not stored in DB
        
        # Face embeddings: 512 dim, cosine similarity
        if not self.index.load_index("face"):
            # Check if this is a corruption case
            rebuild_result = self.index.auto_rebuild_if_corrupted("face")
            if rebuild_result["action"] == "failed" or rebuild_result["action"] == "none":
                self.index.create_index("face", dimension=512, metric="cosine")
                self.index.save_index("face")
            logging.info(f"Face index init: {rebuild_result}")

        # Image embeddings: 768 dim (CLIP-Large), cosine similarity
        if not self.index.load_index("image"):
            self.index.create_index("image", dimension=768, metric="cosine")
            self.index.save_index("image")

        # Pet embeddings: 768 dim (CLIP-Large), cosine similarity
        # Separate index for pet identity clustering and similarity search
        if not self.index.load_index("pet"):
            rebuild_result = self.index.auto_rebuild_if_corrupted("pet")
            if rebuild_result["action"] == "failed" or rebuild_result["action"] == "none":
                self.index.create_index("pet", dimension=768, metric="cosine")
                self.index.save_index("pet")
            logging.info(f"Pet index init: {rebuild_result}")
    
    def _get_face_embeddings_for_rebuild(self) -> List[Tuple[int, np.ndarray]]:
        """Get all face embeddings from database for FAISS rebuild."""
        return self.store.get_all_embeddings_with_faces()
    
    def _get_pet_embeddings_for_rebuild(self) -> List[Tuple[int, np.ndarray]]:
        """Get all pet embeddings from database for FAISS rebuild."""
        return self.store.get_all_pet_embeddings_with_detections()

    def import_photo_metadata_only_sync(self, photo_path: str) -> Dict:
        """
        SYNCHRONOUS version of import - designed to run in thread pool.
        Fast import with EXIF metadata only, no ML processing.
        
        This is Phase 1 of the decoupled import process:
        - Extract EXIF metadata
        - Add to database
        - Photos immediately visible in dashboard
        - NO ML operations (face/object detection happens later)
        """
        # Validate path for safety (prevents traversal/symlink attacks)
        try:
            validated_path = validate_photo_path(photo_path)
            photo_path = str(validated_path)
        except ValueError as e:
            return {"status": "error", "reason": str(e)}
        
        # Extract EXIF metadata
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
            # Photo already exists - get existing photo
            existing_photo = self.store.get_photo_by_path(photo_path)
            if existing_photo:
                photo_id = existing_photo["id"]
                
                # Store location if GPS coordinates are available and not already stored
                if metadata.get("latitude") is not None and metadata.get("longitude") is not None:
                    existing_location = self.store.get_location(photo_id)
                    if not existing_location:
                        self.store.add_location(
                            photo_id=photo_id,
                            latitude=metadata["latitude"],
                            longitude=metadata["longitude"]
                        )
                
                return {"status": "exists", "photo_id": photo_id}
            else:
                return {"status": "skipped", "reason": "duplicate"}

        # Store location if GPS coordinates are available
        if metadata.get("latitude") is not None and metadata.get("longitude") is not None:
            self.store.add_location(
                photo_id=photo_id,
                latitude=metadata["latitude"],
                longitude=metadata["longitude"]
            )

        return {
            "status": "imported",
            "photo_id": photo_id,
            "date_taken": metadata.get("date_taken"),
            "has_location": metadata.get("latitude") is not None,
        }

    def process_photo_ml_sync(self, photo_id: int, photo_path: str) -> Dict:
        """
        SYNCHRONOUS ML processing - designed to run in thread pool.
        
        This is Phase 2 of the decoupled process:
        - Face detection + embeddings
        - Object detection  
        - Pet detection + embeddings
        - Scene detection (Florence-2, CLIP, Places365)
        - Image embeddings
        
        All operations are intentionally synchronous so they can run
        in a ThreadPoolExecutor without blocking the async event loop.
        """
        import logging
        from services.ml.utils.image_cache import get_image_cache

        results: Dict = {
            "photo_id": photo_id,
            "faces": [],
            "objects": [],
            "pets": [],
            "scenes": [],
            "image_embedding_id": None,
        }

        # Validate path for safety
        try:
            validated_path = validate_photo_path(photo_path)
            photo_path = str(validated_path)
        except ValueError as e:
            logging.error(f"Invalid photo path: {e}")
            try:
                self.store.mark_photo_ml_error(photo_id, str(e))
            except Exception:
                pass
            return {"status": "error", "reason": str(e), **results}

        # Skip already-processed photos (prevents rescanning)
        try:
            if self.store.is_photo_ml_processed(photo_id):
                return {"status": "skipped", "reason": "already_processed", **results}
        except Exception:
            pass

        image_cache = get_image_cache()
        try:
            cached = image_cache.decode_image(photo_path)
            if cached is None:
                logging.error(f"Could not decode image: {photo_path}")
                try:
                    self.store.mark_photo_ml_error(photo_id, "decode_failed")
                except Exception:
                    pass
                return {"status": "error", "reason": "decode_failed", **results}

            # Extract cached images and scale factors
            face_image = cached["face_bgr"]
            face_scale = cached["scale_factors"]["face"]
            ml_image_bgr = cached["ml_bgr"]
            ml_image_rgb = cached["ml_rgb"]
            ml_scale = cached["scale_factors"]["ml"]
            florence_image = cached["florence_rgb"]
            original_bgr = cached["original_bgr"]

            # FACE DETECTION (with embeddings)
            face_detections = self.face_detector.detect_with_embeddings(
                photo_path,
                image_bgr=face_image,
                scale_factor=face_scale,
            )

            faces_for_faiss = []
            auto_assigned_count = 0
            for face_data in face_detections:
                x, y, w, h = face_data["bbox"]
                conf = face_data["confidence"]
                embedding = face_data["embedding"]

                auto_person_id = None
                if conf >= CLUSTERING_CONFIG["min_confidence"]:
                    try:
                        auto_person_id = self._find_matching_person(embedding)
                        if auto_person_id:
                            auto_assigned_count += 1
                    except Exception as e:
                        logging.warning(f"Identity matching failed: {str(e)}")

                face_id = self.store.add_face_with_embedding(
                    photo_id=photo_id,
                    bbox_x=x,
                    bbox_y=y,
                    bbox_w=w,
                    bbox_h=h,
                    confidence=conf,
                    embedding=embedding,
                    person_id=auto_person_id,
                )

                faces_for_faiss.append((face_id, embedding))
                results["faces"].append(face_id)

            for face_id, embedding in faces_for_faiss:
                self.index.add_vectors("face", embedding.reshape(1, -1), [face_id])

            # OBJECT DETECTION
            try:
                object_detections = self.object_detector.detect(
                    photo_path,
                    image_bgr=ml_image_bgr,
                    scale_factor=ml_scale,
                )
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
                logging.warning(f"Object detection failed for {photo_path}: {e}")

            # PET DETECTION & EMBEDDING
            try:
                animal_detections = self.object_detector.detect_animals(
                    photo_path,
                    min_confidence=0.4,
                    image_bgr=ml_image_bgr,
                    scale_factor=ml_scale,
                )

                if animal_detections:
                    img = original_bgr
                    img_height, img_width = img.shape[:2]
                    pets_for_faiss = []

                    for x, y, w, h, species, conf in animal_detections:
                        padding = 0.2
                        pad_x = int(w * padding)
                        pad_y = int(h * padding)

                        crop_x1 = max(0, x - pad_x)
                        crop_y1 = max(0, y - pad_y)
                        crop_x2 = min(img_width, x + w + pad_x)
                        crop_y2 = min(img_height, y + h + pad_y)

                        pet_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
                        if pet_crop.shape[0] < 32 or pet_crop.shape[1] < 32:
                            continue

                        pet_embedding = self.image_embedder.embed_crop(pet_crop)
                        if np.allclose(pet_embedding, 0):
                            continue

                        pet_detection_id = self.store.add_pet_detection_with_embedding(
                            photo_id=photo_id,
                            bbox_x=x,
                            bbox_y=y,
                            bbox_w=w,
                            bbox_h=h,
                            species=species,
                            confidence=conf,
                            embedding=pet_embedding,
                        )

                        pets_for_faiss.append((pet_detection_id, pet_embedding))
                        results["pets"].append(pet_detection_id)

                    for pet_detection_id, pet_embedding in pets_for_faiss:
                        self.index.add_vectors("pet", pet_embedding.reshape(1, -1), [pet_detection_id])
            except Exception as e:
                logging.warning(f"Pet detection failed for {photo_path}: {e}")

            # IMAGE EMBEDDING
            try:
                image_embedding = self.image_embedder.embed_pil(ml_image_rgb)
                self.index.add_vectors("image", image_embedding.reshape(1, -1), [photo_id])
                results["image_embedding_id"] = photo_id
            except Exception as e:
                logging.warning(f"Image embedding failed for {photo_path}: {e}")

            # FUSED SCENE DETECTION
            try:
                fused_tags = self._detect_scenes_fused(
                    photo_path,
                    results.get("objects", []),
                    ml_image_rgb=ml_image_rgb,
                    florence_image_rgb=florence_image,
                )

                stored_tags = set()
                for tag, confidence, source in fused_tags:
                    if tag in stored_tags:
                        continue
                    self.store.add_scene(photo_id=photo_id, scene_label=tag, confidence=confidence)
                    stored_tags.add(tag)
                    results["scenes"].append(tag)

                # Store Florence tags separately for precise object UI fallback
                florence_prefix = "florence:"
                stored_florence_tags = set()
                for tag, confidence, source in fused_tags:
                    if source != "florence":
                        continue
                    prefixed_tag = f"{florence_prefix}{tag}"
                    if prefixed_tag in stored_florence_tags:
                        continue
                    self.store.add_scene(photo_id=photo_id, scene_label=prefixed_tag, confidence=confidence)
                    stored_florence_tags.add(prefixed_tag)
            except Exception as e:
                logging.warning(f"Scene detection failed for {photo_path}: {e}")
                results["scenes"] = []

            # Mark processed
            try:
                self.store.mark_photo_ml_processed(photo_id)
            except Exception:
                pass
            
            results["status"] = "processed"
            return results
        except Exception as e:
            logging.error(f"Fatal ML processing error for {photo_path}: {e}", exc_info=True)
            try:
                self.store.mark_photo_ml_error(photo_id, str(e))
            except Exception:
                pass
            return {"status": "error", "reason": str(e), **results}
        finally:
            try:
                image_cache.clear(photo_path)
            except Exception:
                pass

    async def import_photo(self, photo_path: str) -> Dict:
        """Import a photo with metadata only (no face/object detection).
        
        This is Phase 1 of the import process - fast import that allows photos
        to appear in the dashboard immediately, grouped by date.
        """
        # Validate path for safety (prevents traversal/symlink attacks)
        try:
            validated_path = validate_photo_path(photo_path)
            photo_path = str(validated_path)
        except ValueError as e:
            return {"status": "error", "reason": str(e)}
        
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
                
                # Store location if GPS coordinates are available and not already stored
                if metadata.get("latitude") is not None and metadata.get("longitude") is not None:
                    existing_location = self.store.get_location(photo_id)
                    if not existing_location:
                        self.store.add_location(
                            photo_id=photo_id,
                            latitude=metadata["latitude"],
                            longitude=metadata["longitude"]
                        )
                
                return {"status": "exists", "photo_id": photo_id, "updated": needs_update}
            else:
                return {"status": "skipped", "reason": "duplicate"}

        # Store location if GPS coordinates are available
        if metadata.get("latitude") is not None and metadata.get("longitude") is not None:
            self.store.add_location(
                photo_id=photo_id,
                latitude=metadata["latitude"],
                longitude=metadata["longitude"]
            )

        return {
            "status": "imported",
            "photo_id": photo_id,
            "date_taken": metadata.get("date_taken"),
            "has_location": metadata.get("latitude") is not None,
        }

    async def process_photo_ml(self, photo_id: int, photo_path: str) -> Dict:
        """Process ML features for an already-imported photo (Phase 2).
        
        This performs face detection, object detection, pet detection, and embedding generation.
        Uses efficient detect_with_embeddings to do detection + embedding in one pass.
        
        OPTIMIZATION: Single image decode shared across all ML models via ImageCache.
        """
        import logging
        from services.ml.utils.image_cache import get_image_cache

        results: Dict = {
            "photo_id": photo_id,
            "faces": [],
            "objects": [],
            "pets": [],
            "scenes": [],
            "image_embedding_id": None,
        }

        # Validate path for safety
        try:
            validated_path = validate_photo_path(photo_path)
            photo_path = str(validated_path)
        except ValueError as e:
            logging.error(f"Invalid photo path: {e}")
            try:
                self.store.mark_photo_ml_error(photo_id, str(e))
            except Exception:
                pass
            return {"status": "error", "reason": str(e), **results}

        # Skip already-processed photos (prevents rescanning)
        try:
            if self.store.is_photo_ml_processed(photo_id):
                return {"status": "skipped", "reason": "already_processed", **results}
        except Exception:
            # If schema is older or check fails, proceed with processing.
            pass

        image_cache = get_image_cache()
        try:
            cached = image_cache.decode_image(photo_path)
            if cached is None:
                logging.error(f"Could not decode image: {photo_path}")
                try:
                    self.store.mark_photo_ml_error(photo_id, "decode_failed")
                except Exception:
                    pass
                return {"status": "error", "reason": "decode_failed", **results}

            # Extract cached images and scale factors
            face_image = cached["face_bgr"]
            face_scale = cached["scale_factors"]["face"]
            ml_image_bgr = cached["ml_bgr"]
            ml_image_rgb = cached["ml_rgb"]
            ml_scale = cached["scale_factors"]["ml"]
            florence_image = cached["florence_rgb"]
            original_bgr = cached["original_bgr"]

            # =======================================================================
            # FACE DETECTION (with embeddings)
            # =======================================================================
            face_detections = self.face_detector.detect_with_embeddings(
                photo_path,
                image_bgr=face_image,
                scale_factor=face_scale,
            )

            faces_for_faiss = []
            auto_assigned_count = 0
            for face_data in face_detections:
                x, y, w, h = face_data["bbox"]
                conf = face_data["confidence"]
                embedding = face_data["embedding"]

                auto_person_id = None
                if conf >= CLUSTERING_CONFIG["min_confidence"]:
                    try:
                        auto_person_id = self._find_matching_person(embedding)
                        if auto_person_id:
                            auto_assigned_count += 1
                            logging.info(f"Auto-assigned face to person {auto_person_id} (similarity match)")
                    except Exception as e:
                        logging.warning(f"Identity matching failed: {str(e)}")

                face_id = self.store.add_face_with_embedding(
                    photo_id=photo_id,
                    bbox_x=x,
                    bbox_y=y,
                    bbox_w=w,
                    bbox_h=h,
                    confidence=conf,
                    embedding=embedding,
                    person_id=auto_person_id,
                )

                faces_for_faiss.append((face_id, embedding))
                results["faces"].append(face_id)

            for face_id, embedding in faces_for_faiss:
                self.index.add_vectors("face", embedding.reshape(1, -1), [face_id])

            if auto_assigned_count > 0:
                logging.info(f"Auto-assigned {auto_assigned_count} faces to known people")

            # =======================================================================
            # OBJECT DETECTION (optional)
            # =======================================================================
            try:
                object_detections = self.object_detector.detect(
                    photo_path,
                    image_bgr=ml_image_bgr,
                    scale_factor=ml_scale,
                )
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
                logging.warning(f"Object detection failed for {photo_path}: {e}")

            # =====================================================================
            # PET DETECTION & EMBEDDING (optional)
            # =====================================================================
            try:
                animal_detections = self.object_detector.detect_animals(
                    photo_path,
                    min_confidence=0.4,
                    image_bgr=ml_image_bgr,
                    scale_factor=ml_scale,
                )

                if animal_detections:
                    img = original_bgr
                    img_height, img_width = img.shape[:2]
                    pets_for_faiss = []

                    for x, y, w, h, species, conf in animal_detections:
                        padding = 0.2
                        pad_x = int(w * padding)
                        pad_y = int(h * padding)

                        crop_x1 = max(0, x - pad_x)
                        crop_y1 = max(0, y - pad_y)
                        crop_x2 = min(img_width, x + w + pad_x)
                        crop_y2 = min(img_height, y + h + pad_y)

                        pet_crop = img[crop_y1:crop_y2, crop_x1:crop_x2]
                        if pet_crop.shape[0] < 32 or pet_crop.shape[1] < 32:
                            continue

                        pet_embedding = self.image_embedder.embed_crop(pet_crop)
                        if np.allclose(pet_embedding, 0):
                            continue

                        pet_detection_id = self.store.add_pet_detection_with_embedding(
                            photo_id=photo_id,
                            bbox_x=x,
                            bbox_y=y,
                            bbox_w=w,
                            bbox_h=h,
                            species=species,
                            confidence=conf,
                            embedding=pet_embedding,
                        )

                        pets_for_faiss.append((pet_detection_id, pet_embedding))
                        results["pets"].append(pet_detection_id)

                    for pet_detection_id, pet_embedding in pets_for_faiss:
                        self.index.add_vectors("pet", pet_embedding.reshape(1, -1), [pet_detection_id])
            except Exception as e:
                logging.warning(f"Pet detection failed for {photo_path}: {e}")

            # =======================================================================
            # IMAGE EMBEDDING (optional)
            # =======================================================================
            try:
                image_embedding = self.image_embedder.embed_pil(ml_image_rgb)
                self.index.add_vectors("image", image_embedding.reshape(1, -1), [photo_id])
                results["image_embedding_id"] = photo_id
            except Exception as e:
                logging.warning(f"Image embedding failed for {photo_path}: {e}")

            # =====================================================================
            # FUSED SCENE DETECTION (optional)
            # =====================================================================
            try:
                fused_tags = self._detect_scenes_fused(
                    photo_path,
                    results.get("objects", []),
                    ml_image_rgb=ml_image_rgb,
                    florence_image_rgb=florence_image,
                )

                stored_tags = set()
                for tag, confidence, source in fused_tags:
                    if tag in stored_tags:
                        continue
                    self.store.add_scene(photo_id=photo_id, scene_label=tag, confidence=confidence)
                    stored_tags.add(tag)
                    results["scenes"].append(tag)

                # Store Florence tags separately for precise object UI fallback
                florence_prefix = "florence:"
                stored_florence_tags = set()
                for tag, confidence, source in fused_tags:
                    if source != "florence":
                        continue
                    prefixed_tag = f"{florence_prefix}{tag}"
                    if prefixed_tag in stored_florence_tags:
                        continue
                    self.store.add_scene(photo_id=photo_id, scene_label=prefixed_tag, confidence=confidence)
                    stored_florence_tags.add(prefixed_tag)
            except Exception as e:
                logging.warning(f"Scene detection failed for {photo_path}: {e}")
                results["scenes"] = []

            # Mark processed (even if optional detectors failed) to prevent rescans
            try:
                self.store.mark_photo_ml_processed(photo_id)
            except Exception:
                pass
            results["status"] = "processed"
            return results
        except Exception as e:
            logging.error(f"Fatal ML processing error for {photo_path}: {e}", exc_info=True)
            try:
                self.store.mark_photo_ml_error(photo_id, str(e))
            except Exception:
                pass
            return {"status": "error", "reason": str(e), **results}
        finally:
            try:
                image_cache.clear(photo_path)
            except Exception:
                pass
    
    def _detect_scenes_fused(
        self, 
        image_path: str, 
        object_ids: List[int],
        ml_image_rgb: Optional['Image.Image'] = None,
        florence_image_rgb: Optional['Image.Image'] = None
    ) -> List[Tuple[str, float, str]]:
        """
        Fused scene detection combining Places365, CLIP, Florence-2, and YOLO evidence.
        
        Args:
            image_path: Path to image
            object_ids: List of object IDs detected in this image
            ml_image_rgb: Optional pre-decoded PIL RGB image for Places365/CLIP
            florence_image_rgb: Optional pre-decoded PIL RGB image for Florence-2
            
        Returns:
            List of (tag, confidence, source) tuples, sorted by confidence
            source is one of: 'places365', 'clip', 'florence', 'yolo'
        """
        import logging
        
        all_tags = []  # (tag, confidence, source)
        seen_tags = set()
        
        # =====================================================================
        # 1. Places365 Scene Detection (with pre-decoded image)
        # =====================================================================
        try:
            # Get simplified category tags
            places_tags = self.scene_detector.get_all_scene_tags(image_path, image_rgb=ml_image_rgb)
            for tag in places_tags:
                if tag not in seen_tags:
                    all_tags.append((tag, 0.8, 'places365'))  # High confidence for categorical match
                    seen_tags.add(tag)
            
            # Get detailed detections with confidence
            detailed = self.scene_detector.detect(image_path, top_k=10, image_rgb=ml_image_rgb)
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
        # 2. CLIP Zero-Shot Scene Detection (with pre-decoded image)
        # =====================================================================
        try:
            clip_detections = self.clip_scene_detector.detect(image_path, image_rgb=ml_image_rgb)
            for tag, confidence in clip_detections:
                if confidence >= SCENE_FUSION_CONFIG["clip_min_confidence"]:
                    if tag not in seen_tags:
                        all_tags.append((tag, confidence, 'clip'))
                        seen_tags.add(tag)
        except Exception as e:
            logging.warning(f"CLIP scene detection failed: {e}")
        
        # =====================================================================
        # 3. Florence-2 Vision-Language Tags (with pre-decoded image)
        # =====================================================================
        try:
            generic_filter = SCENE_FUSION_CONFIG.get("generic_tags_filter", set())
            florence_detections = self.florence_detector.get_scene_tags(image_path, image_rgb=florence_image_rgb)
            for tag, confidence in florence_detections:
                # Filter generic tags and apply confidence threshold
                if confidence >= SCENE_FUSION_CONFIG["florence_min_confidence"]:
                    if tag not in seen_tags and tag not in generic_filter:
                        all_tags.append((tag, confidence, 'florence'))
                        seen_tags.add(tag)
        except Exception as e:
            logging.warning(f"Florence-2 scene detection failed: {e}")
        
        # =====================================================================
        # 4. YOLO Object Evidence -> Scene Implications
        # =====================================================================
        try:
            yolo_implications = SCENE_FUSION_CONFIG["yolo_scene_implications"]

            # object_ids are object table IDs; look up each category and apply implications.
            for obj_id in object_ids:
                category = self.store.get_object_category(obj_id)
                if not category:
                    continue

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

        filtered_data = []
        low_confidence_count = 0
        
        for face_id, embedding in embeddings_data:
            face = self.store.get_face(face_id)
            if not face:
                continue
            if face.get("suppressed"):
                continue
            if face.get("person_locked") and face.get("person_id") is not None:
                continue
            if face.get('confidence', 0) >= min_confidence:
                filtered_data.append((face_id, embedding))
            else:
                low_confidence_count += 1
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

    async def search_similar_images(
        self, 
        query_text: str, 
        k: int = 10,
        min_similarity: float = 0.20,
        return_scores: bool = False
    ) -> List:
        """
        Search for similar images using text query with similarity filtering.
        
        Args:
            query_text: Natural language query
            k: Maximum number of results to return
            min_similarity: Minimum cosine similarity threshold (0-1).
                           Results below this threshold are filtered out.
                           - 0.30+ = Strong match (very relevant)
                           - 0.20-0.30 = Moderate match (somewhat relevant)
                           - <0.20 = Weak match (filtered out as noise)
            return_scores: If True, returns list of (photo_id, similarity) tuples.
                          If False (default), returns list of photo_ids only.
        
        Returns:
            If return_scores=False: List of photo IDs that match the query
            If return_scores=True: List of (photo_id, similarity) tuples
        """
        import logging
        
        query_embedding = self.image_embedder.embed_text(query_text)
        
        # Get more candidates than k to account for filtering
        # Request 3x candidates to have enough after threshold filtering
        candidates_k = min(k * 3, 150)
        scores, photo_ids = self.index.search("image", query_embedding, k=candidates_k)
        
        # Filter by similarity threshold
        # FAISS IndexFlatIP with normalized vectors returns cosine similarity directly
        # The "distance" returned is actually the inner product = cosine similarity
        # Range: -1 to 1, where 1 = identical, 0 = orthogonal, -1 = opposite
        filtered_results = []
        for score, pid in zip(scores, photo_ids):
            if pid < 0:
                continue
            
            # Score IS the cosine similarity (inner product of normalized vectors)
            similarity = float(score)
            
            if similarity >= min_similarity:
                filtered_results.append((int(pid), similarity))
                logging.debug(f"CLIP match: photo_id={pid}, similarity={similarity:.3f}")
            else:
                logging.debug(f"CLIP filtered out: photo_id={pid}, similarity={similarity:.3f} < {min_similarity}")
        
        # Sort by similarity (highest first) and return top k
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        filtered_results = filtered_results[:k]
        
        logging.info(f"CLIP search '{query_text}': {len(filtered_results)} results above threshold {min_similarity} (from {candidates_k} candidates)")
        
        if return_scores:
            return filtered_results
        else:
            return [pid for pid, _ in filtered_results]

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

    def _find_matching_person(
        self,
        embedding: np.ndarray,
        similarity_threshold: float = 0.70,
        min_matches: int = 1,
    ) -> Optional[int]:
        """
        Find a matching person for a face embedding using FAISS similarity search.
        
        This is the core of PERSISTENT IDENTITY LEARNING:
        - After a merge, the merged person has multiple face embeddings
        - New face embeddings are compared against ALL known faces in FAISS
        - If a strong match is found to a face that belongs to a person, auto-assign
        
        Args:
            embedding: The face embedding to match (512-dim numpy array)
            similarity_threshold: Minimum cosine similarity to consider a match (0-1)
                                 0.70 = high confidence, avoids false positives
            min_matches: Minimum number of matching faces to confirm identity
        
        Returns:
            person_id if a match is found, None otherwise
        """
        import logging
        
        # Search FAISS for similar faces
        # Use higher k to find multiple matches for the same person
        k = 10
        distances, similar_face_ids = self.index.search("face", embedding, k=k)
        
        if len(similar_face_ids) == 0:
            return None
        
        # Count matches per person_id above the similarity threshold
        person_matches = {}  # person_id -> list of similarities
        
        for distance, similar_face_id in zip(distances, similar_face_ids):
            if similar_face_id < 0:
                continue
            
            # Convert distance to similarity (FAISS IndexFlatIP returns inner product)
            # For normalized vectors, this IS the cosine similarity
            similarity = float(distance)
            
            if similarity < similarity_threshold:
                continue
            
            # Get the face and check if it has a person_id
            face = self.store.get_face(int(similar_face_id))
            if not face:
                continue
            
            person_id = face.get("person_id")
            if person_id is None:
                continue
            
            if person_id not in person_matches:
                person_matches[person_id] = []
            person_matches[person_id].append(similarity)
        
        if not person_matches:
            return None
        
        # Find the person with the most matches (and highest average similarity)
        best_person_id = None
        best_score = 0
        
        for person_id, similarities in person_matches.items():
            if len(similarities) >= min_matches:
                avg_similarity = sum(similarities) / len(similarities)
                # Score = number of matches * average similarity
                score = len(similarities) * avg_similarity
                
                if score > best_score:
                    best_score = score
                    best_person_id = person_id
        
        if best_person_id:
            logging.info(
                f"Identity match found: person_id={best_person_id}, "
                f"matches={len(person_matches[best_person_id])}, "
                f"best_similarity={max(person_matches[best_person_id]):.3f}"
            )
        
        return best_person_id
    
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
        Includes transactional safety and automatic cleanup of orphaned people.
        """
        import logging
        
        # TRANSACTIONAL SAFETY: Delete from DB first, then FAISS
        # Step 1: Delete from database and get person_id for orphan cleanup
        deletion_result = self.store.delete_face(face_id)
        
        if not deletion_result["deleted"]:
            return {"status": "not_found"}
        
        # Step 2: Remove embedding from FAISS index
        try:
            self.index.load_index("face")
            self.index.remove_vectors("face", [face_id])
            self.index.save_index("face")
            logging.info(f"Removed face {face_id} from FAISS index")
        except Exception as e:
            logging.error(f"Failed to remove face {face_id} from FAISS: {str(e)}")
            # Continue - FAISS can be rebuilt later if needed
        
        # Step 3: Clean up orphaned person if this was their last face
        orphaned_people = []
        if deletion_result["person_id"]:
            try:
                orphaned_people = self.store.cleanup_orphaned_people()
                if orphaned_people:
                    logging.info(f"Cleaned up {len(orphaned_people)} orphaned people: {orphaned_people}")
            except Exception as e:
                logging.error(f"Failed to clean up orphaned people: {str(e)}")
        
        return {
            "status": "deleted", 
            "face_id": face_id,
            "person_cleaned_up": deletion_result["person_id"] in orphaned_people if deletion_result["person_id"] else False
        }
    
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
        eps = eps or PET_CLUSTERING_CONFIG["eps"]
        min_samples = min_samples or PET_CLUSTERING_CONFIG["min_samples"]
        min_confidence = min_confidence or PET_CLUSTERING_CONFIG["min_confidence"]
        
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
                if cluster_detection_count == 1 and not PET_CLUSTERING_CONFIG["keep_single_detection_clusters"]:
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
        threshold = PET_CLUSTERING_CONFIG.get("auto_recluster_threshold")
        if threshold is None:
            return False
        
        unclustered = self.store.count_pet_detections_without_clusters()
        return unclustered >= threshold
