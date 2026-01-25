# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
"""Florence-2 vision-language model for rich image captioning and tagging."""

from typing import List, Tuple, Optional
import logging
import re
import traceback

import torch
from PIL import Image


class FlorenceDetector:
    """
    Florence-2-base detector for rich image understanding.
    
    Generates:
    - Short captions
    - Detailed scene descriptions
    - Extracted tags (nouns, scene descriptors)
    
    Complements YOLO/CLIP/Places365 with natural language understanding.
    """
    
    # Stopwords to filter from tags
    STOPWORDS = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'of', 'in', 'on', 'at', 'to', 'for',
        'with', 'by', 'from', 'up', 'down', 'out', 'off', 'over', 'under',
        'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
        'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'this', 'that', 'these', 'those'
    }
    
    # Generic/overly broad tags to filter
    GENERIC_TAGS = {
        'photo', 'image', 'picture', 'scene', 'view', 'background',
        'foreground', 'object', 'item', 'thing', 'stuff', 'area',
        'place', 'location', 'shot', 'photograph', 'pic'
    }
    
    # Maximum tags to extract
    MAX_TAGS = 10
    
    # Minimum confidence for tags
    MIN_TAG_CONFIDENCE = 0.6
    
    def __init__(self):
        """Initialize Florence-2 detector with lazy loading."""
        self.model = None
        self.processor = None
        self.device = None
        self.dtype = None
        self._load_attempted = False
        self._load_error: Optional[str] = None
    
    def _detect_device(self) -> Tuple[str, torch.dtype]:
        """Detect best available device and dtype."""
        if torch.cuda.is_available():
            # NVIDIA GPU - float16 works well and saves memory
            return "cuda", torch.float16
        elif torch.backends.mps.is_available():
            # Apple Silicon (M1/M2) - must use float32 for Florence-2 compatibility
            # Florence-2 has layers that don't support float16 on MPS
            return "mps", torch.float32
        else:
            # CPU fallback (requires float32)
            return "cpu", torch.float32
    
    def _load_model(self) -> bool:
        """
        Lazy load Florence-2-base model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        # Already loaded
        if self.model is not None:
            return True
        
        # Already tried and failed - don't retry
        if self._load_attempted:
            return False
        
        self._load_attempted = True
        
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM, AutoConfig
            import warnings
            
            # Suppress HuggingFace warnings during loading
            warnings.filterwarnings("ignore", category=UserWarning)
            
            # Detect device
            self.device, self.dtype = self._detect_device()
            
            logging.info(f"Loading Florence-2-base on {self.device} with {self.dtype}")
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(
                "microsoft/Florence-2-base",
                trust_remote_code=True
            )
            
            # Load config first and patch to avoid SDPA compatibility issues
            config = AutoConfig.from_pretrained(
                "microsoft/Florence-2-base",
                trust_remote_code=True
            )
            config._attn_implementation = "eager"
            
            # Load model - always load in float32 first, then convert if needed
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Florence-2-base",
                trust_remote_code=True,
                config=config,
                torch_dtype=torch.float32,  # Load in float32 first
            )
            
            # Move to device first
            self.model = self.model.to(self.device)
            
            # Then convert dtype if not float32 (CUDA can use float16)
            if self.dtype != torch.float32:
                try:
                    self.model = self.model.to(dtype=self.dtype)
                except Exception as dtype_err:
                    logging.warning(f"Could not convert to {self.dtype}, keeping float32: {dtype_err}")
                    self.dtype = torch.float32
            
            self.model.eval()
            
            logging.info(f"Florence-2-base loaded successfully on {self.device} with {self.dtype}")
            return True
            
        except Exception as e:
            self._load_error = str(e)
            logging.error(f"Failed to load Florence-2-base: {e}")
            logging.error(traceback.format_exc())
            self.model = None
            self.processor = None
            return False
    
    def _run_task(
        self, 
        image_path: str, 
        task_prompt: str,
        image_rgb: Optional[Image.Image] = None
    ) -> str:
        """
        Run a Florence-2 task on an image.
        
        Args:
            image_path: Path to image (for logging if image_rgb provided)
            task_prompt: Task prompt (e.g., "<CAPTION>", "<DETAILED_CAPTION>")
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            Generated text output
        """
        # Try to load model if not already loaded
        if not self._load_model():
            # Model failed to load, return empty gracefully
            return ""
        
        if self.model is None or self.processor is None:
            return ""
        
        try:
            # Use pre-decoded image if provided, otherwise load from disk
            if image_rgb is not None:
                image = image_rgb
            else:
                image = Image.open(image_path).convert('RGB')
                
                # Resize large images to prevent memory issues
                max_size = 1024
                if max(image.size) > max_size:
                    ratio = max_size / max(image.size)
                    new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Prepare inputs
            inputs = self.processor(
                text=task_prompt,
                images=image,
                return_tensors="pt"
            )
            
            # Move inputs to device and cast floating point tensors to model dtype
            processed_inputs = {}
            for k, v in inputs.items():
                if isinstance(v, torch.Tensor):
                    if v.is_floating_point():
                        # Pixel values need to match model dtype
                        processed_inputs[k] = v.to(device=self.device, dtype=self.dtype)
                    else:
                        # Integer tensors (input_ids, attention_mask) - device only
                        processed_inputs[k] = v.to(device=self.device)
                else:
                    processed_inputs[k] = v
            inputs = processed_inputs
            
            # Generate using greedy decoding with cache disabled
            # use_cache=False is required to avoid 'NoneType' error in prepare_inputs_for_generation
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    num_beams=1,
                    do_sample=False,
                    use_cache=False,  # Required to avoid KV cache bug in Florence-2
                )
            
            # Decode
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            # Clean output (remove task prompt if echoed)
            generated_text = generated_text.replace(task_prompt, "").strip()
            
            return generated_text
            
        except Exception as e:
            logging.error(f"Florence-2 task '{task_prompt}' failed for {image_path}: {e}")
            return ""
    
    def get_caption(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> str:
        """
        Get short caption for an image.
        
        Args:
            image_path: Path to image (for logging if image_rgb provided)
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            Short caption (1 sentence)
        """
        caption = self._run_task(image_path, "<CAPTION>", image_rgb=image_rgb)
        
        # Trim to reasonable length
        if len(caption) > 200:
            caption = caption[:197] + "..."
        
        return caption
    
    def get_detailed_caption(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> str:
        """
        Get detailed caption for an image.
        
        Args:
            image_path: Path to image (for logging if image_rgb provided)
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            Detailed caption (2-3 sentences)
        """
        caption = self._run_task(image_path, "<DETAILED_CAPTION>", image_rgb=image_rgb)
        
        # Trim to reasonable length
        if len(caption) > 500:
            caption = caption[:497] + "..."
        
        return caption
    
    def extract_tags(self, caption: str) -> List[str]:
        """
        Extract normalized tags from a caption.
        
        Args:
            caption: Caption text
        
        Returns:
            List of normalized tags (lowercase, deduplicated, filtered)
        """
        if not caption:
            return []
        
        # Convert to lowercase
        caption = caption.lower()
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-z]+\b', caption)
        
        # Filter stopwords, generic tags, and short words
        meaningful_words = [
            w for w in words 
            if w not in self.STOPWORDS 
            and w not in self.GENERIC_TAGS
            and len(w) > 2
        ]
        
        # Deduplicate while preserving order
        seen = set()
        tags = []
        for word in meaningful_words:
            if word not in seen:
                seen.add(word)
                tags.append(word)
        
        # Limit to MAX_TAGS
        return tags[:self.MAX_TAGS]
    
    def detect(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> Tuple[str, List[str]]:
        """
        Full detection: caption + tags.
        
        Args:
            image_path: Path to image (for logging if image_rgb provided)
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            Tuple of (caption, tags)
            - caption: Short caption string
            - tags: List of extracted tags
        """
        try:
            # Get detailed caption for better tag extraction
            detailed_caption = self.get_detailed_caption(image_path, image_rgb=image_rgb)
            
            # Get short caption for storage
            short_caption = self.get_caption(image_path, image_rgb=image_rgb)
            
            # Extract tags from detailed caption
            tags = self.extract_tags(detailed_caption)
            
            logging.info(f"Florence-2 detected {len(tags)} tags for {image_path}")
            
            return short_caption, tags
            
        except Exception as e:
            logging.error(f"Florence-2 detection failed for {image_path}: {e}")
            return "", []
    
    def get_scene_tags(
        self, 
        image_path: str,
        image_rgb: Optional[Image.Image] = None
    ) -> List[Tuple[str, float]]:
        """
        Get scene tags with confidence scores (for pipeline integration).
        
        Args:
            image_path: Path to image (for logging if image_rgb provided)
            image_rgb: Optional pre-decoded PIL RGB image (from ImageCache)
        
        Returns:
            List of (tag, confidence) tuples
        """
        # Try to load model if not loaded
        if not self._load_model():
            return []
        
        _, tags = self.detect(image_path, image_rgb=image_rgb)
        
        # Assign confidence based on position (earlier = more relevant)
        # Use higher confidence range since Florence-2 is high quality
        results = []
        for i, tag in enumerate(tags):
            # Confidence decreases from 0.95 to 0.70 based on position
            if len(tags) > 0:
                confidence = 0.95 - (i * 0.25 / len(tags))
                confidence = max(0.70, confidence)  # Floor at 0.70
            else:
                confidence = 0.70
            results.append((tag, confidence))
        
        return results
