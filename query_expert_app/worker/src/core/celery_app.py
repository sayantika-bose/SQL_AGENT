"""
Celery application configuration with Redis broker.
Completely decoupled from API components.
"""
from celery import Celery
from celery.signals import task_prerun, task_postrun
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

# Task progress tracking with Redis
@task_prerun.connect
def task_prerun_handler(task_id: str, task: Any, *args: Any, **kwargs: Any) -> None:
    """
    Handler called before task execution.
    Updates Redis with task status.
    
    Args:
        task_id: The Celery task ID
        task: The task instance
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": "STARTED",
            "progress": 0,
            "result": ""  # Empty string instead of None
        }
    )
    # Set expiration to avoid Redis memory issues (24 hours)
    redis_client.expire(f"task:{task_id}", 86400)

@task_postrun.connect
def task_postrun_handler(task_id: str, task: Any, retval: Any, state: str, *args: Any, **kwargs: Any) -> None:
    """
    Handler called after task execution.
    Updates Redis with task completion status and result.
    
    Args:
        task_id: The Celery task ID
        task: The task instance
        retval: The return value of the task
        state: The final state of the task
    """
    redis_client.hset(
        f"task:{task_id}",
        mapping={
            "status": state,
            "progress": 100,
            "result": str(retval) if retval is not None else None
        }
    )

def update_task_progress(task_id: str, progress: int, message: Optional[str] = None) -> None:
    """
    Update task progress in Redis.
    
    Args:
        task_id: The task ID
        progress: Progress percentage (0-100)
        message: Optional status message
    """
    update_data: Dict[str, Union[int, str]] = {
        "progress": progress
    }
    if message:
        update_data["message"] = message
    
    redis_client.hset(f"task:{task_id}", mapping=update_data)

def get_task_info(task_id: str) -> Dict[str, Any]:
    """
    Get task information from Redis.
    
    Args:
        task_id: The task ID
        
    Returns:
        Task information including status and progress
    """
    task_info = redis_client.hgetall(f"task:{task_id}")
    if not task_info:
        return {"status": "NOT_FOUND", "progress": 0}
    
    # Convert progress to int if it exists
    if "progress" in task_info:
        try:
            task_info["progress"] = int(task_info["progress"])
        except (ValueError, TypeError):
            pass
            
    return task_info