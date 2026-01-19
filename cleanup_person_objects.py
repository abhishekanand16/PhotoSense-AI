#!/usr/bin/env python3
"""Cleanup script to remove 'person' objects from the objects table."""

import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ml.storage.sqlite_store import SQLiteStore
import sqlite3

def cleanup_person_objects(dry_run: bool = True):
    """Remove all 'person' objects from the database.
    
    Since we have a dedicated face detection system for people,
    we don't need person objects in the objects table.
    
    Args:
        dry_run: If True, only shows what would be removed
    """
    print("=" * 60)
    print("PhotoSense Person Objects Cleanup")
    print("=" * 60)
    
    store = SQLiteStore()
    
    # Find all person objects
    conn = sqlite3.connect(store.db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find objects with category containing 'person'
    cursor.execute("""
        SELECT id, photo_id, category, confidence 
        FROM objects 
        WHERE category LIKE '%person%'
        ORDER BY photo_id
    """)
    
    person_objects = cursor.fetchall()
    
    print(f"\nFound {len(person_objects)} person objects in database")
    
    if len(person_objects) == 0:
        print("✓ No person objects to remove!")
        conn.close()
        return
    
    # Show some examples
    if len(person_objects) > 0:
        print("\nExamples:")
        for obj in person_objects[:5]:
            print(f"  - Object {obj['id']}: photo_id={obj['photo_id']}, "
                  f"category='{obj['category']}', confidence={obj['confidence']:.2f}")
        
        if len(person_objects) > 5:
            print(f"  ... and {len(person_objects) - 5} more")
    
    # Count affected photos
    cursor.execute("""
        SELECT COUNT(DISTINCT photo_id) 
        FROM objects 
        WHERE category LIKE '%person%'
    """)
    affected_photos = cursor.fetchone()[0]
    print(f"\nAffected photos: {affected_photos}")
    
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")
        print("Run with --apply flag to remove these objects")
    else:
        print("\n⚠️  Removing person objects...")
        cursor.execute("DELETE FROM objects WHERE category LIKE '%person%'")
        conn.commit()
        print(f"✓ Removed {len(person_objects)} person objects")
        print("✓ Cleanup complete!")
    
    conn.close()
    
    print("\nNote: Future scans will no longer detect people as objects.")
    print("Use the People tab for face detection instead.")
    print("=" * 60)


if __name__ == "__main__":
    # Check for --apply flag
    dry_run = "--apply" not in sys.argv
    
    if dry_run:
        print("Running in DRY RUN mode (use --apply to make actual changes)\n")
    else:
        print("⚠️  APPLYING CHANGES - This will modify your database!\n")
    
    cleanup_person_objects(dry_run=dry_run)
