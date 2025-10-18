"""
Base schema models for API requests and responses.
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional

class TaskResponse(BaseModel):
    """Response model for task creation."""
    task_id: str
    status: str = "pending"

class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    progress: int
    result: Optional[Any] = None
    message: Optional[str] = None