"""
FastAPI Data API for SQLite database operations.
Main application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv,find_dotenv
load_dotenv(find_dotenv())


from data_api.src.core.config import get_settings
from data_api.src.core.database import init_db
from data_api.src.routers import query_router, schema_router, table_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    logger.info("Starting Data API...")
    settings = get_settings()
    init_db()
    logger.info(f"Database initialized at: {settings.database_path}")
    yield
    # Shutdown
    logger.info("Shutting down Data API...")


# Create FastAPI app
app = FastAPI(
    title="SQL Agent Data API",
    description="API for executing read-only SQL queries on SQLite database",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router.router, prefix="/api/query", tags=["Query"])
app.include_router(schema_router.router, prefix="/api/schema", tags=["Schema"])
app.include_router(table_router.router, prefix="/api/table", tags=["Table"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "SQL Agent Data API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "data-api"}


