# PhotoSense-AI

Offline visual intelligence application for organizing and searching photos using computer vision and machine learning.

## Overview

PhotoSense-AI is a desktop application that automatically understands your photos using computer vision. It detects faces, identifies objects, and enables semantic search—all running locally on your machine with no cloud services.

## Features

- **Automatic Photo Analysis**: Scans folders and extracts metadata
- **Face Detection & Clustering**: Identifies and groups people automatically
- **Object Detection**: Recognizes objects and categorizes photos
- **Semantic Search**: Find photos by natural language descriptions
- **People Management**: Rename and merge person clusters
- **Fully Offline**: All processing happens locally
- **Fast Vector Search**: FAISS-powered similarity search
- **Metadata Extraction**: EXIF data parsing and organization

## Tech Stack

- **Desktop App**: Tauri + React + TypeScript + Tailwind CSS
- **Backend API**: FastAPI (Python)
- **ML/CV**: RetinaFace, YOLOv8, CLIP, ArcFace
- **Storage**: SQLite (metadata) + FAISS (vector search)
- **Build Tools**: Vite, Rust/Cargo

## Prerequisites

- Python 3.10+
- Node.js 18+
- Rust (for Tauri desktop app)
  - Install from [rustup.rs](https://rustup.rs/)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/abhishekanand16/PhotoSense-AI.git
cd PhotoSense-AI
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Desktop App Setup

```bash
cd apps/desktop

# Install dependencies
npm install

# Install Tauri CLI (if not already installed)
npm install -g @tauri-apps/cli
```

## Running

### Development Mode

#### Start Backend API

```bash
# From project root
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the API server
uvicorn services.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

#### Start Desktop App

```bash
# From apps/desktop directory
npm run tauri dev
```

This will start the Tauri development server and open the desktop application.

### Production Build

Install PyInstaller for backend bundling:

```bash
pip install pyinstaller
```

```bash
# Build desktop installers (bundled backend)
cd packaging/desktop-wrapper
./build_desktop.sh   # macOS/Linux
# or: .\build_desktop.ps1 (Windows)

# The built application will be in packaging/desktop-wrapper/src-tauri/target/release/bundle/
```

## Usage

### Initial Setup

1. **Add Photos**: 
   - Open the Settings view
   - Click "Add Photos" or "Scan Folder"
   - Select a folder containing your photos
   - The app will automatically process all images

2. **Wait for Processing**:
   - First-time processing downloads ML models automatically
   - Large photo collections may take time to process
   - Progress is shown in the UI

### Using the Application

1. **Browse Photos**: 
   - View photos organized by date in the Photos view
   - Navigate through your collection

2. **People View**:
   - See automatically detected people clusters
   - Click on a person to see all their photos
   - Rename people by clicking the edit icon
   - Merge duplicate clusters if needed

3. **Objects View**:
   - Browse photos by detected objects
   - Filter by object categories

4. **Search**:
   - Use natural language queries (e.g., "beach sunset", "dog playing")
   - Filter by person, date range, or object category
   - Results are ranked by relevance

5. **Settings**:
   - Manage photo folders
   - View statistics
   - Configure application preferences

## API Documentation

The backend API provides REST endpoints for all functionality:

### Endpoints

- `GET /` - API status
- `GET /health` - Health check
- `GET /photos` - List all photos
- `GET /photos/{id}` - Get photo details
- `POST /scan` - Scan a folder for photos
- `GET /people` - List all detected people
- `GET /people/{id}` - Get person details
- `PUT /people/{id}` - Update person name
- `POST /people/merge` - Merge two people
- `GET /objects` - List detected objects
- `POST /search` - Semantic search
- `GET /stats` - Database statistics

See `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

```
PhotoSense-AI/
├── apps/
│   └── desktop/              # Tauri + React desktop app
│       ├── src/
│       │   ├── components/   # React components
│       │   ├── views/        # Main views (Photos, People, Search, etc.)
│       │   ├── services/     # API client and utilities
│       │   └── styles/       # CSS/Tailwind styles
│       └── src-tauri/        # Rust backend for Tauri
├── packaging/
│   └── desktop-wrapper/      # PyInstaller + Tauri packaging wrapper
├── services/
│   ├── api/                  # FastAPI service
│   │   ├── routes/           # API route handlers
│   │   ├── models.py         # Pydantic models
│   │   └── main.py           # FastAPI app
│   └── ml/                   # ML pipeline
│       ├── detectors/        # Face and object detectors
│       ├── embeddings/       # Face and image embedding models
│       └── storage/          # SQLite and FAISS storage
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Configuration

### Data Storage

Runtime data is stored in the OS app data directory:
- macOS: `~/Library/Application Support/PhotoSense-AI`
- Windows: `%APPDATA%/PhotoSense-AI`
- Linux: `~/.local/share/PhotoSense-AI`

Override with `PHOTOSENSE_DATA_DIR` if needed.

Stored items include `photosense.db`, `indices/`, `cache/`, `logs/`, and `state/`.

### Model Files

ML models are downloaded automatically on first use:
- RetinaFace (face detection)
- YOLOv8 (object detection)
- CLIP (image embeddings)
- ArcFace (face embeddings)

Models are cached in the system's default cache directory.

## Development

### Running Tests

```bash
# Backend tests (when available)
pytest

# Frontend tests (when available)
cd apps/desktop
npm test
```

### Code Style

- Python: Follow PEP 8
- TypeScript/React: Use ESLint and Prettier
- Rust: Use `rustfmt`

### Adding New Features

1. Backend: Add routes in `services/api/routes/`
2. Frontend: Add views in `apps/desktop/src/views/`
3. ML: Add detectors/embeddings in `services/ml/`

## Troubleshooting

### Common Issues

**Models not downloading:**
- Check internet connection
- Ensure sufficient disk space
- Check Python/transformers cache permissions

**Slow processing:**
- Large photo collections take time
- Processing happens in background
- Check system resources (CPU, RAM)

**Database errors:**
- Ensure write permissions in the app data directory
- Check disk space
- Verify SQLite installation

**Tauri build errors:**
- Ensure Rust is properly installed: `rustc --version`
- Update Rust: `rustup update`
- Clear build cache: `cd apps/desktop && rm -rf src-tauri/target`

**API connection errors:**
- Ensure backend is running on port 8000
- Check CORS settings if accessing from browser
- Verify firewall settings

## Performance Tips

- Process photos in batches for large collections
- Use SSD storage for better I/O performance
- Allocate sufficient RAM (8GB+ recommended)
- Close other applications during initial scan

## Security & Privacy

- **100% Local Processing**: All ML models run on your machine
- **No Cloud Services**: No photo data is sent to external servers
- **Local Storage**: All data stored in the app data directory
- **No Telemetry**: No tracking or analytics
- **Optional Geocoding**: Location names (city, country) can be resolved using OpenStreetMap's Nominatim API. This is optional and requires network access. If disabled or offline, GPS coordinates are still stored locally but without place names. The app works fully offline without geocoding.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

This means:
- You can use, modify, and distribute this software
- If you modify and distribute it, you must release your changes under AGPL-3.0
- If you run a modified version as a network service, you must provide source code access
- You must preserve copyright notices and attribution

See the [LICENSE](LICENSE) file for the full license text.

For third-party software licenses, see [LICENSE-THIRD-PARTY](LICENSE-THIRD-PARTY).

## Acknowledgments

- RetinaFace for face detection
- Ultralytics YOLOv8 for object detection
- OpenAI CLIP for image embeddings
- FAISS for efficient vector search
- Tauri for desktop app framework

## Notes

- First run will download ML models automatically (several GB)
- Processing large photo collections may take time
- All data is stored locally—no cloud services used
- Models are cached for faster subsequent runs
