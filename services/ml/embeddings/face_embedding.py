"""Face embedding generation using ArcFace (InsightFace)."""

from typing import Optional

import cv2
import numpy as np
from insightface.app import FaceAnalysis


class FaceEmbedder:
    """Generate face embeddings using InsightFace ArcFace model."""

    def __init__(self, model_name: str = "buffalo_l"):
        """
        Initialize face embedder.
        Uses InsightFace's ArcFace model via ONNX runtime.
        
        Args:
            model_name: InsightFace model pack (buffalo_l includes recognition)
        """
        self.model_name = model_name
        self.app = None  # Lazy loading
        self.embedding_dim = 512  # ArcFace produces 512-dim embeddings

    def _load_model(self) -> None:
        """Lazy load the InsightFace model with recognition."""
        if self.app is None:
            # Load with recognition module for ArcFace embeddings
            self.app = FaceAnalysis(
                name=self.model_name,
                allowed_modules=['detection', 'recognition'],  # Include recognition for embeddings
                providers=['CPUExecutionProvider']
            )
            self.app.prepare(ctx_id=-1, det_size=(640, 640))

    def embed(self, face_image: np.ndarray) -> np.ndarray:
        """
        Generate embedding for a face image.
        
        Args:
            face_image: BGR numpy array of face region (can be cropped or full image)
            
        Returns:
            512-dimensional normalized embedding vector
        """
        self._load_model()
        
        # InsightFace expects full image, detects and aligns internally
        faces = self.app.get(face_image)
        
        if len(faces) == 0:
            # No face detected - return zero embedding
            # In production, this should be handled at detection stage
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Use first face (assume face_image contains single face)
        face = faces[0]
        embedding = face.embedding
        
        # Normalize embedding (InsightFace may already normalize, but ensure it)
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding.astype(np.float32)
    
    def embed_aligned(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Generate embedding from pre-aligned face (112x112 RGB).
        
        Args:
            aligned_face: Pre-aligned face image (112x112, RGB or BGR)
            
        Returns:
            512-dimensional normalized embedding vector
        """
        # For pre-aligned faces, we still use InsightFace's full pipeline
        # as it handles the alignment internally. This method is kept for API compatibility.
        return self.embed(aligned_face)
