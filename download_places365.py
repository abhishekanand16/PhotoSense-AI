#!/usr/bin/env python3
"""Direct download of Places365 model."""

import torch
import os

# Set cache directory
os.environ['TORCH_HOME'] = os.path.expanduser('~/.cache/torch')

print("Downloading Places365 ResNet50...")
print("This may take a few minutes (model is ~100MB)...")

try:
    # Force download with verbose output
    model = torch.hub.load(
        'CSAILVision/places365',
        'resnet50',
        pretrained=True,
        force_reload=True,  # Force fresh download
        verbose=True
    )
    print("\n✓ Success! Places365 model downloaded to ~/.cache/torch/hub/")
    
except Exception as e:
    print(f"\n✗ Failed: {e}")
    print("\nTrying alternative method...")
    
    # Alternative: Download directly from GitHub
    import urllib.request
    import zipfile
    
    cache_dir = os.path.expanduser('~/.cache/torch/hub')
    os.makedirs(cache_dir, exist_ok=True)
    
    # Download the repository
    repo_url = "https://github.com/CSAILVision/places365/archive/refs/heads/master.zip"
    zip_path = os.path.join(cache_dir, "places365.zip")
    
    print(f"Downloading from {repo_url}...")
    urllib.request.urlretrieve(repo_url, zip_path)
    
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(cache_dir)
    
    os.remove(zip_path)
    print("✓ Downloaded via alternative method")
