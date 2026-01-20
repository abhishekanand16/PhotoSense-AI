"""Object detection using YOLOv8."""

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


class ObjectDetector:
    """Object detection using YOLOv8."""

    # Animal classes for pet detection (maps YOLO class -> species name)
    ANIMAL_CLASSES = {
        "bird": "bird",
        "cat": "cat",
        "dog": "dog",
        "horse": "horse",
        "sheep": "sheep",
        "cow": "cow",
        "elephant": "elephant",
        "bear": "bear",
        "zebra": "zebra",
        "giraffe": "giraffe",
    }

    # Enhanced category mapping - keep original YOLO classes for better searchability
    # Map to both simplified category AND keep original class name
    # NOTE: "person" is excluded - we have dedicated face detection for people
    CATEGORY_MAP = {
        # "person": "person",  # EXCLUDED - use face detection instead
        "bicycle": "vehicle",
        "car": "vehicle",
        "motorcycle": "vehicle",
        "airplane": "vehicle",
        "bus": "vehicle",
        "train": "vehicle",
        "truck": "vehicle",
        "boat": "vehicle",
        "traffic light": "street",
        "fire hydrant": "street",
        "stop sign": "street",
        "parking meter": "street",
        "bench": "furniture",
        "bird": "animal",
        "cat": "animal",
        "dog": "animal",
        "horse": "animal",
        "sheep": "animal",
        "cow": "animal",
        "elephant": "animal",
        "bear": "animal",
        "zebra": "animal",
        "giraffe": "animal",
        "backpack": "accessory",
        "umbrella": "accessory",
        "handbag": "accessory",
        "tie": "accessory",
        "suitcase": "accessory",
        "frisbee": "sports",
        "skis": "sports",
        "snowboard": "sports",
        "sports ball": "sports",
        "kite": "sports",
        "baseball bat": "sports",
        "baseball glove": "sports",
        "skateboard": "sports",
        "surfboard": "sports",
        "tennis racket": "sports",
        "bottle": "food",
        "wine glass": "food",
        "cup": "food",
        "fork": "food",
        "knife": "food",
        "spoon": "food",
        "bowl": "food",
        "banana": "food",
        "apple": "food",
        "sandwich": "food",
        "orange": "food",
        "broccoli": "food",
        "carrot": "food",
        "hot dog": "food",
        "pizza": "food",
        "donut": "food",
        "cake": "food",
        "chair": "furniture",
        "couch": "furniture",
        "potted plant": "plant",  # KEY: Plants!
        "bed": "furniture",
        "dining table": "furniture",
        "toilet": "bathroom",
        "tv": "electronics",
        "laptop": "electronics",
        "mouse": "electronics",
        "remote": "electronics",
        "keyboard": "electronics",
        "cell phone": "electronics",
        "microwave": "appliance",
        "oven": "appliance",
        "toaster": "appliance",
        "sink": "appliance",
        "refrigerator": "appliance",
        "book": "item",
        "clock": "item",
        "vase": "decoration",
        "scissors": "tool",
        "teddy bear": "toy",
        "hair drier": "item",
        "toothbrush": "item",
    }

    def __init__(self, confidence_threshold: float = 0.55, model_size: str = "n"):
        """
        Initialize object detector.
        model_size: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
        confidence_threshold: Minimum confidence (0.55 balances precision vs recall)
        """
        self.confidence_threshold = confidence_threshold
        self.model_size = model_size
        self.model = None  # Lazy loading

    def _load_model(self) -> None:
        """Lazy load YOLOv8 model."""
        if self.model is None:
            model_name = f"yolov8{self.model_size}.pt"
            self.model = YOLO(model_name)

    def detect(self, image_path: str) -> List[Tuple[int, int, int, int, str, float]]:
        """
        Detect objects in an image.
        Returns list of (x, y, width, height, category, confidence) tuples.
        Category format: "simplified_category:original_class" (e.g., "plant:potted plant")
        """
        import logging
        
        self._load_model()
        
        try:
            results = self.model(image_path, conf=self.confidence_threshold, verbose=False)
        except Exception as e:
            logging.error(f"Object detection failed for {image_path}: {e}")
            return []

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]

                # Map to simplified category - skip if not in our category map
                simplified_category = self.CATEGORY_MAP.get(class_name)
                if simplified_category is None:
                    continue  # Skip objects that don't match known categories

                # Store both simplified category and original class name
                # Format: "simplified:original" (e.g., "plant:potted plant")
                category = f"{simplified_category}:{class_name}"

                width = int(x2 - x1)
                height = int(y2 - y1)
                detections.append((int(x1), int(y1), width, height, category, confidence))
        
        logging.info(f"Detected {len(detections)} objects in {image_path}")
        return detections

    def detect_animals(self, image_path: str, min_confidence: float = 0.4) -> List[Tuple[int, int, int, int, str, float]]:
        """
        Detect animals/pets in an image for identity grouping.
        Returns list of (x, y, width, height, species, confidence) tuples.
        
        Uses a lower confidence threshold than general objects since we want
        to capture pets even when partially visible.
        """
        import logging
        
        self._load_model()
        
        try:
            results = self.model(image_path, conf=min_confidence, verbose=False)
        except Exception as e:
            logging.error(f"Animal detection failed for {image_path}: {e}")
            return []

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names[class_id]
                
                # Only keep animal classes
                if class_name not in self.ANIMAL_CLASSES:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                confidence = float(box.conf[0].cpu().numpy())
                species = self.ANIMAL_CLASSES[class_name]
                
                width = int(x2 - x1)
                height = int(y2 - y1)
                detections.append((int(x1), int(y1), width, height, species, confidence))
        
        logging.info(f"Detected {len(detections)} animals in {image_path}")
        return detections
