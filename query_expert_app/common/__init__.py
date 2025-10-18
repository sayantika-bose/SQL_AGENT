"""
Common package for shared functionality across the application.
"""

from .config.config_manager import ConfigManager, get_config_manager

__all__ = ['ConfigManager', 'get_config_manager']
