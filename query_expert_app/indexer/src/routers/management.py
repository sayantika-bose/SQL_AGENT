"""
API endpoints for document and collection management operations
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from indexer.src.services.indexer_service import get_indexer_service
from indexer.src.models.schemas import (
    DeleteRequest, DeleteResponse,
    FileListResponse, CollectionStatsResponse,
    HealthResponse, AccessLevel
)
from indexer.src.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/management", tags=["management"])


def get_indexer_service_dependency():
    """Dependency to get indexer service"""
    return get_indexer_service()


def get_settings_dependency():
    """Dependency to get settings"""
    return get_settings()


@router.delete("/documents", response_model=DeleteResponse)
async def delete_documents(
    request: DeleteRequest,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Delete documents or specific chunks
    
    This endpoint can delete all chunks from a specific file or delete specific chunks by ID.
    """
    try:
        response = indexer_service.delete_documents(request)
        
        if response.success:
            if request.filename:
                logger.info(f"Deleted all chunks from file: {request.filename}")
            elif request.chunk_ids:
                logger.info(f"Deleted {len(request.chunk_ids)} specific chunks")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete operation failed: {str(e)}")


@router.delete("/documents/{filename}", response_model=DeleteResponse)
async def delete_document_by_filename(
    filename: str,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Delete all chunks from a specific document
    
    This endpoint deletes all chunks associated with the specified filename.
    """
    try:
        request = DeleteRequest(filename=filename)
        response = indexer_service.delete_documents(request)
        
        if response.success:
            logger.info(f"Deleted document: {filename}")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Delete document failed: {str(e)}")


@router.get("/files", response_model=FileListResponse)
async def list_indexed_files(
    access_level: Optional[AccessLevel] = Query(default=None, description="Filter by access level"),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    List all indexed files
    
    This endpoint returns a list of all files that have been indexed,
    optionally filtered by access level.
    """
    try:
        response = indexer_service.list_files(access_level)
        
        if response.success:
            logger.info(f"Listed {response.total_count} files")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"List files failed: {str(e)}")


@router.get("/stats", response_model=CollectionStatsResponse)
async def get_collection_statistics(
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Get collection statistics
    
    This endpoint returns statistics about the document collection,
    including total chunks, files, and other metrics.
    """
    try:
        response = indexer_service.get_collection_stats()
        
        if response.success:
            logger.info(f"Retrieved collection stats: {response.total_chunks} chunks, {response.total_files} files")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get collection stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get collection stats failed: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check(
    indexer_service = Depends(get_indexer_service_dependency),
    settings = Depends(get_settings_dependency)
):
    """
    Health check endpoint
    
    This endpoint provides information about the service status,
    database connectivity, and configuration.
    """
    try:
        # Get collection stats to verify database connectivity
        stats_response = indexer_service.get_collection_stats()
        
        database_status = "healthy" if stats_response.success else "unhealthy"
        total_chunks = stats_response.total_chunks if stats_response.success else 0
        
        # Get vector database health check
        from indexer.src.core.vector_db import get_vector_db
        vector_db = get_vector_db()
        health_info = vector_db.health_check()
        
        return HealthResponse(
            status=health_info.get("status", "unknown"),
            version="0.1.0",
            database_status=health_info.get("opensearch", "unknown"),
            total_chunks=total_chunks,
            embedding_model=settings.ollama_model,
            details=health_info
        )
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            version="0.1.0",
            database_status="error",
            total_chunks=0,
            embedding_model=settings.ollama_model if settings else "unknown",
            details={"error": str(e)}
        )


@router.post("/reset")
async def reset_collection(
    confirm: bool = Query(default=False, description="Confirmation flag to prevent accidental resets"),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Reset the entire collection (DANGEROUS)
    
    This endpoint deletes all documents and chunks from the collection.
    Requires explicit confirmation to prevent accidental data loss.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Collection reset requires confirmation. Set confirm=true to proceed."
        )
    
    try:
        # Get all files first
        files_response = indexer_service.list_files()
        
        if not files_response.success:
            raise HTTPException(status_code=500, detail="Failed to list files for reset")
        
        deleted_count = 0
        errors = []
        
        # Delete each file's chunks
        for filename in files_response.files:
            delete_request = DeleteRequest(filename=filename)
            delete_response = indexer_service.delete_documents(delete_request)
            
            if delete_response.success:
                deleted_count += 1
            else:
                errors.append(f"Failed to delete {filename}: {delete_response.error}")
        
        if errors:
            logger.warning(f"Collection reset completed with errors: {errors}")
            return {
                "success": True,
                "message": f"Collection reset completed with {len(errors)} errors",
                "files_deleted": deleted_count,
                "errors": errors
            }
        else:
            logger.info(f"Collection reset completed successfully: {deleted_count} files deleted")
            return {
                "success": True,
                "message": "Collection reset completed successfully",
                "files_deleted": deleted_count,
                "errors": []
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Collection reset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Collection reset failed: {str(e)}")


@router.get("/access-levels")
async def get_access_levels(
    settings = Depends(get_settings_dependency)
):
    """
    Get available access levels
    
    This endpoint returns the list of valid access levels configured for the system.
    """
    try:
        return {
            "success": True,
            "access_levels": settings.valid_access_levels_list,
            "default_access_level": settings.default_access_level
        }
        
    except Exception as e:
        logger.error(f"Get access levels error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get access levels failed: {str(e)}")


@router.get("/config")
async def get_configuration(
    settings = Depends(get_settings_dependency)
):
    """
    Get service configuration
    
    This endpoint returns the current service configuration (non-sensitive values only).
    """
    try:
        return {
            "success": True,
            "configuration": {
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "max_file_size_mb": settings.max_file_size_mb,
                "allowed_extensions": settings.allowed_extensions_list,
                "ollama_model": settings.ollama_model,
                "opensearch_index": settings.opensearch_index,
                "valid_access_levels": settings.valid_access_levels_list,
                "default_access_level": settings.default_access_level
            }
        }
        
    except Exception as e:
        logger.error(f"Get configuration error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get configuration failed: {str(e)}")