"""
Main entry point for the Celery worker.
"""
import os
import sys
import importlib
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())

from common.config.config_manager import get_config_manager


# Get configuration
config_manager = get_config_manager()
from worker.src.core.celery_app import celery_app


# Import task modules to register them with Celery
# This approach avoids Windows permission issues with the include parameter
from  worker.src.agents.master_agent import process_user_question

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