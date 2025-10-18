"""
Task service for handling Celery task operations.
"""
import json
from typing import Dict, Any, Optional, List, Union
from celery import Celery

from common.config.config_manager import get_config_manager

# Get configuration
config_manager = get_config_manager()
worker_config = config_manager.worker_config

# Use the broker URL from worker config
REDIS_URL = worker_config.celery.broker_url

def send_task_to_celery(task_name: str, args=None, kwargs=None) -> str:
    """
    Send a task to Celery through Redis.
    
    This function creates a temporary Celery app to send tasks without
    directly importing the worker module, maintaining decoupling.
    
    Args:
        task_name: The full task name (e.g., "worker.tasks.process_logs")
        args: Positional arguments for the task
        kwargs: Keyword arguments for the task
        
    Returns:
        The task ID
    """
    # Create a temporary Celery app just for sending tasks
    temp_app = Celery(
        'api',
        broker=REDIS_URL,
        backend=REDIS_URL
    )
    
    # Send the task
    task = temp_app.send_task(
        task_name,
        args=args or [],
        kwargs=kwargs or {}
    )
    
    return task.id

def parse_task_result(result: Optional[str]) -> Any:
    """
    Parse task result from string to appropriate format.
    
    Args:
        result: String result from Redis
        
    Returns:
        Parsed result (dict, list, or original string)
    """
    if not result:
        return None
        
    if isinstance(result, str):
        try:
            # Try to parse as JSON
            return json.loads(result)
        except json.JSONDecodeError:
            # Keep as string if not valid JSON
            return result
    
    return result