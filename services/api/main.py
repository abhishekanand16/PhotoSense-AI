"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.routes import faces, objects, people, photos, scan, scenes, search, stats

app = FastAPI(
    title="PhotoSense-AI API",
    description="Local API service for PhotoSense-AI desktop application",
    version="1.0.0",
)

# CORS middleware for desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(photos.router)
app.include_router(people.router)
app.include_router(faces.router)
app.include_router(scan.router)
app.include_router(search.router)
app.include_router(objects.router)
app.include_router(scenes.router)
app.include_router(stats.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "PhotoSense-AI API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
