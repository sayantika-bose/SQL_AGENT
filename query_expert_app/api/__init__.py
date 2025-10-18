"""
API package for FastAPI implementation.
This package can be imported and extended by other applications.
"""
from .app import app
from .services.task_service import send_task_to_celery
from .routers.task_router import get_task_status
from .services.redis_service import get_redis_client

# Export key components for easy importing
__all__ = [
    'app',
    'send_task_to_celery',
    'get_task_status',
    'get_redis_client'
]