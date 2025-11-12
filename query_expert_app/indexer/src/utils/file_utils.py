"""
Utility functions for file operations
"""
import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal hash string
    """
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()


def get_file_info(file_path: Path) -> dict:
    """
    Get comprehensive file information
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
    """
    if not file_path.exists():
        return {"exists": False}
    
    stat = file_path.stat()
    
    return {
        "exists": True,
        "name": file_path.name,
        "size": stat.st_size,
        "extension": file_path.suffix.lower().lstrip('.'),
        "created": stat.st_ctime,
        "modified": stat.st_mtime,
        "is_file": file_path.is_file(),
        "is_directory": file_path.is_dir()
    }


def ensure_directory(directory_path: Path) -> bool:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        directory_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing or replacing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    cleaned = filename
    
    for char in invalid_chars:
        cleaned = cleaned.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip(' .')
    
    # Ensure filename is not empty
    if not cleaned:
        cleaned = "unnamed_file"
    
    return cleaned


def get_unique_filename(directory: Path, filename: str) -> str:
    """
    Get a unique filename in the directory by adding a counter if needed
    
    Args:
        directory: Target directory
        filename: Desired filename
        
    Returns:
        Unique filename
    """
    file_path = directory / filename
    
    if not file_path.exists():
        return filename
    
    # Split filename and extension
    name_part = Path(filename).stem
    ext_part = Path(filename).suffix
    
    counter = 1
    while True:
        new_filename = f"{name_part}_{counter}{ext_part}"
        new_path = directory / new_filename
        
        if not new_path.exists():
            return new_filename
        
        counter += 1


def validate_file_extension(filename: str, allowed_extensions: list) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension against allowed list
    
    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "No filename provided"
    
    extension = Path(filename).suffix.lower().lstrip('.')
    
    if not extension:
        return False, "File has no extension"
    
    if extension not in [ext.lower() for ext in allowed_extensions]:
        allowed_str = ", ".join(allowed_extensions)
        return False, f"Extension '{extension}' not allowed. Allowed: {allowed_str}"
    
    return True, None