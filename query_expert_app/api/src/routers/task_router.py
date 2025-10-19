"""
Base router for task-related endpoints.

This module provides the foundation for task management endpoints.
Specific applications should define their own task routers in their respective packages.
"""
from fastapi import APIRouter, HTTPException

from api.src.services.task_service import send_task_to_celery, parse_task_result
from api.src.services.redis_service import get_task_info
from api.src.models.schemas import TaskResponse, TaskStatusResponse

# Create a base router that can be extended by applications
base_router = APIRouter(tags=["tasks"])

@base_router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """
    Get the status of a task.
    
    This endpoint retrieves task status from Redis.
    
    Returns:
        TaskStatusResponse with:
            - task_id: The task identifier
            - status: One of "INPROGRESS", "SUCCESS", "FAILURE", "NOT_FOUND"
            - progress_message: Descriptive message about current task state
            - result: Task result (only present on SUCCESS)
            - error: Error message (only present on FAILURE)
    """
    # Get task info from Redis
    task_info = get_task_info(task_id)
    
    if task_info.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Parse result if it exists
    result = parse_task_result(task_info.get("result"))
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task_info.get("status", "PENDING"),
        progress_message=task_info.get("progress_message", "Processing"),
        result=result,
        error=task_info.get("error")
    )