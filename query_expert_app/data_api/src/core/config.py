"""
Configuration management for Data API
"""
import os
from functools import lru_cache
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.config.config_manager import get_common_settings
from common.models.common_config_model import CommonConfig


class DataApiSettings:
    """Data API specific settings"""
    
    def __init__(self, common_config: CommonConfig):
        self._common_config = common_config
        
    @property
    def database_path(self) -> str:
        """Get database path from environment or use default"""
        return os.getenv("DATABASE_PATH", "data/database.db")
    
    @property
    def data_api_host(self) -> str:
        """Get Data API host"""
        return os.getenv("DATA_API_HOST", self._common_config.data_api.host)
    
    @property
    def data_api_port(self) -> int:
        """Get Data API port"""
        return int(os.getenv("DATA_API_PORT", self._common_config.data_api.port))
    
    @property
    def common_config(self) -> CommonConfig:
        """Get common configuration"""
        return self._common_config
    
    @property
    def app_name(self) -> str:
        """Get application name"""
        return self._common_config.app_name
    
    @property
    def environment(self) -> str:
        """Get environment"""
        return self._common_config.environment.value
    
    @property
    def debug(self) -> bool:
        """Get debug mode"""
        return self._common_config.debug
    
    @property
    def max_query_length(self) -> int:
        """Maximum allowed query length"""
        return int(os.getenv("MAX_QUERY_LENGTH", "10000"))
    
    @property
    def query_timeout(self) -> int:
        """Query timeout in seconds"""
        return int(os.getenv("QUERY_TIMEOUT", "30"))


@lru_cache()
def get_settings() -> DataApiSettings:
    """Get cached settings instance"""
    common_config = get_common_settings()
    return DataApiSettings(common_config)