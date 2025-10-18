"""
Helper functions for accessing configuration in the API package.
"""
from typing import Any, Dict, Optional

from common.config.config_manager import get_config_manager


def get_api_config() -> Dict:
    """
    Get the common configuration relevant for API.
    
    Returns:
        API configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.common_config.dict()


def get_redis_config() -> Dict:
    """
    Get Redis configuration parameters.
    
    Returns:
        Redis configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.common_config.redis.dict()


def get_logging_config() -> Dict:
    """
    Get logging configuration parameters.
    
    Returns:
        Logging configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.common_config.logging.dict()


def is_debug_mode() -> bool:
    """
    Check if application is in debug mode.
    
    Returns:
        True if in debug mode, False otherwise
    """
    config_manager = get_config_manager()
    return config_manager.common_config.debug


def get_config_value(path: str, default: Optional[Any] = None) -> Any:
    """
    Get a specific configuration value using dot notation.
    
    Args:
        path: Dot notation path (e.g., 'common.redis.host')
        default: Default value if path not found
        
    Returns:
        Configuration value or default
    """
    config_manager = get_config_manager()
    return config_manager.get_config_value(path, default)