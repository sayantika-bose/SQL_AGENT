"""
Main entry point for the FastAPI application.
"""
import uvicorn
import os
from api.src.app import app

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the FastAPI app with Uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Enable auto-reload for development
    )