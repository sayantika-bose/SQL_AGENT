"""
FastAPI application with endpoints to interact with the Celery worker through Redis.
Uses a modular structure with models, routers, and services.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from api.src.routers.task_router import base_router
from common.config.config_manager import get_config_manager

# Get configuration
config_manager = get_config_manager()
common_config = config_manager.common_config

# Create FastAPI app
app = FastAPI(
    title=f"{common_config.app_name} API",
    description="API for log root cause analysis using Celery workers with Redis",
    version="0.1.0",
    debug=common_config.debug
)

# Configure CORS - restrict in production environments
origins = ["*"] if common_config.environment == "development" else ["https://app.example.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Log RCA API is running"}

# Include routers
app.include_router(base_router, prefix="/api")