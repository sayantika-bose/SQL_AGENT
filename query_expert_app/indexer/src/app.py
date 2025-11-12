"""
Main FastAPI application for the Indexer service
"""
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from indexer.src.core.config import get_settings
from indexer.src.core.vector_db import init_vector_db
from indexer.src.routers import indexing, search, management

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting Indexer service...")
    
    try:
        # Log configuration first
        settings = get_settings()
        logger.info(f"Service configuration:")
        logger.info(f"  - Host: {settings.indexer_host}:{settings.indexer_port}")
        logger.info(f"  - Environment: {settings.environment}")
        logger.info(f"  - OpenSearch URL: {settings.opensearch_url}")
        logger.info(f"  - OpenSearch index: {settings.opensearch_index}")
        logger.info(f"  - Ollama URL: {settings.ollama_base_url}")
        logger.info(f"  - Ollama model: {settings.ollama_model}")
        logger.info(f"  - Chunk size: {settings.chunk_size}")
        logger.info(f"  - Max file size: {settings.max_file_size_mb}MB")
        logger.info(f"  - Allowed extensions: {', '.join(settings.allowed_extensions_list)}")
        
        # Try to initialize vector database connection
        try:
            init_vector_db()
            logger.info("✅ Vector database initialized successfully")
        except Exception as db_error:
            logger.warning(f"⚠️  Vector database initialization failed: {str(db_error)}")
            logger.warning("⚠️  Service will start in limited mode. Some features may not work.")
            logger.warning("⚠️  Please ensure OpenSearch is running on the configured URL.")
        
        logger.info("🚀 Indexer service startup completed")
        
    except Exception as e:
        logger.error(f"❌ Critical startup error: {str(e)}")
        # Don't raise the exception - let the service start in limited mode
        logger.warning("⚠️  Service starting in limited mode due to initialization errors")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Indexer service...")
    logger.info("Indexer service shutdown completed")


# Create FastAPI application
def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Document Indexer Service",
        description="Microservice for document chunking, embedding, and vector storage with access control",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(indexing.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(management.router, prefix="/api/v1")
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        return {
            "service": "Document Indexer Service",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/management/health"
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler for unhandled errors"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "detail": str(exc) if settings.debug else "Contact administrator"
            }
        )
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    """
    Run the application directly
    
    This is useful for development. In production, use a proper ASGI server.
    """
    settings = get_settings()
    
    uvicorn.run(
        "indexer.src.app:app",
        host=settings.indexer_host,
        port=settings.indexer_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )