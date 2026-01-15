"""
Face detection module for PhotoSense-AI.

Uses MTCNN for face detection and cropping.
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
from PIL import Image

try:
    from mtcnn import MTCNN
except ImportError:
    raise ImportError(
        "MTCNN not installed. Install with: pip install mtcnn"
    )

logger = logging.getLogger(__name__)


class FaceDetector:
    """Face detector using MTCNN."""

    def __init__(self, min_face_size: int = 20, scale_factor: float = 0.709):
        """
        Initialize MTCNN face detector.

        Args:
            min_face_size: Minimum face size to detect
            scale_factor: Scale factor for image pyramid
        """
        self.detector = MTCNN(
            min_face_size=min_face_size,
            scale_factor=scale_factor
        )
        logger.info("MTCNN face detector initialized")

    def detect_faces(self, image_path: str) -> List[dict]:
        """
        Detect faces in an image.

        Args:
            image_path: Path to image file

        Returns:
            List of face detection dictionaries, each containing:
                - 'box': [x, y, width, height]
                - 'confidence': Detection confidence score
                - 'keypoints': Facial keypoints (optional)
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            pixels = np.asarray(image)
            
            # Detect faces
            detections = self.detector.detect_faces(pixels)
            
            logger.debug(f"Detected {len(detections)} faces in {image_path}")
            
            return detections

        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {e}")
            return []

    def crop_face(
        self,
        image_path: str,
        bbox: List[int],
        output_path: str,
        margin: float = 0.2,
        target_size: Tuple[int, int] = (160, 160)
    ) -> bool:
        """
        Crop and save a face region from an image.

        Args:
            image_path: Path to source image
            bbox: Bounding box [x, y, width, height]
            output_path: Path to save cropped face
            margin: Margin to add around face (as fraction of bbox size)
            target_size: Target size for cropped face (width, height)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_width, img_height = image.size
            x, y, width, height = bbox
            
            # Add margin
            margin_x = int(width * margin)
            margin_y = int(height * margin)
            
            # Calculate crop coordinates with bounds checking
            left = max(0, x - margin_x)
            top = max(0, y - margin_y)
            right = min(img_width, x + width + margin_x)
            bottom = min(img_height, y + height + margin_y)
            
            # Crop face
            face_crop = image.crop((left, top, right, bottom))
            
            # Resize to target size
            face_crop = face_crop.resize(target_size, Image.Resampling.LANCZOS)
            
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save cropped face
            face_crop.save(output_path, 'JPEG', quality=95)
            
            return True

        except Exception as e:
            logger.error(f"Error cropping face from {image_path}: {e}")
            return False

    def process_image(
        self,
        image_path: str,
        output_dir: str,
        min_confidence: float = 0.9
    ) -> List[dict]:
        """
        Detect faces in an image and crop them.

        Args:
            image_path: Path to source image
            output_dir: Directory to save cropped faces
            min_confidence: Minimum confidence threshold for detections

        Returns:
            List of detection results, each containing:
                - 'bbox': [x, y, width, height]
                - 'confidence': Detection confidence
                - 'face_path': Path to cropped face image
        """
        # Detect faces
        detections = self.detect_faces(image_path)
        
        if not detections:
            return []
        
        results = []
        image_stem = Path(image_path).stem
        
        # Process each detection
        for idx, detection in enumerate(detections):
            confidence = detection.get('confidence', 0.0)
            
            # Filter by confidence
            if confidence < min_confidence:
                logger.debug(f"Skipping low-confidence detection: {confidence}")
                continue
            
            bbox = detection['box']  # [x, y, width, height]
            
            # Generate output filename
            face_filename = f"{image_stem}_face_{idx:03d}.jpg"
            face_path = os.path.join(output_dir, face_filename)
            
            # Crop and save face
            success = self.crop_face(image_path, bbox, face_path)
            
            if success:
                results.append({
                    'bbox': bbox,
                    'confidence': confidence,
                    'face_path': face_path,
                })
            else:
                logger.warning(f"Failed to crop face {idx} from {image_path}")
        
        return results
