"""
Configuration settings for the Indexer service
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from dotenv import find_dotenv, load_dotenv

# Load environment variables from .env file
load_dotenv(find_dotenv())


class Settings(BaseSettings):
    """Application settings"""
    
    # Service settings
    indexer_host: str = Field(default="localhost", env="INDEXER_HOST")
    indexer_port: int = Field(default=8002, env="INDEXER_PORT")
    
    # OpenSearch settings
    opensearch_url: str = Field(
        default="http://localhost:9200", 
        env="OPENSEARCH_URL"
    )
    opensearch_index: str = Field(
        default="documents", 
        env="OPENSEARCH_INDEX"
    )
    opensearch_auth: Optional[str] = Field(
        default=None, 
        env="OPENSEARCH_AUTH"
    )
    opensearch_use_ssl: bool = Field(
        default=False, 
        env="OPENSEARCH_USE_SSL"
    )
    opensearch_verify_certs: bool = Field(
        default=False, 
        env="OPENSEARCH_VERIFY_CERTS"
    )
    
    # Ollama settings
    ollama_base_url: str = Field(
        default="http://localhost:11434", 
        env="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="nomic-embed-text:v1.5", 
        env="OLLAMA_MODEL"
    )
    
    # Document processing settings
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    
    # Upload settings
    upload_directory: str = Field(
        default="./uploads", 
        env="UPLOAD_DIRECTORY"
    )
    allowed_extensions: str = Field(
        default="pdf,txt,docx,xlsx,csv,md", 
        env="ALLOWED_EXTENSIONS"
    )
    
    # Access control
    default_access_level: str = Field(
        default="user", 
        env="DEFAULT_ACCESS_LEVEL"
    )
    valid_access_levels: str = Field(
        default="administrator,user,guest", 
        env="VALID_ACCESS_LEVELS"
    )
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # OCR settings
    enable_ocr: bool = Field(default=True, env="ENABLE_OCR")
    ocr_language: str = Field(default="eng", env="OCR_LANGUAGE")
    ocr_dpi: int = Field(default=300, env="OCR_DPI")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Get allowed file extensions as list"""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    @property
    def valid_access_levels_list(self) -> list[str]:
        """Get valid access levels as list"""
        return [level.strip().lower() for level in self.valid_access_levels.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()