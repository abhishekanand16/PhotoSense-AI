"""Face detection using InsightFace (ONNX-based)."""

from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis


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
    
    def detect_with_embeddings(self, image_path: str) -> List[Dict]:
        """
        Detect faces and generate embeddings in one pass.
        More efficient than separate detection + embedding.
        
        Returns list of dicts with:
        - bbox: (x, y, width, height)
        - confidence: detection confidence
        - embedding: 512-dim face embedding (aligned internally by InsightFace)
        - landmarks: facial landmarks (5 points: left_eye, right_eye, nose, mouth_left, mouth_right)
        """
        import logging
        
        self._load_model()
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
        for face in faces:
            confidence = float(face.det_score)
            
            if confidence >= self.confidence_threshold:
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                
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
                
                # Extract landmarks (5 key points)
                landmarks = face.kps.astype(int).tolist() if hasattr(face, 'kps') else None
                
                results.append({
                    'bbox': (int(x1), int(y1), int(width), int(height)),
                    'confidence': confidence,
                    'embedding': embedding.astype(np.float32),
                    'landmarks': landmarks
                })
        
        logging.info(f"Detected {len(results)} faces with embeddings in {image_path}")
        return results
