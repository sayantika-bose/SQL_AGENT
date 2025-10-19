"""
Pydantic schemas for API request/response models.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict


class TaskResponse(BaseModel):
    """Response model for task submission"""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(default="INPROGRESS", description="Initial task status")
    message: str = Field(default="Task submitted successfully", description="Status message")


class TaskStatusResponse(BaseModel):
    """Response model for task status queries"""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(
        ..., 
        description="Task status: INPROGRESS, SUCCESS, FAILURE, or NOT_FOUND"
    )
    progress_message: Optional[str] = Field(
        None, 
        description="Descriptive message about current task progress"
    )
    result: Optional[Any] = Field(
        None, 
        description="Task result (only present when status is SUCCESS)"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message (only present when status is FAILURE)"
    )
    
    