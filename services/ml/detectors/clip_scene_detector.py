"""Scene detection using CLIP (alternative to Places365)."""

from typing import List, Tuple
import logging

import torch
import numpy as np
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


class CLIPSceneDetector:
    """Scene detection using CLIP zero-shot classification."""
    
    # Scene categories to detect
    SCENE_CATEGORIES = [
        'sunset', 'sunrise', 'beach', 'ocean', 'seashore',
        'mountain', 'mountains', 'hill',
        'forest', 'woods', 'jungle', 'trees',
        'garden', 'botanical garden', 'flower garden',
        'flowers', 'blooming flowers',
        'nature', 'natural landscape', 'wilderness',
        'park', 'public park', 'playground',
        'lake', 'river', 'waterfall', 'pond', 'water',
        'city', 'urban', 'cityscape', 'street',
        'building', 'architecture', 'skyscraper',
        'indoor', 'interior', 'room',
        'outdoor', 'outside', 'exterior',
        'sky', 'clouds', 'blue sky',
        'night', 'nighttime', 'evening',
        'snow', 'snowy', 'winter',
        'desert', 'sand', 'dunes',
        'field', 'meadow', 'grassland',
    ]
    
    # Simplified category mapping
    CATEGORY_MAPPING = {
        'sunset': 'sunset',
        'sunrise': 'sunrise',
        'beach': 'beach',
        'ocean': 'beach',
        'seashore': 'beach',
        'mountain': 'mountain',
        'mountains': 'mountain',
        'hill': 'mountain',
        'forest': 'forest',
        'woods': 'forest',
        'jungle': 'forest',
        'trees': 'tree',
        'garden': 'garden',
        'botanical garden': 'garden',
        'flower garden': 'flowers',
        'flowers': 'flowers',
        'blooming flowers': 'flowers',
        'nature': 'nature',
        'natural landscape': 'nature',
        'wilderness': 'nature',
        'park': 'park',
        'public park': 'park',
        'playground': 'park',
        'lake': 'water',
        'river': 'water',
        'waterfall': 'water',
        'pond': 'water',
        'water': 'water',
        'city': 'city',
        'urban': 'city',
        'cityscape': 'city',
        'street': 'city',
        'building': 'building',
        'architecture': 'building',
        'skyscraper': 'building',
        'indoor': 'indoor',
        'interior': 'indoor',
        'room': 'indoor',
        'outdoor': 'outdoor',
        'outside': 'outdoor',
        'exterior': 'outdoor',
        'sky': 'sky',
        'clouds': 'sky',
        'blue sky': 'sky',
        'night': 'night',
        'nighttime': 'night',
        'evening': 'night',
        'snow': 'snow',
        'snowy': 'snow',
        'winter': 'snow',
        'desert': 'landscape',
        'sand': 'landscape',
        'dunes': 'landscape',
        'field': 'nature',
        'meadow': 'nature',
        'grassland': 'nature',
    }

    def __init__(self, model_name: str = "openai/clip-vit-large-patch14", confidence_threshold: float = 0.15):
        """Initialize CLIP scene detector."""
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self) -> None:
        """Lazy load CLIP model."""
        if self.model is not None:
            return
            
        try:
            self.model = CLIPModel.from_pretrained(self.model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.eval()
            logging.info("CLIP scene detector loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load CLIP scene detector: {e}")
            self.model = None

    def detect(self, image_path: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Detect scenes in an image using CLIP zero-shot classification.
        
        Args:
            image_path: Path to image file
            top_k: Number of top predictions to return
            
        Returns:
            List of (scene_label, confidence) tuples
        """
        self._load_model()
        
        if self.model is None:
            logging.warning(f"CLIP scene detector not available, skipping detection for {image_path}")
            return []
        
        try:
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Create text prompts
            text_prompts = [f"a photo of {category}" for category in self.SCENE_CATEGORIES]
            
            # Process inputs
            inputs = self.processor(
                text=text_prompts,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
            
            # Get top predictions
            top_indices = np.argsort(probs)[::-1][:top_k * 2]  # Get more to filter
            
            scenes = []
            seen_categories = set()
            
            for idx in top_indices:
                if len(scenes) >= top_k:
                    break
                    
                confidence = float(probs[idx])
                if confidence < self.confidence_threshold:
                    continue
                
                scene_label = self.SCENE_CATEGORIES[idx]
                simplified = self.CATEGORY_MAPPING.get(scene_label, scene_label)
                
                # Avoid duplicate simplified categories
                if simplified not in seen_categories:
                    scenes.append((scene_label, confidence))
                    seen_categories.add(simplified)
            
            logging.info(f"Detected {len(scenes)} scenes in {image_path}")
            return scenes
            
        except Exception as e:
            logging.error(f"CLIP scene detection failed for {image_path}: {e}")
            return []
    
    def get_all_scene_tags(self, image_path: str) -> List[str]:
        """
        Get all relevant scene tags for an image.
        
        Returns:
            List of simplified scene category tags
        """
        scenes = self.detect(image_path, top_k=10)
        
        if not scenes:
            return []
        
        tags = set()
        for scene_label, confidence in scenes:
            simplified = self.CATEGORY_MAPPING.get(scene_label, scene_label)
            tags.add(simplified)
        
        return sorted(list(tags))
    
    def get_primary_scene(self, image_path: str) -> Tuple[str, float]:
        """
        Get the primary scene category for an image.
        
        Returns:
            (scene_category, confidence)
        """
        scenes = self.detect(image_path, top_k=1)
        
        if not scenes:
            return ('unknown', 0.0)
        
        scene_label, confidence = scenes[0]
        simplified = self.CATEGORY_MAPPING.get(scene_label, scene_label)
        
        return (simplified, confidence)
