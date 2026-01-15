"""Face embedding generation using ArcFace."""

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import onnxruntime as ort


class FaceEmbedder:
    """Generate face embeddings using ArcFace model."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize face embedder.
        Uses ONNX ArcFace model (will download if not provided).
        """
        self.model_path = model_path or "models/arcface_r50_v1.onnx"
        self.session = None
        self.input_size = (112, 112)  # ArcFace input size
        self.embedding_dim = 512

    def _load_model(self) -> None:
        """Lazy load the ONNX model."""
        if self.session is None:
            # For now, use a placeholder - in production, load actual ArcFace model
            # self.session = ort.InferenceSession(self.model_path)
            pass

    def _preprocess_face(self, face_image: np.ndarray) -> np.ndarray:
        """Preprocess face image for ArcFace."""
        # Resize to input size
        face_resized = cv2.resize(face_image, self.input_size)
        # Normalize to [0, 1] and convert to float32
        face_normalized = face_resized.astype(np.float32) / 255.0
        # Convert BGR to RGB
        face_rgb = cv2.cvtColor(face_normalized, cv2.COLOR_BGR2RGB)
        # Transpose to CHW format
        face_chw = np.transpose(face_rgb, (2, 0, 1))
        # Add batch dimension
        face_batch = np.expand_dims(face_chw, axis=0)
        return face_batch

    def embed(self, face_image: np.ndarray) -> np.ndarray:
        """
        Generate embedding for a face image.
        face_image: BGR numpy array of cropped face.
        Returns: 512-dimensional embedding vector.
        """
        self._load_model()
        preprocessed = self._preprocess_face(face_image)

        # Placeholder: In production, run through ONNX model
        # For now, return a random embedding for structure
        # output = self.session.run(None, {"input": preprocessed})[0]
        # embedding = output[0]
        # Normalize
        # embedding = embedding / np.linalg.norm(embedding)

        # Temporary: Generate a deterministic embedding based on image hash
        # This is just for structure - replace with real model
        img_hash = hash(face_image.tobytes()) % (2**32)
        np.random.seed(img_hash)
        embedding = np.random.randn(self.embedding_dim).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)

        return embedding
