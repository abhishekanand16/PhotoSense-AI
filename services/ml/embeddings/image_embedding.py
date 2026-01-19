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
        Generate embedding for an image.
        Returns: 512-dimensional embedding vector.
        """
        self._load_model()

        image = Image.open(image_path).convert("RGB")
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
        Returns: 512-dimensional embedding vector.
        """
        self._load_model()

        inputs = self.processor(text=text, return_tensors="pt", padding=True).to(self.device)

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            embedding = text_features[0].cpu().numpy()

        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.astype(np.float32)
