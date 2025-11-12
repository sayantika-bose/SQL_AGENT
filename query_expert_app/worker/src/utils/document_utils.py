"""
Document-related utility functions
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)


def extract_document_references(content: str) -> List[str]:
    """
    Extract document filenames from tool response content
    
    Args:
        content: Tool response content that may contain document references
        
    Returns:
        List of unique document filenames from actual search results
    """
    # First, look for the special marker with actual filenames from search results
    marker_pattern = r'__DOCUMENT_REFERENCES__:\s*([^\n]+)'
    marker_match = re.search(marker_pattern, content)
    
    if marker_match:
        # Extract filenames from the marker
        filenames_str = marker_match.group(1).strip()
        if filenames_str:
            filenames = [name.strip() for name in filenames_str.split(',') if name.strip()]
            logger.debug(f"Extracted references from marker: {filenames}")
            return filenames
    
    # Fallback: Look for document references in the formatted text
    references = []
    
    # Pattern 1: Look for "From: filename.ext" patterns
    from_pattern = r'\*\*From:\s*([^*\n]+\.[a-zA-Z0-9]{2,5})\*\*'
    from_matches = re.findall(from_pattern, content)
    references.extend([match.strip() for match in from_matches])
    
    # Pattern 2: Look for "• **filename.ext**" patterns in source lists
    source_pattern = r'•\s*\*\*([^*]+\.[a-zA-Z0-9]{2,5})\*\*'
    source_matches = re.findall(source_pattern, content)
    references.extend([match.strip() for match in source_matches])
    
    # Clean and deduplicate
    cleaned_refs = []
    for ref in references:
        # Remove markdown formatting and extra text
        clean_ref = re.sub(r'\*\*([^*]+)\*\*', r'\1', ref)
        clean_ref = clean_ref.strip()
        
        # Only include if it looks like a valid filename
        if clean_ref and '.' in clean_ref and len(clean_ref) < 100:
            if clean_ref not in cleaned_refs:
                cleaned_refs.append(clean_ref)
    
    logger.debug(f"Extracted references from content: {cleaned_refs}")
    return cleaned_refs