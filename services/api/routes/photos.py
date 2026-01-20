"""Photo-related endpoints."""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks

from services.api.models import PhotoResponse
from services.ml.storage.sqlite_store import SQLiteStore
from services.ml.utils import extract_exif_metadata

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("", response_model=List[PhotoResponse])
async def list_photos():
    """Get all photos."""
    store = SQLiteStore()
    try:
        photos = store.get_all_photos()
        # Convert to PhotoResponse format, ensuring all fields are properly formatted
        result = []
        for photo in photos:
            photo_dict = {
                "id": photo["id"],
                "file_path": photo["file_path"],
                "date_taken": photo.get("date_taken"),
                "camera_model": photo.get("camera_model"),
                "width": photo.get("width"),
                "height": photo.get("height"),
                "file_size": photo.get("file_size"),
                "created_at": str(photo.get("created_at", "")) if photo.get("created_at") else "",
            }
            result.append(photo_dict)
        return result
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(photo_id: int):
    """Get a specific photo."""
    store = SQLiteStore()
    try:
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        # Ensure created_at is a string
        if photo.get("created_at") and not isinstance(photo["created_at"], str):
            photo["created_at"] = str(photo["created_at"])
        elif not photo.get("created_at"):
            photo["created_at"] = ""
        return photo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{photo_id}")
