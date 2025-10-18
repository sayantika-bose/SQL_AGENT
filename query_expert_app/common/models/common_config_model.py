from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class RedisConfig(BaseModel):
    host: str = Field("localhost", description="Redis host")
    port: int = Field(6379, description="Redis port")
    db: int = Field(0, description="Redis database number")
    password: Optional[str] = Field(None, description="Redis password")
    ssl: bool = Field(False, description="Use SSL connection")

    @property
    def url(self) -> str:
        """Generate Redis URL from config"""
        auth = f":{self.password}@" if self.password else ""
        protocol = "rediss://" if self.ssl else "redis://"
        return f"{protocol}{auth}{self.host}:{self.port}/{self.db}"

class LoggingConfig(BaseModel):
    level: str = Field("INFO", description="Logging level")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
                       description="Log format")
    file_path: Optional[str] = Field(None, description="Log file path")

class DataApiConfig(BaseModel):
    host: str = Field("localhost", description="Data API host")
    port: int = Field(8001, description="Data API port")
    url: str
    
    @property
    def url(self) -> str:
        """Generate Data API URL"""
        return f"http://{self.host}:{self.port}"

class OllamaConfig(BaseModel):
    model: str = Field("gpt-oss:20b-cloud", description="Ollama model name")
    base_url: str = Field("http://localhost:11434", description="Ollama base URL")

class CommonConfig(BaseModel):
    app_name: str = Field(..., description="Application name")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Environment")
    redis: RedisConfig = Field(..., description="Redis configuration")
    logging: LoggingConfig = Field(..., description="Logging configuration")
    data_api: DataApiConfig = Field(..., description="Data API configuration")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig, description="Ollama configuration")
    debug: bool = Field(False, description="Debug mode")
    
    @property
    def data_api_url(self) -> str:
        """Get Data API URL"""
        return self.data_api.url
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        return self.redis.url