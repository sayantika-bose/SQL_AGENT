"""
Redis service for interacting with Redis.
"""
import redis
from typing import Dict, Any

from common.config.config_manager import get_config_manager

# Get configuration
config_manager = get_config_manager()
redis_config = config_manager.common_config.redis

# Create Redis client
redis_client = redis.Redis(
    host=redis_config.host,
    port=redis_config.port,
    db=redis_config.db,
    password=redis_config.password,
    decode_responses=True,
    ssl=redis_config.ssl
)

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

def get_redis_client():
    return redis_client