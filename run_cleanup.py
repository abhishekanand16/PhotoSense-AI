#!/usr/bin/env python3
# PhotoSense-AI - https://github.com/abhishekanand16/PhotoSense-AI
# Copyright (c) 2026 Abhishek Anand. Licensed under AGPL-3.0.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.ml.cleanup_duplicates import full_cleanup

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PhotoSense Duplicate People Cleanup")
    print("="*60)
    
    print("\n🔍 Running analysis (dry run)...\n")
    full_cleanup(dry_run=True)
    
    print("\n" + "="*60)
    response = input("\n⚠️  Apply these changes? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\n✓ Applying changes...\n")
        full_cleanup(dry_run=False)
    else:
        print("\n❌ Cleanup cancelled. No changes were made.")
