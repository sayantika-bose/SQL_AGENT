import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache
import logging

from common.models.common_config_model import CommonConfig

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self):
        self._common_config: Optional[CommonConfig] = None
        self._common_config_path: Optional[Path] = None
        self._initialized: bool = False
        
    def _get_env_var(self, var_name: str, default: Optional[str] = None) -> str:
        """Get environment variable with validation"""
        value = os.getenv(var_name, default)
        
        return value
    
    def _load_json_config(self, config_path: Path) -> Dict[str, Any]:
        """Load JSON configuration from file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error reading config file {config_path}: {e}")
    
    def _resolve_config_paths(self):
        """Resolve configuration file paths from environment variables"""
        # Common config path
        common_config_env = self._get_env_var("COMMON_CONFIG_PATH")
        self._common_config_path = Path(common_config_env)
        
    
        logger.info(f"Common config path: {self._common_config_path}")
    
    def initialize(self, common_config_path=None):
        """Initialize and validate both configurations
        
        Args:
            common_config_path: Optional explicit path to common config  
        """
        try:
            # Use explicit paths if provided, otherwise resolve from environment
            if common_config_path:
                self._common_config_path = Path(common_config_path)
                
            # If paths weren't provided explicitly, resolve from environment
            if not self._common_config_path:
                self._resolve_config_paths()
            
            # Load and validate common config
            common_config_data = self._load_json_config(self._common_config_path)
            self._common_config = CommonConfig(**common_config_data)
            logger.info(f"Common configuration loaded and validated successfully")
            
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    @property
    def common_config(self) -> CommonConfig:
        """Get the validated common configuration"""
        if not self._initialized:
            self.initialize()
        if self._common_config is None:
            raise RuntimeError("Common configuration not available")
        return self._common_config
    
    
    def reload(self):
        """Reload both configurations from files"""
        self._common_config = None
        self._initialized = False
        self.initialize()

# Create a singleton instance
config_manager = ConfigManager()

# Backward compatibility functions
@lru_cache()
def get_config_manager() -> ConfigManager:
    """Get the config manager instance (for backward compatibility)"""
    return config_manager

@lru_cache()
def get_common_settings() -> CommonConfig:
    """Cached function to get common settings"""
    return config_manager.common_config

# Don't export configs directly as they require initialization first