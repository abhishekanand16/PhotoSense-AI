#!/usr/bin/env python3
"""Test enhanced search capabilities."""

import asyncio
import sys
sys.path.insert(0, '/Users/abhishek/Documents/GitHub/PhotoSense-AI')

from services.ml.utils.search_utils import SearchQueryProcessor

def test_query_processor():
    """Test the query processor with various queries."""
    
    test_queries = [
        "plant",
        "plants",
        "tree",
        "trees",
        "flower",
        "flowers",
        "garden",
        "nature",
        "sunset",
        "beach",
        "car",
        "laptop",
        "sunset at beach",
        "trees in forest",
        "indoor plant",
    ]
    
    print("=" * 70)
    print("TESTING SEARCH QUERY PROCESSOR")
    print("=" * 70)
    
    for query in test_queries:
        result = SearchQueryProcessor.process_query(query)
        
        print(f"\nQuery: '{query}'")
        print(f"  Scene tags: {result['scene_tags']}")
        print(f"  Object patterns: {result['object_patterns']}")
        print(f"  Use CLIP: {result['should_use_clip']}")

if __name__ == '__main__':
    test_query_processor()
