# PhotoSense-AI

Offline photo organization system with facial recognition and automatic person grouping.

## Overview

PhotoSense-AI is a privacy-first, offline photo management system that scans local image folders, extracts metadata, performs facial recognition, and automatically groups photos by individuals using unsupervised learning. The system runs entirely on your local machine—no cloud services, no external APIs, no data leaving your device.

## Features

- **Recursive Image Scanning**: Automatically finds all images in specified directories
- **Metadata Extraction**: Extracts EXIF data including date taken, camera model, and image dimensions
- **Face Detection**: Detects human faces in images using MTCNN
- **Face Recognition**: Generates facial embeddings using FaceNet
- **Automatic Clustering**: Groups faces by person using DBSCAN unsupervised learning
- **Person Labeling**: Map clusters to human-readable names
- **Local Search**: Search images by person, date, or camera model
- **Fully Offline**: All processing happens locally—no internet required after installation

## Tech Stack

- **Language**: Python 3.10+
- **Face Detection**: MTCNN
- **Face Embeddings**: FaceNet (keras-facenet)
- **Clustering**: DBSCAN (scikit-learn)
- **Metadata Extraction**: Pillow (PIL)
- **Database**: SQLite
- **CLI**: Click
- **Optional UI**: Streamlit

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip3
- macOS (tested), Linux, or Windows

### Installation

1. Clone or navigate to the project directory:
```bash
cd PhotoSense-AI
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Complete Workflow

1. **Scan a directory for images**:
```bash
python src/main.py scan --input /path/to/your/photos
```

2. **Detect faces in scanned images**:
```bash
python src/main.py detect
```

3. **Generate face embeddings**:
```bash
python src/main.py encode
```

4. **Cluster faces into people**:
```bash
python src/main.py cluster
```

5. **Label people with names**:
```bash
# First, list all people
python src/main.py list-people

# Then label a person
python src/main.py label --person-id 1 --name "Alice"
```

6. **Search for images**:
```bash
# Search by person
python src/main.py search --person "Alice"

# Search by date
python src/main.py search --date "2023-12-25"

# Search by date range
python src/main.py search --start-date "2023-01-01" --end-date "2023-12-31"

# Search by camera
python src/main.py search --camera "iPhone"
```

7. **Check database statistics**:
```bash
python src/main.py stats
```

#### Optional: Web UI

Launch the Streamlit web interface:
```bash
streamlit run app.py
```

Then open your browser to the URL shown (typically http://localhost:8501).

#### View all available commands:
```bash
python src/main.py --help
```

## How It Works

The system follows a pipeline approach:

1. **Scanning**: Recursively finds all image files (JPG, JPEG, PNG) in the specified directory
2. **Metadata Extraction**: Extracts EXIF data and basic image information
3. **Face Detection**: Detects all faces in each image using MTCNN
4. **Face Cropping**: Crops and normalizes detected face regions
5. **Embedding Generation**: Generates facial embeddings using FaceNet
6. **Clustering**: Groups similar faces using DBSCAN unsupervised learning
7. **Person Mapping**: Allows assigning human-readable names to clusters
8. **Search**: Query images by person, date, or camera model

All data is stored locally in a SQLite database and file system.

## Project Status

**Status**: All Core Features Implemented ✅

- ✅ Image scanning and metadata extraction
- ✅ SQLite database schema
- ✅ Face detection using MTCNN
- ✅ Face embeddings using FaceNet
- ✅ Clustering using DBSCAN
- ✅ Search and labeling functionality
- ✅ CLI interface with all commands
- ✅ Optional Streamlit web UI

## Extension Points

The following features are designed as extension points but not yet implemented. The codebase is structured to support these additions:

### Video Processing
- **Location**: `src/scanner/scan_images.py` - Add video file extensions
- **Implementation**: Extract frames from video files, then process through existing face detection pipeline
- **Storage**: Extend `images` table to include video metadata

### Face Similarity Search
- **Location**: `src/search/search.py` - Add similarity search method
- **Implementation**: Use FAISS for efficient vector similarity search on embeddings
- **Usage**: Find faces similar to a query face image

### Emotion Detection
- **Location**: `src/face/` - New module `emotion.py`
- **Implementation**: Add emotion classification model (e.g., FER2013) after face detection
- **Storage**: Add `emotion` column to `faces` table

### Enhanced UI
- **Location**: `app.py` - Streamlit interface
- **Improvements**: 
  - Interactive graph visualization of person relationships
  - Timeline view for chronological browsing
  - Advanced filtering and sorting options
  - Face comparison tool

### Performance Optimizations
- **Batch Processing**: Process multiple images in parallel
- **Caching**: Cache embeddings and detection results
- **Indexing**: Add database indexes for faster queries
- **Duplicate Detection**: Use perceptual hashing to identify duplicate images

## License

This project is designed as a portfolio/resume project. Use as you see fit.
