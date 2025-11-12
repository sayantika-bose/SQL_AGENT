"""
API endpoints for document search operations
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from indexer.src.services.indexer_service import get_indexer_service
from indexer.src.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    ChunkResponse, AccessLevel
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


def get_indexer_service_dependency():
    """Dependency to get indexer service"""
    return get_indexer_service()


@router.post("/", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Search for documents based on query text and access level
    
    This endpoint performs semantic search across indexed documents,
    respecting access level restrictions.
    """
    try:
        response = indexer_service.search_documents(request)
        
        if response.success:
            logger.info(f"Search completed: query='{request.query}', results={response.total_count}")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/", response_model=SearchResponse)
async def search_documents_get(
    query: str = Query(..., min_length=1, max_length=1000, description="Search query text"),
    access_level: AccessLevel = Query(default=AccessLevel.USER, description="User's access level"),
    max_results: int = Query(default=10, ge=1, le=50, description="Maximum number of results"),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Search for documents using GET method (alternative to POST)
    
    This endpoint provides the same search functionality as the POST endpoint
    but uses query parameters for simpler integration.
    """
    try:
        request = SearchRequest(
            query=query,
            access_level=access_level,
            max_results=max_results
        )
        
        response = indexer_service.search_documents(request)
        
        if response.success:
            logger.info(f"Search completed: query='{query}', results={response.total_count}")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/chunk/{chunk_id}", response_model=ChunkResponse)
async def get_chunk_by_id(
    chunk_id: str,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Get a specific document chunk by its ID
    
    This endpoint retrieves the full content and metadata for a specific chunk.
    """
    try:
        result = indexer_service.get_chunk_by_id(chunk_id)
        
        if result["success"]:
            return ChunkResponse(
                success=True,
                chunk_id=result["chunk_id"],
                content=result["content"],
                metadata=result["metadata"]
            )
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chunk error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get chunk failed: {str(e)}")


@router.get("/similar/{chunk_id}")
async def find_similar_chunks(
    chunk_id: str,
    access_level: AccessLevel = Query(default=AccessLevel.USER),
    max_results: int = Query(default=5, ge=1, le=20),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Find chunks similar to a given chunk
    
    This endpoint uses the content of an existing chunk to find similar chunks
    in the same access level.
    """
    try:
        # First get the chunk content
        chunk_result = indexer_service.get_chunk_by_id(chunk_id)
        
        if not chunk_result["success"]:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Use the chunk content as search query
        search_request = SearchRequest(
            query=chunk_result["content"],
            access_level=access_level,
            max_results=max_results + 1  # +1 to account for the original chunk
        )
        
        response = indexer_service.search_documents(search_request)
        
        if not response.success:
            raise HTTPException(status_code=500, detail=response.error)
        
        # Filter out the original chunk from results
        similar_chunks = [
            result for result in response.results 
            if result.chunk_id != chunk_id
        ][:max_results]
        
        return {
            "success": True,
            "original_chunk_id": chunk_id,
            "similar_chunks": similar_chunks,
            "total_count": len(similar_chunks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Find similar chunks error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Find similar chunks failed: {str(e)}")


@router.get("/context/{chunk_id}")
async def get_chunk_context(
    chunk_id: str,
    context_size: int = Query(default=2, ge=1, le=5, description="Number of chunks before and after"),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Get contextual chunks around a specific chunk
    
    This endpoint retrieves chunks that appear before and after the specified chunk
    in the original document, providing context for better understanding.
    """
    try:
        # Get the target chunk
        chunk_result = indexer_service.get_chunk_by_id(chunk_id)
        
        if not chunk_result["success"]:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        chunk_metadata = chunk_result["metadata"]
        filename = chunk_metadata.get("filename")
        chunk_index = chunk_metadata.get("chunk_index", 0)
        access_level = chunk_metadata.get("access_level", "user")
        
        if not filename:
            raise HTTPException(status_code=400, detail="Chunk metadata missing filename")
        
        # Search for chunks from the same file with nearby indices
        search_request = SearchRequest(
            query="*",  # This won't work with semantic search, we need a different approach
            access_level=AccessLevel(access_level),
            max_results=50,  # Get more results to filter
            filters={"filename": filename}
        )
        
        # Note: This is a simplified implementation. In a production system,
        # you might want to add a specific method to get chunks by filename and index range
        
        return {
            "success": True,
            "message": "Context retrieval not fully implemented - requires additional vector DB methods",
            "chunk_id": chunk_id,
            "filename": filename,
            "chunk_index": chunk_index,
            "suggestion": "Consider implementing a method to query chunks by filename and index range"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chunk context error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get chunk context failed: {str(e)}")