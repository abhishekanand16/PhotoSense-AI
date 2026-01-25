# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
"""Global image embedding for semantic search using CLIP."""

from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


class ImageEmbedder:
    """Generate image embeddings using CLIP for semantic search."""

    def __init__(self, model_name: str = "openai/clip-vit-large-patch14"):
        """Initialize CLIP embedder with larger, more accurate model."""
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # CLIP large model has 768 dimensions (more expressive than base's 512)
        self.embedding_dim = 768

    def _load_model(self) -> None:
        """Lazy load CLIP model."""
        if self.model is None:
            self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.eval()

    def embed(self, image_path: str) -> np.ndarray:
        """
        Generate embedding for an image from file.
        Returns: 768-dimensional embedding vector (CLIP-Large).
        """
        self._load_model()

        try:
            image = Image.open(image_path).convert("RGB")
            return self._embed_pil_internal(image)
        except Exception as e:
            import logging
            logging.error(f"Image embedding failed for {image_path}: {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def embed_pil(self, image: Image.Image) -> np.ndarray:
        """
        Generate embedding for a pre-decoded PIL Image.
        Used when image is already in memory (from ImageCache).
        Returns: 768-dimensional embedding vector (CLIP-Large).
        """
        self._load_model()

        try:
            return self._embed_pil_internal(image)
        except Exception as e:
            import logging
            logging.error(f"PIL image embedding failed: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def _embed_pil_internal(self, image: Image.Image) -> np.ndarray:
        """Internal method to embed a PIL image."""
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            embedding = image_features[0].cpu().numpy()

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for text query.
        Returns: 768-dimensional embedding vector (CLIP-Large).
        """
        self._load_model()

        try:
            inputs = self.processor(text=text, return_tensors="pt", padding=True).to(self.device)

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                embedding = text_features[0].cpu().numpy()

            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            return embedding.astype(np.float32)
        except Exception as e:
            import logging
            logging.error(f"Text embedding failed for '{text}': {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def embed_crop(self, image_crop: np.ndarray) -> np.ndarray:
        """
        Generate embedding for an image crop (numpy array BGR format from cv2).
        Used for pet identity embeddings from cropped detection regions.
        Returns: 768-dimensional embedding vector (CLIP-Large).
        """
        import cv2
        self._load_model()

        try:
            # Convert BGR (cv2) to RGB (PIL)
            if len(image_crop.shape) == 3 and image_crop.shape[2] == 3:
                rgb_crop = cv2.cvtColor(image_crop, cv2.COLOR_BGR2RGB)
            else:
                rgb_crop = image_crop
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_crop)
            
            inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                embedding = image_features[0].cpu().numpy()

            # Normalize
            embedding = embedding / np.linalg.norm(embedding)
            return embedding.astype(np.float32)
        except Exception as e:
            import logging
            logging.error(f"Crop embedding failed: {e}")
            # Return zero vector as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def embed_texts_batch(self, texts: list) -> np.ndarray:
        """
        Generate embeddings for multiple text prompts (batch).
        Used for CLIP zero-shot classification.
        Returns: (N, 768) array of normalized embeddings.
        """
        self._load_model()

        try:
            inputs = self.processor(text=texts, return_tensors="pt", padding=True).to(self.device)

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                embeddings = text_features.cpu().numpy()

            # Normalize each embedding
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            return embeddings.astype(np.float32)
        except Exception as e:
            import logging
            logging.error(f"Batch text embedding failed: {e}")
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
