"""
Single-decode image cache for PhotoSense-AI performance optimization.

Provides:
- Single image decode per photo (shared across all ML models)
- Pre-resized versions for different ML tasks
- Memory-efficient temporary storage during processing
"""

import cv2
import numpy as np
from PIL import Image
from typing import Dict, Optional, Tuple
import logging


class ImageCache:
    """
    Thread-local cache for decoded images during ML processing.
    Ensures each image is decoded exactly once per photo.
    """
    
    # Maximum sizes for different ML tasks (preserves aspect ratio)
    SIZE_FACE = 1024  # Face detection max side
    SIZE_ML = 768     # Object/scene/embedding max side
    SIZE_FLORENCE = 1024  # Florence captioning max side
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    def decode_image(self, image_path: str) -> Optional[Dict]:
        """
        Decode an image once and cache it with pre-resized versions.
        
        Returns dict with:
        - 'original_bgr': Original resolution as numpy BGR (for cropping)
        - 'original_rgb': Original resolution as PIL RGB
        - 'face_bgr': Resized for face detection (max 1024px side)
        - 'ml_bgr': Resized for object/scene detection (max 768px side)
        - 'ml_rgb': Resized for CLIP/Florence (max 768px side) as PIL Image
        - 'florence_rgb': Resized for Florence (max 1024px side) as PIL Image
        - 'original_size': (width, height) of original
        - 'scale_factors': dict of scale factors for bbox mapping
        """
        if image_path in self._cache:
            return self._cache[image_path]
        
        try:
            # Single decode using cv2 (fastest for numpy)
            original_bgr = cv2.imread(image_path)
            if original_bgr is None:
                logging.warning(f"Could not read image: {image_path}")
                return None
            
            orig_h, orig_w = original_bgr.shape[:2]
            original_size = (orig_w, orig_h)
            
            # Create PIL version for models that need it
            original_rgb_array = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
            original_rgb = Image.fromarray(original_rgb_array)
            
            # Compute scale factors and resized versions
            scale_factors = {}
            
            # Face detection size (1024px max side)
            face_bgr, face_scale = self._resize_for_size(original_bgr, self.SIZE_FACE)
            scale_factors['face'] = face_scale
            
            # ML size (768px max side) - for object detection, scene detection, CLIP
            ml_bgr, ml_scale = self._resize_for_size(original_bgr, self.SIZE_ML)
            scale_factors['ml'] = ml_scale
            ml_rgb_array = cv2.cvtColor(ml_bgr, cv2.COLOR_BGR2RGB)
            ml_rgb = Image.fromarray(ml_rgb_array)
            
            # Florence size (1024px max side)
            florence_bgr, florence_scale = self._resize_for_size(original_bgr, self.SIZE_FLORENCE)
            scale_factors['florence'] = florence_scale
            florence_rgb_array = cv2.cvtColor(florence_bgr, cv2.COLOR_BGR2RGB)
            florence_rgb = Image.fromarray(florence_rgb_array)
            
            cached = {
                'original_bgr': original_bgr,
                'original_rgb': original_rgb,
                'face_bgr': face_bgr,
                'ml_bgr': ml_bgr,
                'ml_rgb': ml_rgb,
                'florence_rgb': florence_rgb,
                'original_size': original_size,
                'scale_factors': scale_factors,
            }
            
            self._cache[image_path] = cached
            return cached
            
        except Exception as e:
            logging.error(f"Failed to decode image {image_path}: {e}")
            return None
    
    def _resize_for_size(self, img: np.ndarray, max_size: int) -> Tuple[np.ndarray, float]:
        """
        Resize image to max_size on longest side, preserving aspect ratio.
        Returns (resized_img, scale_factor).
        scale_factor is used to map bboxes back to original coordinates.
        """
        h, w = img.shape[:2]
        max_dim = max(h, w)
        
        if max_dim <= max_size:
            # No resize needed
            return img, 1.0
        
        scale = max_size / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale
    
    def scale_bbox(self, bbox: Tuple[int, int, int, int], scale_factor: float) -> Tuple[int, int, int, int]:
        """
        Scale bounding box from resized coordinates back to original coordinates.
        bbox is (x, y, w, h).
        """
        if scale_factor == 1.0:
            return bbox
        
        x, y, w, h = bbox
        inv_scale = 1.0 / scale_factor
        return (
            int(x * inv_scale),
            int(y * inv_scale),
            int(w * inv_scale),
            int(h * inv_scale)
        )
    
    def clear(self, image_path: Optional[str] = None):
        """
        Clear cache for a specific image or all images.
        Call after processing each photo to free memory.
        """
        if image_path:
            self._cache.pop(image_path, None)
        else:
            self._cache.clear()
    
    def get_original_bgr(self, image_path: str) -> Optional[np.ndarray]:
        """Get original BGR image for direct cropping operations."""
        cached = self.decode_image(image_path)
        return cached['original_bgr'] if cached else None
    
    def get_face_image(self, image_path: str) -> Optional[np.ndarray]:
        """Get resized image optimized for face detection."""
        cached = self.decode_image(image_path)
        return cached['face_bgr'] if cached else None
    
    def get_ml_image_bgr(self, image_path: str) -> Optional[np.ndarray]:
        """Get resized BGR image for object detection."""
        cached = self.decode_image(image_path)
        return cached['ml_bgr'] if cached else None
    
    def get_ml_image_rgb(self, image_path: str) -> Optional[Image.Image]:
        """Get resized PIL RGB image for CLIP/scene detection."""
        cached = self.decode_image(image_path)
        return cached['ml_rgb'] if cached else None
    
    def get_florence_image(self, image_path: str) -> Optional[Image.Image]:
        """Get resized PIL RGB image for Florence captioning."""
        cached = self.decode_image(image_path)
        return cached['florence_rgb'] if cached else None
    
    def get_scale_factor(self, image_path: str, task: str) -> float:
        """Get scale factor for a specific task ('face', 'ml', 'florence')."""
        cached = self.decode_image(image_path)
        if cached:
            return cached['scale_factors'].get(task, 1.0)
        return 1.0


# Global singleton for the current processing batch
_image_cache = None


def get_image_cache() -> ImageCache:
    """Get the global image cache singleton."""
    global _image_cache
    if _image_cache is None:
        _image_cache = ImageCache()
    return _image_cache


def clear_image_cache():
    """Clear the global image cache."""
    global _image_cache
    if _image_cache is not None:
        _image_cache.clear()
