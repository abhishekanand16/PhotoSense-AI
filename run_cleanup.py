#!/usr/bin/env python3
"""Quick script to run the duplicate people cleanup."""

import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from services.ml.cleanup_duplicates import full_cleanup

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PhotoSense Duplicate People Cleanup")
    print("="*60)
    
    # First run in dry-run mode to show what would be done
    print("\n🔍 Running analysis (dry run)...\n")
    full_cleanup(dry_run=True)
    
    # Ask user for confirmation
    print("\n" + "="*60)
    response = input("\n⚠️  Apply these changes? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\n✓ Applying changes...\n")
        full_cleanup(dry_run=False)
    else:
        print("\n❌ Cleanup cancelled. No changes were made.")
