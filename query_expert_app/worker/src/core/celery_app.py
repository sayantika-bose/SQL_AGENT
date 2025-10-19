"""
Celery application configuration with Redis broker.
Completely decoupled from API components.
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import redis
import os
from typing import Dict, Optional, Any, Union

from common.config.config_manager import get_config_manager

# Get configuration
config_manager = get_config_manager()
common_config = config_manager.common_config
worker_config = config_manager.worker_config

# Redis connection settings from config
redis_config = common_config.redis
REDIS_HOST = redis_config.host
REDIS_PORT = redis_config.port
REDIS_DB = redis_config.db
REDIS_PASSWORD = redis_config.password

# Create Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Create Celery app with Redis broker
celery_app = Celery(
    'worker',
    broker=worker_config.celery.broker_url,
    backend=worker_config.celery.result_backend
)

# Configure Celery
celery_app.conf.update(
    task_serializer=worker_config.celery.task_serializer,
    accept_content=worker_config.celery.accept_content,
    result_serializer=worker_config.celery.result_serializer,
    enable_utc=True,
    task_track_started=worker_config.celery.task_track_started,
    worker_prefetch_multiplier=worker_config.celery.worker_prefetch_multiplier,
    worker_concurrency=worker_config.celery.worker_concurrency,
    task_time_limit=worker_config.celery.task_time_limit,
    task_soft_time_limit=worker_config.celery.task_soft_time_limit,
    task_routes={
        'long_running_task': {'queue': 'default'}
    }
)

# Task status constants
TASK_STATUS_INPROGRESS = "INPROGRESS"
TASK_STATUS_SUCCESS = "SUCCESS"
TASK_STATUS_FAILURE = "FAILURE"
TASK_STATUS_NOT_FOUND = "NOT_FOUND"

# Task progress tracking with Redis
@task_prerun.connect
def task_prerun_handler(task_id: str, task: Any, *args: Any, **kwargs: Any) -> None:
    """
    Handler called before task execution.
    Updates Redis with INPROGRESS status.
    
    Args:
        task_id: The Celery task ID
        task: The task instance
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_INPROGRESS,
            "progress_message": "Processing Your Request",
            "result": ""
        }
    )
    # Set expiration to avoid Redis memory issues (24 hours)
    redis_client.expire(f"task:{task_id}", 86400)

@task_postrun.connect
def task_postrun_handler(task_id: str, task: Any, retval: Any, state: str, *args: Any, **kwargs: Any) -> None:
    """
    Handler called after task execution.
    Updates Redis with SUCCESS status and result.
    
    Args:
        task_id: The Celery task ID
        task: The task instance
        retval: The return value of the task
        state: The final state of the task
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_SUCCESS,
            "progress_message": "Task completed successfully",
            "result": str(retval) if retval is not None else ""
        }
    )

@task_failure.connect
def task_failure_handler(task_id: str, exception: Exception, *args: Any, **kwargs: Any) -> None:
    """
    Handler called when task fails.
    Updates Redis with FAILURE status and error details.
    
    Args:
        task_id: The Celery task ID
        exception: The exception that caused the failure
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_FAILURE,
            "progress_message": "Task failed",
            "result": "",
            "error": str(exception)
        }
    )

def update_task_progress(task_id: str, message: str) -> None:
    """
    Update task progress message in Redis while maintaining INPROGRESS status.
    
    Args:
        task_id: The task ID
        message: Progress message describing current subtask
    
    Example:
        update_task_progress(task_id, "Processing user data")
        update_task_progress(task_id, "Generating reports")
        update_task_progress(task_id, "Sending notifications")
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_INPROGRESS,
            "progress_message": message
        }
    )

def mark_task_success(task_id: str, result: Any = None, message: Optional[str] = None) -> None:
    """
    Manually mark a task as SUCCESS.
    
    Args:
        task_id: The task ID
        result: The task result
        message: Optional success message
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_SUCCESS,
            "progress_message": message or "Task completed successfully",
            "result": str(result) if result is not None else ""
        }
    )

def mark_task_failure(task_id: str, error: str, message: Optional[str] = None) -> None:
    """
    Manually mark a task as FAILURE.
    
    Args:
        task_id: The task ID
        error: The error message
        message: Optional failure message
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": TASK_STATUS_FAILURE,
            "progress_message": message or "Task failed",
            "result": "",
            "error": error
        }
    )

def get_task_info(task_id: str) -> Dict[str, Any]:
    """
    Get task information from Redis.
    
    Args:
        task_id: The task ID
        
    Returns:
        Task information including status and progress_message
    """
    task_info = redis_client.hgetall(f"task:{task_id}")
    if not task_info:
        return {
            "status": TASK_STATUS_NOT_FOUND,
            "progress_message": "Task not found"
        }
            
    return task_info