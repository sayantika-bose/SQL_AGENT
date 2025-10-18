"""
Main entry point for the Celery worker.
"""
import os
import sys
import importlib
from .core.celery_app import celery_app

# Import task modules to register them with Celery
# This approach avoids Windows permission issues with the include parameter
from  .tasks.tasks import long_running_task

if __name__ == "__main__":
    # Add arguments for Celery worker
    argv = [
        'worker',
        '--loglevel=INFO',
        '--concurrency=1',
        '--pool=solo',
    ]
    
    # Start the Celery worker process
    celery_app.worker_main(argv)