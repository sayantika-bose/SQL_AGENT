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

class CommonConfig(BaseModel):
    app_name: str = Field(..., description="Application name")
    environment: Environment = Field(Environment.DEVELOPMENT, description="Environment")
    redis: RedisConfig = Field(..., description="Redis configuration")
    logging: LoggingConfig = Field(..., description="Logging configuration")
    debug: bool = Field(False, description="Debug mode")