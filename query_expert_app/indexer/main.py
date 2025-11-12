#!/usr/bin/env python3
"""
Startup script for the Indexer service
"""

# Import and run the application
from indexer.src.app import app
import uvicorn
import logging
from indexer.src.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()

    # configure logger from settings
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger = logging.getLogger("indexer")

    logger.info(f"Starting Indexer service on {settings.indexer_host}:{settings.indexer_port}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Documentation available at: http://{settings.indexer_host}:{settings.indexer_port}/docs")
    
    if settings.debug:
        # Use import string for reload functionality
        uvicorn.run(
            app,            host=settings.indexer_host,
            port=settings.indexer_port,
        )
    else:
        # Use app object for production
        uvicorn.run(
            app,
            host=settings.indexer_host,
            port=settings.indexer_port,
            reload=False,
            log_level=settings.log_level.lower()
        )