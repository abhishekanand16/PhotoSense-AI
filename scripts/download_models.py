#!/usr/bin/env python3
"""Download required ML models for offline use."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def download_places365():
    """Download Places365 model to cache."""
    try:
        import torch
        
        logging.info("Downloading Places365 ResNet50 model...")
        os.environ['TORCH_HOME'] = os.path.expanduser('~/.cache/torch')
        
        # This will download and cache the model
        model = torch.hub.load(
            'CSAILVision/places365',
            'resnet50',
            pretrained=True,
            verbose=True
        )
        
        logging.info("✓ Places365 model downloaded successfully")
        
        # Download labels
        import urllib.request
        labels_dir = os.path.join(os.path.dirname(__file__), '..', 'services', 'ml', 'detectors')
        labels_path = os.path.join(labels_dir, 'places365_labels.txt')
        
        logging.info("Downloading Places365 labels...")
        label_url = 'https://raw.githubusercontent.com/csailvision/places365/master/categories_places365.txt'
        
        try:
            with urllib.request.urlopen(label_url, timeout=30) as response:
                content = response.read().decode('utf-8')
                
            with open(labels_path, 'w') as f:
                f.write(content)
            
            logging.info(f"✓ Labels saved to {labels_path}")
        except Exception as e:
            logging.warning(f"Could not download labels: {e}")
            logging.info("Labels will be generated automatically")
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to download Places365: {e}")
        return False

def download_clip():
    """Download CLIP model to cache."""
    try:
        from transformers import CLIPModel, CLIPProcessor
        
        logging.info("Downloading CLIP-ViT-Large model...")
        
        model_name = "openai/clip-vit-large-patch14"
        model = CLIPModel.from_pretrained(model_name)
        processor = CLIPProcessor.from_pretrained(model_name)
        
        logging.info("✓ CLIP model downloaded successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to download CLIP: {e}")
        return False

def download_yolo():
    """Download YOLO model to cache."""
    try:
        from ultralytics import YOLO
        
        logging.info("Downloading YOLOv8n model...")
        
        model = YOLO("yolov8n.pt")
        
        logging.info("✓ YOLO model downloaded successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to download YOLO: {e}")
        return False

def main():
    """Download all models."""
    logging.info("=" * 60)
    logging.info("PhotoSense-AI Model Download")
    logging.info("=" * 60)
    
    results = {
        'Places365': download_places365(),
        'CLIP': download_clip(),
        'YOLO': download_yolo(),
    }
    
    logging.info("\n" + "=" * 60)
    logging.info("Download Summary:")
    logging.info("=" * 60)
    
    for model, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        logging.info(f"{model:20} {status}")
    
    all_success = all(results.values())
    
    if all_success:
        logging.info("\n✓ All models downloaded successfully!")
        logging.info("You can now use PhotoSense-AI offline.")
        return 0
    else:
        logging.warning("\n⚠ Some models failed to download.")
        logging.warning("The application will still work but may have limited functionality.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
