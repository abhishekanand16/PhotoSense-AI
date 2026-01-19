"""Object detection using YOLOv8."""

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


class ObjectDetector:
    """Object detection using YOLOv8."""

    # Simplified category mapping
    CATEGORY_MAP = {
        "person": "person",
        "bicycle": "vehicle",
        "car": "vehicle",
        "motorcycle": "vehicle",
        "airplane": "vehicle",
        "bus": "vehicle",
        "train": "vehicle",
        "truck": "vehicle",
        "boat": "vehicle",
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
        "sports ball": "sports",
        "kite": "sports",
        "baseball bat": "sports",
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
        "pizza": "food",
        "donut": "food",
        "cake": "food",
    }

    def __init__(self, confidence_threshold: float = 0.5, model_size: str = "n"):
        """
        Initialize object detector.
        model_size: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
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

                # Map to simplified category
                category = self.CATEGORY_MAP.get(class_name, "other")

                width = int(x2 - x1)
                height = int(y2 - y1)
                detections.append((int(x1), int(y1), width, height, category, confidence))
        
        logging.info(f"Detected {len(detections)} objects in {image_path}")
        return detections
