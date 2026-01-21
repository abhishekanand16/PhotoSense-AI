"""Scene detection using Places365-CNN."""

from pathlib import Path
from typing import List, Tuple, Optional
import logging

import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np


class SceneDetector:
    """Scene detection using Places365 ResNet50."""
    
    # Top scene categories relevant for photo search
    RELEVANT_SCENES = {
        'sunset': ['sky/sunset', 'beach/sunset', 'mountain/sunset'],
        'sunrise': ['sky/sunrise'],
        'beach': ['beach', 'coast', 'sandbar', 'seashore'],
        'mountain': ['mountain', 'mountain_snowy', 'mountain_path', 'valley/mountain'],
        'forest': ['forest/broadleaf', 'forest_path', 'forest_road', 'bamboo_forest', 'rainforest'],
        'tree': ['tree_farm', 'orchard', 'forest', 'woods'],
        'nature': ['field/cultivated', 'field/wild', 'meadow', 'pasture', 'hayfield'],
        'garden': ['botanical_garden', 'formal_garden', 'vegetable_garden', 'herb_garden', 'rose_garden'],
        'flowers': ['flower_garden', 'rose_garden', 'botanical_garden'],
        'city': ['street', 'skyscraper', 'downtown', 'building_facade', 'plaza'],
        'indoor': ['living_room', 'bedroom', 'kitchen', 'dining_room', 'office'],
        'park': ['park', 'formal_garden', 'botanical_garden', 'playground'],
        'water': ['lake/natural', 'river', 'waterfall', 'ocean', 'pond'],
        'snow': ['ski_slope', 'snowfield', 'ice_skating_rink/outdoor'],
        'night': ['sky/night', 'street/night'],
        'building': ['church/outdoor', 'temple/asia', 'mosque', 'castle', 'palace'],
        'landscape': ['valley', 'canyon', 'cliff', 'desert/sand', 'desert/vegetation'],
        'sky': ['sky', 'sky/sunset', 'sky/sunrise', 'sky/night'],
    }

    def __init__(self, confidence_threshold: float = 0.1):
        """
        Initialize scene detector.
        
        Args:
            confidence_threshold: Minimum confidence for scene detection
        """
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.labels = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Standard Places365 preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def _load_model(self) -> None:
        """Lazy load Places365 model with offline fallback."""
        if self.model is not None:
            return
            
        try:
            # Try loading from torch hub with local cache
            import os
            torch_home = Path.home() / ".cache" / "torch"
            torch_home.mkdir(parents=True, exist_ok=True)
            os.environ['TORCH_HOME'] = str(torch_home)
            
            # Silence torch hub's noisy "Using cache found ..." output when cached.
            try:
                self.model = torch.hub.load(
                    'CSAILVision/places365',
                    'resnet50',
                    pretrained=True,
                    skip_validation=True,  # Skip validation to work offline if cached
                    verbose=False,
                )
            except TypeError:
                # Older torch versions may not support verbose=
                self.model = torch.hub.load(
                    'CSAILVision/places365',
                    'resnet50',
                    pretrained=True,
                    skip_validation=True
                )
            self.model.eval()
            self.model.to(self.device)
            
            # Load scene labels with offline fallback
            import urllib.request
            local_labels_path = Path(__file__).parent / "places365_labels.txt"
            
            # First try local file (faster and more reliable)
            if local_labels_path.exists():
                with open(local_labels_path, "r", encoding="utf-8") as f:
                    self.labels = []
                    for line in f.readlines():
                        # Format: "/a/airfield 0" -> "airfield"
                        parts = line.strip().split(' ')
                        if parts:
                            label = parts[0]
                            # Remove leading "/a/", "/b/", etc.
                            if label.startswith('/'):
                                label = label.split('/', 2)[-1]  # Get everything after "/x/"
                            self.labels.append(label)
                logging.info(f"Loaded {len(self.labels)} Places365 labels from local file")
            else:
                # Fallback to URL if local file doesn't exist
                label_url = 'https://raw.githubusercontent.com/csailvision/places365/master/categories_places365.txt'
                try:
                    with urllib.request.urlopen(label_url, timeout=10) as response:
                        self.labels = []
                        for line in response.readlines():
                            parts = line.decode('utf-8').strip().split(' ')
                            if parts:
                                label = parts[0]
                                if label.startswith('/'):
                                    label = label.split('/', 2)[-1]
                                self.labels.append(label)
                except Exception as e:
                    logging.warning(f"Could not load Places365 labels: {e}")
                    self.labels = [f"scene_{i}" for i in range(365)]
                else:
                    # Ultimate fallback: create minimal labels
                    self.labels = [f"scene_{i}" for i in range(365)]
                
            logging.info("Places365 scene detector loaded successfully")
            
        except Exception as e:
            logging.error(f"Failed to load Places365 model: {e}")
            # Set model to None so detection gracefully fails
            self.model = None
            self.labels = []

    def detect(
        self, 
        image_path: str, 
        top_k: int = 5,
        image_rgb: Optional[Image.Image] = None
    ) -> List[Tuple[str, float]]:
        """
        Detect scenes in an image.
        
        Args:
            image_path: Path to image file (for logging, if image_rgb provided)
            top_k: Number of top predictions to return
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
            
        Returns:
            List of (scene_label, confidence) tuples
        """
        self._load_model()
        
        # If model failed to load, return empty list gracefully
        if self.model is None or not self.labels:
            logging.warning(f"Scene detector not available, skipping detection for {image_path}")
            return []
        
        try:
            # Use pre-decoded image if provided, otherwise load from disk
            if image_rgb is not None:
                img = image_rgb
            else:
                img = Image.open(image_path).convert('RGB')
            
            img_tensor = self.transform(img).unsqueeze(0).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                logits = self.model(img_tensor)
                probs = torch.nn.functional.softmax(logits, dim=1)
                probs = probs.cpu().numpy()[0]
            
            # Get top predictions
            top_indices = np.argsort(probs)[::-1][:top_k]
            
            scenes = []
            for idx in top_indices:
                confidence = float(probs[idx])
                if confidence >= self.confidence_threshold:
                    scene_label = self.labels[idx]
                    scenes.append((scene_label, confidence))
            
            logging.info(f"Detected {len(scenes)} scenes in {image_path}")
            return scenes
            
        except Exception as e:
            logging.error(f"Scene detection failed for {image_path}: {e}")
            return []
    
    def get_primary_scene(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> Tuple[str, float]:
        """
        Get the primary scene category for an image.
        
        Args:
            image_path: Path to image file
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            (scene_category, confidence) - e.g., ('sunset', 0.85)
        """
        scenes = self.detect(image_path, top_k=10, image_rgb=image_rgb)
        
        if not scenes:
            return ('unknown', 0.0)
        
        # Check for relevant scene categories
        for category, keywords in self.RELEVANT_SCENES.items():
            for scene_label, confidence in scenes:
                for keyword in keywords:
                    if keyword in scene_label.lower():
                        return (category, confidence)
        
        # If no match, return the highest confidence scene
        return (scenes[0][0].split('/')[0], scenes[0][1])
    
    def get_all_scene_tags(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> List[str]:
        """
        Get all relevant scene tags for an image.
        
        Args:
            image_path: Path to image file
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            List of scene category tags (e.g., ['sunset', 'beach', 'outdoor'])
        """
        scenes = self.detect(image_path, top_k=10, image_rgb=image_rgb)
        
        if not scenes:
            return []
        
        tags = set()
        
        # Map detected scenes to our categories
        for scene_label, confidence in scenes:
            scene_lower = scene_label.lower()
            
            for category, keywords in self.RELEVANT_SCENES.items():
                for keyword in keywords:
                    if keyword in scene_lower:
                        tags.add(category)
                        break
        
        # Add generic indoor/outdoor tag
        outdoor_keywords = ['outdoor', 'outside', 'exterior']
        indoor_keywords = ['indoor', 'inside', 'interior', 'room']
        
        for scene_label, confidence in scenes[:3]:  # Check top 3
            scene_lower = scene_label.lower()
            if any(kw in scene_lower for kw in outdoor_keywords):
                tags.add('outdoor')
            elif any(kw in scene_lower for kw in indoor_keywords):
                tags.add('indoor')
        
        return sorted(list(tags))
