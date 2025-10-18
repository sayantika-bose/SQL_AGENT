"""
Configuration module for MITRA AI Foundation.
"""
from .config_manager import (
    config_manager,
    get_config_manager,  # Backward compatibility
    get_common_settings,
    get_worker_settings
)
from ..models.common_config_model import CommonConfig
from ..models.worker_config_model import WorkerConfig

__all__ = [
    'config_manager',
    'get_config_manager',  # For backward compatibility
    'get_common_settings',
    'get_worker_settings',
    'CommonConfig',
    'WorkerConfig',
    'common_config',      # Direct access
    'worker_config'       # Direct access
]