import os
import uvicorn
from data_api.src.app import app
from data_api.src.core.config import get_settings

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "data_api.main:app",
        host=settings.data_api_host,
        port=settings.data_api_port,
        reload=True
    )