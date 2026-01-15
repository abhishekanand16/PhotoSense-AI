"""
Face embedding module for PhotoSense-AI.

Uses FaceNet (keras-facenet) to generate facial embeddings.
"""

import os
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List
from PIL import Image

try:
    from keras_facenet import FaceNet
except ImportError:
    raise ImportError(
        "keras-facenet not installed. Install with: pip install keras-facenet"
    )

logger = logging.getLogger(__name__)


class FaceEncoder:
    """Face encoder using FaceNet."""

    def __init__(self):
        """Initialize FaceNet model."""
        try:
            self.model = FaceNet()
            logger.info("FaceNet model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize FaceNet: {e}")
            raise

    def encode_face(self, face_image_path: str) -> Optional[np.ndarray]:
        """
        Generate embedding for a face image.

        Args:
            face_image_path: Path to cropped face image

        Returns:
            Face embedding as numpy array (128-dimensional) or None on error
        """
        try:
            # Load and preprocess image
            image = Image.open(face_image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize to 160x160 (FaceNet input size)
            image = image.resize((160, 160), Image.Resampling.LANCZOS)
            
            # Convert to numpy array and normalize
            pixels = np.asarray(image)
            
            # FaceNet expects images in range [0, 1] and shape (1, 160, 160, 3)
            pixels = pixels.astype('float32')
            pixels = pixels / 255.0
            pixels = np.expand_dims(pixels, axis=0)
            
            # Generate embedding
            embedding = self.model.embeddings(pixels)
            
            # Return as 1D array
            return embedding[0]

        except Exception as e:
            logger.error(f"Error encoding face from {face_image_path}: {e}")
            return None

    def save_embedding(
        self,
        embedding: np.ndarray,
        output_path: str
    ) -> bool:
        """
        Save embedding to disk as numpy file.

        Args:
            embedding: Face embedding array
            output_path: Path to save embedding (.npy file)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as numpy file
            np.save(output_path, embedding)
            
            return True

        except Exception as e:
            logger.error(f"Error saving embedding to {output_path}: {e}")
            return False

    def load_embedding(self, embedding_path: str) -> Optional[np.ndarray]:
        """
        Load embedding from disk.

        Args:
            embedding_path: Path to embedding file (.npy)

        Returns:
            Face embedding array or None on error
        """
        try:
            embedding = np.load(embedding_path)
            return embedding
        except Exception as e:
            logger.error(f"Error loading embedding from {embedding_path}: {e}")
            return None

    def process_face(
        self,
        face_image_path: str,
        output_dir: str
    ) -> Optional[str]:
        """
        Generate and save embedding for a face image.

        Args:
            face_image_path: Path to cropped face image
            output_dir: Directory to save embedding

        Returns:
            Path to saved embedding file or None on error
        """
        # Generate embedding
        embedding = self.encode_face(face_image_path)
        
        if embedding is None:
            return None
        
        # Generate output filename
        face_stem = Path(face_image_path).stem
        embedding_filename = f"{face_stem}.npy"
        embedding_path = os.path.join(output_dir, embedding_filename)
        
        # Save embedding
        success = self.save_embedding(embedding, embedding_path)
        
        if success:
            return embedding_path
        else:
            return None
