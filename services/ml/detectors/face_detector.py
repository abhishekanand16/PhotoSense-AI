"""Face detection using InsightFace (ONNX-based)."""

from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

# Apply fast face alignment patch BEFORE any InsightFace usage
from services.ml.utils.face_align_patch import apply_patch
apply_patch()


class FaceDetector:
    """Face detection and alignment using InsightFace ONNX model."""

    def __init__(self, confidence_threshold: float = 0.6, model_name: str = "buffalo_l"):
        """
        Initialize face detector.
        
        Args:
            confidence_threshold: Minimum confidence score (0.6 is reasonable for face detection)
            model_name: InsightFace model name (buffalo_l includes detection + landmarks)
        """
        self.confidence_threshold = confidence_threshold
        self.model_name = model_name
        self.app = None  # Lazy loading

    def _load_model(self) -> None:
        """Lazy load the InsightFace model."""
        if self.app is None:
            # Load detection + recognition for full pipeline (includes alignment)
            self.app = FaceAnalysis(
                name=self.model_name,
                allowed_modules=['detection', 'recognition'],  # Need recognition for embeddings
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(ctx_id=-1, det_size=(640, 640))

    def detect(self, image_path: str) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect faces in an image.
        Returns list of (x, y, width, height, confidence) tuples.
        """
        self._load_model()
        image = cv2.imread(image_path)
        if image is None:
            return []

        faces = self.app.get(image)

        results = []
        for face in faces:
            confidence = float(face.det_score)
            
            if confidence >= self.confidence_threshold:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                results.append((int(x1), int(y1), int(width), int(height), confidence))

        return results
    
    def detect_with_embeddings(
        self, 
        image_path: str,
        image_bgr: Optional[np.ndarray] = None,
        scale_factor: float = 1.0
    ) -> List[Dict]:
        """
        Detect faces and generate embeddings in one pass.
        More efficient than separate detection + embedding.
        
        Args:
            image_path: Path to image (for logging purposes if image_bgr provided)
            image_bgr: Optional pre-decoded BGR image (from ImageCache)
            scale_factor: Scale factor to map bboxes back to original coordinates
        
        Returns list of dicts with:
        - bbox: (x, y, width, height) in ORIGINAL image coordinates
        - confidence: detection confidence
        - embedding: 512-dim face embedding (aligned internally by InsightFace)
        - landmarks: facial landmarks (5 points: left_eye, right_eye, nose, mouth_left, mouth_right)
        """
        import logging
        
        self._load_model()
        
        # Use pre-decoded image if provided, otherwise load from disk
        if image_bgr is not None:
            image = image_bgr
        else:
            image = cv2.imread(image_path)
            if image is None:
                logging.warning(f"Could not read image: {image_path}")
                return []

        try:
            faces = self.app.get(image)
        except Exception as e:
            logging.error(f"Face detection failed for {image_path}: {e}")
            return []

        results = []
        inv_scale = 1.0 / scale_factor if scale_factor != 1.0 else 1.0
        
        for face in faces:
            confidence = float(face.det_score)
            
            if confidence >= self.confidence_threshold:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                
                # Scale bbox back to original image coordinates
                if scale_factor != 1.0:
                    x1 = int(x1 * inv_scale)
                    y1 = int(y1 * inv_scale)
                    width = int(width * inv_scale)
                    height = int(height * inv_scale)
                
                # Extract embedding (already aligned by InsightFace)
                embedding = face.embedding
                
                # Skip faces without embeddings (recognition model not loaded)
                if embedding is None:
                    logging.warning(f"No embedding generated for face in {image_path} - recognition model may not be loaded")
                    continue
                
                # Normalize embedding
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                else:
                    logging.warning(f"Zero-norm embedding for face in {image_path}")
                    continue
                
                # Extract landmarks (5 key points) and scale them
                landmarks = None
                if hasattr(face, 'kps') and face.kps is not None:
                    if scale_factor != 1.0:
                        landmarks = [[int(x * inv_scale), int(y * inv_scale)] for x, y in face.kps]
                    else:
                        landmarks = face.kps.astype(int).tolist()
                
                results.append({
                    'bbox': (int(x1), int(y1), int(width), int(height)),
                    'confidence': confidence,
                    'embedding': embedding.astype(np.float32),
                    'landmarks': landmarks
                })
        
        logging.info(f"Detected {len(results)} faces with embeddings in {image_path}")
        return results
