# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
"""CLIP-based zero-shot scene classification for scenery/environment recognition."""

from typing import Dict, List, Tuple, Optional
import logging

import numpy as np
from PIL import Image


class CLIPSceneDetector:
    """
    Zero-shot scene classification using CLIP.
    
    This complements Places365 by:
    1. Detecting scenes Places365 might miss (e.g., "sunset", "golden hour")
    2. Providing semantic scene understanding with natural language prompts
    3. Being more flexible and contextual
    """
    
    # Scene prompts for zero-shot classification
    # Format: (tag_name, [prompts]) - multiple prompts per tag for robustness
    SCENE_PROMPTS = {
        # Time of day / lighting
        'sunset': [
            'a photo of a sunset',
            'a photo taken during sunset with orange sky',
            'a beautiful sunset scene',
            'golden hour photography',
        ],
        'sunrise': [
            'a photo of a sunrise',
            'a photo taken at dawn',
            'early morning sunrise',
        ],
        'night': [
            'a nighttime photo',
            'a photo taken at night',
            'night sky photography',
            'a dark scene at night',
        ],
        'golden_hour': [
            'golden hour lighting',
            'warm golden light photography',
        ],
        
        # Nature scenes
        'beach': [
            'a photo of a beach',
            'a sandy beach with ocean',
            'a tropical beach scene',
            'waves on a beach',
        ],
        'ocean': [
            'a photo of the ocean',
            'ocean waves',
            'sea view photography',
        ],
        'mountain': [
            'a photo of mountains',
            'a mountain landscape',
            'mountain scenery',
            'snow-capped mountains',
        ],
        'forest': [
            'a photo of a forest',
            'trees in a forest',
            'a dense forest scene',
            'woodland photography',
        ],
        'trees': [
            'a photo with trees',
            'trees in nature',
            'a tree-lined scene',
        ],
        'flowers': [
            'a photo of flowers',
            'colorful flowers',
            'a flower garden',
            'blooming flowers',
        ],
        'lake': [
            'a photo of a lake',
            'a calm lake scene',
            'lake reflection photography',
        ],
        'river': [
            'a photo of a river',
            'a flowing river',
            'river scenery',
        ],
        'waterfall': [
            'a photo of a waterfall',
            'a cascading waterfall',
        ],
        'desert': [
            'a desert landscape',
            'sand dunes',
            'a dry desert scene',
        ],
        'snow': [
            'a snowy scene',
            'snow-covered landscape',
            'winter snow photography',
        ],
        'meadow': [
            'a meadow with grass',
            'a grassy field',
            'green meadow',
        ],
        
        # Sky features
        'sky': [
            'a photo with beautiful sky',
            'dramatic sky',
            'cloudy sky',
        ],
        'clouds': [
            'a photo of clouds',
            'fluffy clouds in the sky',
            'dramatic cloud formations',
        ],
        'rainbow': [
            'a photo of a rainbow',
            'rainbow in the sky',
        ],
        
        # Urban scenes
        'city': [
            'a city scene',
            'urban cityscape',
            'city buildings',
            'downtown area',
        ],
        'street': [
            'a street scene',
            'city street photography',
            'urban street',
        ],
        'building': [
            'a photo of a building',
            'architecture photography',
            'a large building',
        ],
        
        # Indoor/Outdoor
        'outdoor': [
            'an outdoor scene',
            'outside photography',
            'outdoor environment',
        ],
        'indoor': [
            'an indoor scene',
            'inside a room',
            'indoor photography',
        ],
        
        # Special scenes
        'landscape': [
            'a landscape photo',
            'scenic landscape',
            'nature landscape photography',
        ],
        'garden': [
            'a garden scene',
            'a beautiful garden',
            'garden photography',
        ],
        'park': [
            'a park scene',
            'a public park',
            'park with greenery',
        ],
    }
    
    # Confidence thresholds
    MIN_CONFIDENCE = 0.25  # Minimum confidence to include a tag
    MAX_TAGS = 5  # Maximum number of CLIP tags per image
    
    def __init__(self):
        """Initialize CLIP scene detector."""
        self._embedder = None
        self._prompt_embeddings = None
        self._tag_names = None
    
    def _get_embedder(self):
        """Lazy load CLIP embedder."""
        if self._embedder is None:
            from services.ml.embeddings.image_embedding import ImageEmbedder
            self._embedder = ImageEmbedder()
        return self._embedder
    
    def _get_prompt_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """
        Get or compute prompt embeddings.
        Returns (embeddings array, list of tag names for each embedding).
        """
        if self._prompt_embeddings is not None:
            return self._prompt_embeddings, self._tag_names
        
        embedder = self._get_embedder()
        
        # Flatten prompts and track which tag each belongs to
        all_prompts = []
        tag_for_prompt = []
        
        for tag, prompts in self.SCENE_PROMPTS.items():
            for prompt in prompts:
                all_prompts.append(prompt)
                tag_for_prompt.append(tag)
        
        # Batch embed all prompts
        self._prompt_embeddings = embedder.embed_texts_batch(all_prompts)
        self._tag_names = tag_for_prompt
        
        logging.info(f"CLIP scene detector: computed {len(all_prompts)} prompt embeddings")
        
        return self._prompt_embeddings, self._tag_names
    
    def detect(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> List[Tuple[str, float]]:
        """
        Detect scene tags using CLIP zero-shot classification.
        
        Args:
            image_path: Path to image file (for logging if image_rgb provided)
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
            
        Returns:
            List of (tag_name, confidence) tuples, sorted by confidence
        """
        try:
            embedder = self._get_embedder()
            prompt_embeddings, tag_names = self._get_prompt_embeddings()
            
            # Get image embedding - use pre-decoded image if provided
            if image_rgb is not None:
                image_embedding = embedder.embed_pil(image_rgb)
            else:
                image_embedding = embedder.embed(image_path)
            
            if np.allclose(image_embedding, 0):
                logging.warning(f"CLIP scene detection failed - zero embedding for {image_path}")
                return []
            
            # Compute similarities (dot product of normalized vectors = cosine similarity)
            similarities = np.dot(prompt_embeddings, image_embedding)
            
            # Aggregate by tag (max similarity across prompts for each tag)
            tag_scores: Dict[str, float] = {}
            for tag_name, sim in zip(tag_names, similarities):
                current = tag_scores.get(tag_name, -1.0)
                if sim > current:
                    tag_scores[tag_name] = float(sim)
            
            # Convert to list and filter by threshold
            results = [
                (tag, score)
                for tag, score in tag_scores.items()
                if score >= self.MIN_CONFIDENCE
            ]
            
            # Sort by confidence and limit
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:self.MAX_TAGS]
            
            logging.info(f"CLIP scene detection: {len(results)} tags for {image_path}")
            return results
            
        except Exception as e:
            logging.error(f"CLIP scene detection failed for {image_path}: {e}")
            return []
    
    def get_scene_tags(self, image_path: str) -> List[str]:
        """
        Get scene tags (without confidence scores).
        
        Returns:
            List of tag names
        """
        detections = self.detect(image_path)
        return [tag for tag, _ in detections]
