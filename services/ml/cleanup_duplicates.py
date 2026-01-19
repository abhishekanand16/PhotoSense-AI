"""Cleanup utility to merge duplicate people based on cluster_id."""

import logging
from collections import defaultdict
from typing import Dict, List

from services.ml.storage.sqlite_store import SQLiteStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_duplicate_people(store: SQLiteStore) -> Dict[int, List[Dict]]:
    """Find people with duplicate cluster_ids.
    
    Returns:
        Dictionary mapping cluster_id to list of people with that cluster_id.
        Only includes cluster_ids that have more than one person.
    """
    all_people = store.get_all_people()
    
    # Group people by cluster_id
    cluster_groups = defaultdict(list)
    for person in all_people:
        cluster_id = person.get('cluster_id')
        if cluster_id is not None:  # Skip people without cluster_id
            cluster_groups[cluster_id].append(person)
    
    # Filter to only duplicates (more than one person per cluster)
    duplicates = {
        cluster_id: people 
        for cluster_id, people in cluster_groups.items() 
        if len(people) > 1
    }
    
    return duplicates


def merge_duplicate_people(store: SQLiteStore, dry_run: bool = False) -> Dict:
    """Merge people with duplicate cluster_ids.
    
    For each cluster_id with multiple people:
    1. Keep the oldest person (first created)
    2. Merge all other people into the oldest one
    3. The name is preserved from the oldest person, or the first named person
    
    Args:
        store: SQLiteStore instance
        dry_run: If True, only report what would be done without making changes
        
    Returns:
        Statistics about the merge operation
    """
    duplicates = find_duplicate_people(store)
    
    if not duplicates:
        logger.info("No duplicate people found!")
        return {
            "status": "success",
            "duplicates_found": 0,
            "merges_performed": 0,
            "people_removed": 0
        }
    
    logger.info(f"Found {len(duplicates)} cluster_ids with duplicate people")
    
    merges_performed = 0
    people_removed = 0
    
    for cluster_id, people in duplicates.items():
        # Sort by created_at to find the oldest
        people_sorted = sorted(people, key=lambda p: p.get('created_at', ''))
        
        # Keep the oldest person
        target_person = people_sorted[0]
        target_id = target_person['id']
        
        # Check if any person has a name - prefer named person as target
        named_people = [p for p in people_sorted if p.get('name')]
        if named_people:
            target_person = named_people[0]
            target_id = target_person['id']
        
        logger.info(f"\nCluster {cluster_id}: Found {len(people)} duplicate people")
        logger.info(f"  Keeping person {target_id} (name: {target_person.get('name', 'Unnamed')})")
        
        # Merge all others into the target
        for person in people_sorted:
            if person['id'] == target_id:
                continue
                
            source_id = person['id']
            logger.info(f"  Merging person {source_id} (name: {person.get('name', 'Unnamed')}) into {target_id}")
            
            if not dry_run:
                # Get face count before merge
                faces_before = store.get_faces_for_person(source_id)
                store.merge_people(source_id, target_id)
                logger.info(f"    Moved {len(faces_before)} faces from person {source_id} to {target_id}")
                people_removed += 1
            
            merges_performed += 1
    
    result = {
        "status": "success",
        "duplicates_found": len(duplicates),
        "merges_performed": merges_performed,
        "people_removed": people_removed if not dry_run else 0,
        "dry_run": dry_run
    }
    
    if dry_run:
        logger.info("\n=== DRY RUN - No changes made ===")
        logger.info(f"Would merge {merges_performed} duplicate people")
    else:
        logger.info("\n=== Cleanup Complete ===")
        logger.info(f"Merged {merges_performed} duplicate people")
        logger.info(f"Removed {people_removed} duplicate person entries")
    
    return result


def cleanup_orphaned_people(store: SQLiteStore, dry_run: bool = False) -> Dict:
    """Remove people who have no faces assigned to them.
    
    Args:
        store: SQLiteStore instance
        dry_run: If True, only report what would be done without making changes
        
    Returns:
        Statistics about the cleanup operation
    """
    all_people = store.get_all_people()
    orphaned = []
    
    for person in all_people:
        faces = store.get_faces_for_person(person['id'])
        if len(faces) == 0:
            orphaned.append(person)
    
    logger.info(f"Found {len(orphaned)} people with no faces")
    
    if not dry_run:
        for person in orphaned:
            logger.info(f"  Deleting person {person['id']} (name: {person.get('name', 'Unnamed')})")
            store.delete_person(person['id'])
    
    return {
        "status": "success",
        "orphaned_people_found": len(orphaned),
        "orphaned_people_removed": len(orphaned) if not dry_run else 0,
        "dry_run": dry_run
    }


def full_cleanup(dry_run: bool = True) -> None:
    """Run full cleanup: merge duplicates and remove orphans.
    
    Args:
        dry_run: If True, only report what would be done without making changes
    """
    logger.info("=" * 60)
    logger.info("PhotoSense People Cleanup Utility")
    logger.info("=" * 60)
    
    store = SQLiteStore()
    
    # Step 1: Merge duplicate people
    logger.info("\nStep 1: Merging duplicate people...")
    merge_result = merge_duplicate_people(store, dry_run=dry_run)
    
    # Step 2: Clean up orphaned people
    logger.info("\nStep 2: Cleaning up orphaned people...")
    orphan_result = cleanup_orphaned_people(store, dry_run=dry_run)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Duplicate people found: {merge_result['duplicates_found']}")
    logger.info(f"Merges performed: {merge_result['merges_performed']}")
    logger.info(f"Orphaned people found: {orphan_result['orphaned_people_found']}")
    
    if dry_run:
        logger.info("\n⚠️  DRY RUN MODE - No changes were made")
        logger.info("Run with dry_run=False to apply changes")
    else:
        logger.info(f"\n✓ Removed {merge_result['people_removed']} duplicate people")
        logger.info(f"✓ Removed {orphan_result['orphaned_people_removed']} orphaned people")
        logger.info("✓ Cleanup complete!")


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        dry_run = False
        logger.warning("⚠️  APPLYING CHANGES - This will modify your database!")
    else:
        logger.info("Running in DRY RUN mode (use --apply to make actual changes)")
    
    full_cleanup(dry_run=dry_run)