async def delete_photo(photo_id: int):
    """Delete a specific photo and all related data, including the file from disk."""
    store = SQLiteStore()
    try:
        # Check if photo exists
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        file_path = photo.get("file_path")
        file_deleted = False
        
        # Delete the file from disk if it exists
        if file_path:
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists() and file_path_obj.is_file():
                    file_path_obj.unlink()
                    file_deleted = True
                    logging.info(f"Deleted file: {file_path}")
                else:
                    logging.warning(f"File not found or not a file: {file_path}")
            except Exception as e:
                logging.error(f"Failed to delete file {file_path}: {str(e)}")
                # Continue with database deletion even if file deletion fails
        
        # Delete the photo and all related data from database
        deleted = store.delete_photo(photo_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete photo from database")
        
        message = f"Photo {photo_id} deleted successfully"
        if file_path and not file_deleted:
            message += " (file was not found on disk)"
        
        return {"status": "success", "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete", response_model=dict)
async def delete_photos(photo_ids: List[int]):
    """Delete multiple photos by their IDs, including files from disk."""
    store = SQLiteStore()
    try:
        deleted_count = 0
        files_deleted = 0
        not_found = []
        errors = []
        
        for photo_id in photo_ids:
            try:
                photo = store.get_photo(photo_id)
                if not photo:
                    not_found.append(photo_id)
                    continue
                
                file_path = photo.get("file_path")
                file_deleted = False
                
                # Delete the file from disk if it exists
                if file_path:
                    try:
                        file_path_obj = Path(file_path)
                        if file_path_obj.exists() and file_path_obj.is_file():
                            file_path_obj.unlink()
                            file_deleted = True
                            files_deleted += 1
                            logging.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        logging.error(f"Failed to delete file {file_path}: {str(e)}")
                        # Continue with database deletion even if file deletion fails
                
                # Delete the photo and all related data from database
                deleted = store.delete_photo(photo_id)
                if deleted:
                    deleted_count += 1
                else:
                    errors.append(photo_id)
            except Exception as e:
                logging.error(f"Failed to delete photo {photo_id}: {str(e)}")
                errors.append(photo_id)
        
        message = f"Deleted {deleted_count} photo(s) from database"
        if files_deleted < deleted_count:
            message += f" ({files_deleted} files deleted from disk)"
        elif files_deleted == deleted_count:
            message += f" ({files_deleted} files deleted from disk)"
        
        return {
            "status": "completed",
            "deleted": deleted_count,
            "files_deleted": files_deleted,
            "not_found": not_found,
            "errors": errors,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{photo_id}/metadata")
async def get_photo_metadata(photo_id: int):
    """
    Get comprehensive metadata for a photo.
    
    Aggregates data from multiple tables:
    - File info (name, size, format, dimensions)
    - Dates (taken, imported)
    - Camera info (make, model)
    - Location (city, region, country, coordinates)
    - Detected people
    - Detected objects
    - Scene tags
    - Custom user tags
    """
    store = SQLiteStore()
    try:
        # Get photo
        photo = store.get_photo(photo_id)
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        file_path = photo.get("file_path", "")
        file_name = file_path.split("/")[-1] if file_path else ""
        file_extension = file_name.split(".")[-1].upper() if "." in file_name else ""
        
        # File info
        file_info = {
            "name": file_name,
            "size": photo.get("file_size"),
            "format": file_extension,
            "width": photo.get("width"),
            "height": photo.get("height"),
            "path": file_path,
        }
        
        # Dates
        dates = {
            "date_taken": photo.get("date_taken"),
            "date_imported": photo.get("created_at"),
        }
        
        # Camera info
        camera = {
            "model": photo.get("camera_model"),
        }
        
        # Location
        location_data = store.get_location(photo_id)
        location = None
        if location_data:
            location = {
                "city": location_data.get("city"),
                "region": location_data.get("region"),
                "country": location_data.get("country"),
                "latitude": location_data.get("latitude"),
                "longitude": location_data.get("longitude"),
            }
        
        # Detected people
        faces = store.get_faces_for_photo(photo_id)
        people = []
        seen_person_ids = set()
        for face in faces:
            person_id = face.get("person_id")
            if person_id and person_id not in seen_person_ids:
                person = store.get_person(person_id)
                if person:
                    people.append({
                        "id": person_id,
                        "name": person.get("name"),
                    })
                    seen_person_ids.add(person_id)
        
        # Detected objects (exclude 'person' and 'other')
        objects_data = store.get_objects_for_photo(photo_id)
        objects = []
        for obj in objects_data:
            category = obj.get("category", "")
            if "person" not in category.lower() and category.lower() != "other":
                objects.append({
                    "category": category,
                    "confidence": obj.get("confidence"),
                })
        
        # Scene tags
        scenes_data = store.get_scenes_for_photo(photo_id)
        scenes = []
        for scene in scenes_data:
            label = scene.get("scene_label", "")
            # Skip florence: prefixed tags for cleaner display
            if not label.startswith("florence:"):
                scenes.append({
                    "label": label,
                    "confidence": scene.get("confidence"),
                })
        
        # Custom user tags
        custom_tags = store.get_tags_for_photo(photo_id)
        
        return {
            "photo_id": photo_id,
            "file_info": file_info,
            "dates": dates,
            "camera": camera,
            "location": location,
            "people": people,
            "objects": objects,
            "scenes": scenes,
            "custom_tags": custom_tags,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-metadata", response_model=dict)
async def update_metadata_for_all_photos(background_tasks: BackgroundTasks):
    """Update metadata for all photos that are missing it."""
    store = SQLiteStore()
    
    async def update_metadata_async():
        """Background task to update metadata for all photos."""
        photos = store.get_all_photos()
        updated = 0
        errors = 0
        
        for photo in photos:
            try:
                file_path = photo["file_path"]
                # Check if file exists
                if not Path(file_path).exists():
                    logging.warning(f"Photo file not found: {file_path}")
                    continue
                
                # Check if metadata is missing
                if not photo.get("date_taken") or not photo.get("width"):
                    # Extract metadata
                    metadata = extract_exif_metadata(file_path)
                    
                    # Update if we got metadata
                    if metadata.get("date_taken") or metadata.get("width"):
                        update_data = {}
                        if not photo.get("date_taken") and metadata.get("date_taken"):
                            update_data["date_taken"] = metadata.get("date_taken")
                        if not photo.get("camera_model") and metadata.get("camera_model"):
                            update_data["camera_model"] = metadata.get("camera_model")
                        if not photo.get("width") and metadata.get("width"):
                            update_data["width"] = metadata.get("width")
                        if not photo.get("height") and metadata.get("height"):
                            update_data["height"] = metadata.get("height")
                        if not photo.get("file_size") and metadata.get("file_size"):
                            update_data["file_size"] = metadata.get("file_size")
                        
                        if update_data:
                            store.update_photo_metadata(photo_id=photo["id"], **update_data)
                            updated += 1
            except Exception as e:
                logging.error(f"Failed to update metadata for photo {photo.get('id')}: {str(e)}")
                errors += 1
        
        logging.info(f"Metadata update completed: {updated} photos updated, {errors} errors")
    
    background_tasks.add_task(update_metadata_async)
    
    return {
        "status": "started",
        "message": "Metadata update started in background"
    }
