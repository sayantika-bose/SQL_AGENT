"""
Helper functions for accessing configuration in the worker package.
"""
from typing import Any, Dict, Optional

from common.config.config_manager import get_config_manager


def get_worker_config() -> Dict:
    """
    Get the complete worker configuration.
    
    Returns:
        Worker configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.worker_config.dict()


def get_celery_config() -> Dict:
    """
    Get Celery configuration parameters.
    
    Returns:
        Celery configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.worker_config.celery.dict()


def get_task_config() -> Dict:
    """
    Get task configuration parameters.
    
    Returns:
        Task configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.worker_config.tasks.dict()


def get_redis_config() -> Dict:
    """
    Get Redis configuration parameters.
    
    Returns:
        Redis configuration as a dictionary
    """
    config_manager = get_config_manager()
    return config_manager.common_config.redis.dict()


def get_config_value(path: str, default: Optional[Any] = None) -> Any:
    """
    Get a specific configuration value using dot notation.
    
    Args:
        path: Dot notation path (e.g., 'worker.tasks.max_retries')
        default: Default value if path not found
        
    Returns:
        Configuration value or default
    """
    config_manager = get_config_manager()
    return config_manager.get_config_value(path, default)