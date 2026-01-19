#!/bin/bash
# Manual Places365 installation script

set -e

echo "Installing Places365 ResNet50..."

# Activate virtual environment
source venv/bin/activate

# Create cache directories
mkdir -p ~/.cache/torch/hub/checkpoints
mkdir -p ~/.cache/torch/hub/CSAILVision_places365_master

echo "Step 1: Downloading model weights from MIT..."
# Download the pretrained weights directly from MIT
cd ~/.cache/torch/hub/checkpoints
if [ ! -f "resnet50_places365.pth.tar" ]; then
    curl -L "http://places2.csail.mit.edu/models_places365/resnet50_places365.pth.tar" -o resnet50_places365.pth.tar
    echo "✓ Model weights downloaded"
else
    echo "✓ Model weights already exist"
fi

echo "Step 2: Cloning Places365 repository..."
cd ~/.cache/torch/hub
if [ ! -d "CSAILVision_places365_master" ]; then
    git clone https://github.com/CSAILVision/places365.git CSAILVision_places365_master
    echo "✓ Repository cloned"
else
    echo "✓ Repository already exists"
fi

echo "Step 3: Downloading category labels..."
cd /Users/abhishek/Documents/GitHub/PhotoSense-AI/services/ml/detectors
if [ ! -f "places365_labels.txt" ]; then
    curl -L "https://raw.githubusercontent.com/csailvision/places365/master/categories_places365.txt" -o places365_labels.txt
    echo "✓ Labels downloaded"
else
    echo "✓ Labels already exist"
fi

echo ""
echo "✓ Places365 installation complete!"
echo "Model location: ~/.cache/torch/hub/checkpoints/resnet50_places365.pth.tar"
echo "Repository: ~/.cache/torch/hub/CSAILVision_places365_master"
echo "Labels: services/ml/detectors/places365_labels.txt"
