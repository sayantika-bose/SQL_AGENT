from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from enum import Enum

class CeleryConfig(BaseModel):
    broker_url: Optional[str] = Field(None, description="Celery broker URL")
    result_backend: Optional[str] = Field(None, description="Celery result backend")
    task_serializer: str = Field("json", description="Task serializer")
    result_serializer: str = Field("json", description="Result serializer")
    accept_content: List[str] = Field(["json"], description="Accepted content types")
    task_track_started: bool = Field(True, description="Track task started")
    worker_concurrency: int = Field(4, description="Worker concurrency")
    worker_prefetch_multiplier: int = Field(1, description="Prefetch multiplier")
    task_time_limit: int = Field(3600, description="Task time limit in seconds")
    task_soft_time_limit: int = Field(3540, description="Task soft time limit in seconds")

class TasksConfig(BaseModel):
    default_timeout: int = Field(3600, description="Default task timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: int = Field(60, description="Retry delay in seconds")
    progress_update_interval: int = Field(5, description="Progress update interval in seconds")

class LogAnalysisConfig(BaseModel):
    batch_size: int = Field(100, description="Batch size for log processing")
    analysis_methods: List[str] = Field(
        ["pattern_matching", "anomaly_detection", "correlation"],
        description="Available analysis methods"
    )
    enable_detailed_logging: bool = Field(True, description="Enable detailed logging")
    max_log_size_mb: int = Field(50, description="Maximum log size in MB")

class WorkerConfig(BaseModel):
    celery: CeleryConfig = Field(..., description="Celery configuration")
    tasks: TasksConfig = Field(..., description="Tasks configuration")
    log_analysis: LogAnalysisConfig = Field(..., description="Log analysis configuration")