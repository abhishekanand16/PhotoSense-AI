"""Search utilities for enhanced natural language query processing."""

from typing import List, Set, Dict, Tuple


class SearchQueryProcessor:
    """Process natural language search queries into scene/object tags."""
    
    # Comprehensive keyword mapping for natural language queries
    KEYWORD_MAPPINGS = {
        # Nature & Plants
        'plant': ['plant', 'garden', 'nature', 'flowers'],
        'plants': ['plant', 'garden', 'nature', 'flowers'],
        'tree': ['tree', 'forest', 'nature', 'park'],
        'trees': ['tree', 'forest', 'nature', 'park'],
        'flower': ['flowers', 'garden', 'nature'],
        'flowers': ['flowers', 'garden', 'nature'],
        'garden': ['garden', 'flowers', 'nature', 'park'],
        'nature': ['nature', 'forest', 'tree', 'landscape', 'outdoor'],
        'forest': ['forest', 'tree', 'nature'],
        'woods': ['forest', 'tree', 'nature'],
        'jungle': ['forest', 'rainforest', 'nature'],
        'grass': ['nature', 'park', 'garden'],
        'lawn': ['nature', 'park', 'garden'],
        'vegetation': ['nature', 'forest', 'garden'],
        
        # Landscapes
        'mountain': ['mountain', 'landscape', 'nature', 'outdoor'],
        'mountains': ['mountain', 'landscape', 'nature', 'outdoor'],
        'hill': ['mountain', 'landscape', 'nature'],
        'hills': ['mountain', 'landscape', 'nature'],
        'valley': ['landscape', 'nature', 'mountain'],
        'cliff': ['landscape', 'mountain'],
        'canyon': ['landscape', 'mountain'],
        'desert': ['landscape', 'nature'],
        
        # Water
        'beach': ['beach', 'water', 'outdoor'],
        'ocean': ['water', 'beach', 'outdoor'],
        'sea': ['water', 'beach', 'outdoor'],
        'lake': ['water', 'nature', 'outdoor'],
        'river': ['water', 'nature', 'outdoor'],
        'waterfall': ['water', 'nature', 'outdoor'],
        'pond': ['water', 'nature', 'park'],
        'stream': ['water', 'nature', 'forest'],
        
        # Sky & Weather
        'sunset': ['sunset', 'sky', 'outdoor'],
        'sunrise': ['sunrise', 'sky', 'outdoor'],
        'sky': ['sky', 'outdoor'],
        'cloud': ['sky', 'outdoor'],
        'clouds': ['sky', 'outdoor'],
        'rain': ['outdoor'],
        'snow': ['snow', 'outdoor', 'mountain'],
        'snowy': ['snow', 'outdoor', 'mountain'],
        
        # Urban
        'city': ['city', 'building', 'street', 'urban', 'outdoor'],
        'urban': ['city', 'building', 'street', 'outdoor'],
        'street': ['city', 'street', 'outdoor'],
        'road': ['street', 'outdoor'],
        'building': ['building', 'city'],
        'buildings': ['building', 'city'],
        'architecture': ['building', 'city'],
        
        # Indoor/Outdoor
        'indoor': ['indoor'],
        'indoors': ['indoor'],
        'inside': ['indoor'],
        'outdoor': ['outdoor', 'nature', 'sky'],
        'outdoors': ['outdoor', 'nature', 'sky'],
        'outside': ['outdoor', 'nature', 'sky'],
        
        # Recreation
        'park': ['park', 'nature', 'outdoor', 'tree'],
        'playground': ['park', 'outdoor'],
        'sports': ['sports', 'outdoor'],
        
        # Objects (map to object detection categories)
        'car': ['vehicle', 'street'],
        'cars': ['vehicle', 'street'],
        'vehicle': ['vehicle', 'street'],
        'bicycle': ['vehicle', 'outdoor'],
        'bike': ['vehicle', 'outdoor'],
        'person': ['person'],
        'people': ['person'],
        'animal': ['animal', 'nature'],
        'animals': ['animal', 'nature'],
        'dog': ['animal'],
        'cat': ['animal'],
        'bird': ['animal', 'nature', 'outdoor'],
        'birds': ['animal', 'nature', 'outdoor'],
        
        # Time
        'night': ['night', 'sky'],
        'nighttime': ['night', 'sky'],
        'evening': ['sunset', 'night', 'sky'],
        'morning': ['sunrise', 'sky'],
        'day': ['outdoor', 'sky'],
        'daytime': ['outdoor', 'sky'],
    }
    
    # Object name synonyms and variations
    OBJECT_SYNONYMS = {
        'plant': ['plant', 'potted plant'],
        'plants': ['plant', 'potted plant'],
        'tree': ['plant', 'potted plant'],  # Trees might be detected as plants
        'trees': ['plant', 'potted plant'],
        'flower': ['plant', 'potted plant', 'vase'],
        'flowers': ['plant', 'potted plant', 'vase'],
        'car': ['car', 'vehicle'],
        'automobile': ['car', 'vehicle'],
        'bike': ['bicycle', 'vehicle'],
        'motorcycle': ['motorcycle', 'vehicle'],
        'dog': ['dog', 'animal'],
        'cat': ['cat', 'animal'],
        'person': ['person'],
        'people': ['person'],
        'human': ['person'],
        'chair': ['chair', 'furniture'],
        'table': ['dining table', 'furniture'],
        'laptop': ['laptop', 'electronics'],
        'computer': ['laptop', 'electronics'],
        'phone': ['cell phone', 'electronics'],
        'tv': ['tv', 'electronics'],
        'television': ['tv', 'electronics'],
        'book': ['book', 'item'],
        'bottle': ['bottle', 'food'],
        'cup': ['cup', 'food'],
        'glass': ['wine glass', 'cup', 'food'],
    }
    
    @staticmethod
    def extract_keywords(query: str) -> Set[str]:
        """
        Extract searchable keywords from a natural language query.
        
        Args:
            query: Natural language search query
            
        Returns:
            Set of scene/object tags to search for
        """
        if not query:
            return set()
        
        query_lower = query.lower().strip()
        keywords = set()
        
        # Check each word in the query
        words = query_lower.split()
        
        for word in words:
            # Remove common punctuation
            clean_word = word.strip('.,!?;:')
            
            # Check if word matches any mapping
            if clean_word in SearchQueryProcessor.KEYWORD_MAPPINGS:
                keywords.update(SearchQueryProcessor.KEYWORD_MAPPINGS[clean_word])
        
        # Also check multi-word phrases
        for phrase, tags in SearchQueryProcessor.KEYWORD_MAPPINGS.items():
            if phrase in query_lower:
                keywords.update(tags)
        
        return keywords
    
    @staticmethod
    def get_object_variations(query: str) -> List[str]:
        """
        Get object name variations for searching object detections.
        
        Args:
            query: Search term (e.g., "plant", "car")
            
        Returns:
            List of object category patterns to match
        """
        query_lower = query.lower().strip()
        variations = []
        
        # Check direct synonyms
        if query_lower in SearchQueryProcessor.OBJECT_SYNONYMS:
            variations.extend(SearchQueryProcessor.OBJECT_SYNONYMS[query_lower])
        
        # Also check if any keyword mappings include object categories
        keywords = SearchQueryProcessor.extract_keywords(query)
        variations.extend(keywords)
        
        # Add the original query
        variations.append(query_lower)
        
        return list(set(variations))  # Remove duplicates
    
    @staticmethod
    def process_query(query: str) -> Dict[str, any]:
        """
        Process a search query and return structured search parameters.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary with:
            - scene_tags: List of scene labels to search
            - object_patterns: List of object category patterns to match
            - should_use_clip: Whether to fall back to CLIP semantic search
        """
        if not query or len(query.strip()) < 2:
            return {
                'scene_tags': [],
                'object_patterns': [],
                'should_use_clip': False
            }
        
        # Extract scene keywords
        scene_tags = list(SearchQueryProcessor.extract_keywords(query))
        
        # Extract object variations
        object_patterns = SearchQueryProcessor.get_object_variations(query)
        
        # Determine if we should use CLIP fallback
        # Use CLIP if: complex query, no matches, or very specific/creative query
        should_use_clip = (
            len(query.split()) > 3 or  # Complex multi-word query
            (not scene_tags and not object_patterns) or  # No matches found
            any(word in query.lower() for word in ['like', 'similar', 'reminds', 'looks'])  # Similarity query
        )
        
        return {
            'scene_tags': scene_tags,
            'object_patterns': object_patterns,
            'should_use_clip': should_use_clip
        }
