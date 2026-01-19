"""Face detection using InsightFace (ONNX-based)."""

from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis


class FaceDetector:
    """Face detection using InsightFace ONNX model (no TensorFlow)."""

    def __init__(self, confidence_threshold: float = 0.7, model_name: str = "buffalo_l"):
        """
        Initialize face detector.
        
        Args:
            confidence_threshold: Minimum confidence score for detections
            model_name: InsightFace model name (buffalo_l, antelopev2, etc.)
        """
        self.confidence_threshold = confidence_threshold
        self.model_name = model_name
        self.app = None  # Lazy loading

    def _load_model(self) -> None:
        """Lazy load the InsightFace model."""
        if self.app is None:
            # Load only detection module (faster, no recognition/attributes)
            # Model name is specified in FaceAnalysis constructor
            self.app = FaceAnalysis(
                name=self.model_name,
                allowed_modules=['detection'],
                providers=['CPUExecutionProvider']  # Use CPU (ONNX runtime)
            )
            # Prepare the model (downloads if needed)
            # ctx_id=-1 means CPU, det_size is detection resolution
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

        # InsightFace detection
        faces = self.app.get(image)

        results = []
        for face in faces:
            confidence = float(face.det_score)
            
            if confidence >= self.confidence_threshold:
                # InsightFace bbox format: [x1, y1, x2, y2]
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                width = x2 - x1
                height = y2 - y1
                results.append((int(x1), int(y1), int(width), int(height), confidence))

        return results
