"""
Worker package for log root cause analysis.
This package can be imported and extended by other applications.
"""
from .core.celery_app import celery_app, update_task_progress
# Tasks are defined in worker/tasks.py but should be imported directly from there
# This avoids circular imports with the tasks package
from .extension import register_task, WorkerExtension

# Export key components for easy importing
__all__ = [
    'celery_app',
    'update_task_progress',
    'register_task',
    'WorkerExtension'
]