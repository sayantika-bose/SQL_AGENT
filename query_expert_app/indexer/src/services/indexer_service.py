"""
Indexer service for managing document indexing and search operations
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from indexer.src.core.vector_db import get_vector_db
from indexer.src.services.document_processor import get_document_processor
from indexer.src.models.schemas import (
    SearchRequest, SearchResponse, SearchResult,
    IndexingRequest, IndexingResponse,
    DeleteRequest, DeleteResponse,
    FileListResponse, CollectionStatsResponse,
    AccessLevel
)

logger = logging.getLogger(__name__)


class IndexerService:
    """Service for document indexing and search operations"""
    
    def __init__(self):
        """Initialize indexer service"""
        self.vector_db = get_vector_db()
        self.document_processor = get_document_processor()
    
    def index_document(self, request: IndexingRequest) -> IndexingResponse:
        """
        Index a document by processing it into chunks and embeddings
        
        Args:
            request: Indexing request with document details
            
        Returns:
            Indexing response with results
        """
        try:
            logger.info(f"Starting document indexing: {request.filename}")
            
            # Process the document
            result = self.document_processor.process_document(
                filename=request.filename,
                access_level=request.access_level,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                custom_metadata=request.metadata
            )
            
            if result["success"]:
                return IndexingResponse(
                    success=True,
                    filename=result["filename"],
                    chunks_created=result["chunks_created"],
                    document_metadata=result["document_metadata"],
                    processing_time=result["processing_time"]
                )
            else:
                return IndexingResponse(
                    success=False,
                    filename=request.filename,
                    error=result["error"]
                )
                
        except Exception as e:
            logger.error(f"Indexing service error for {request.filename}: {str(e)}")
            return IndexingResponse(
                success=False,
                filename=request.filename,
                error=f"Indexing service error: {str(e)}"
            )
    
    def search_documents(self, request: SearchRequest) -> SearchResponse:
        """
        Search for documents based on query and access level
        
        Args:
            request: Search request with query and filters
            
        Returns:
            Search response with results
        """
        try:
            logger.info(f"Searching documents: query='{request.query}', access_level={request.access_level}")
            
            # Perform vector search with access control
            search_result = self.vector_db.search_chunks(
                query_text=request.query,
                access_level=request.access_level.value,
                n_results=request.max_results,
                where_filters=request.filters
            )
            
            if not search_result["success"]:
                return SearchResponse(
                    success=False,
                    query=request.query,
                    access_level=request.access_level,
                    total_count=0,
                    error=search_result["error"]
                )
            
            # Process search results
            results = []
            if search_result["results"] and search_result["results"]["ids"]:
                ids = search_result["results"]["ids"][0]
                documents = search_result["results"]["documents"][0]
                metadatas = search_result["results"]["metadatas"][0]
                distances = search_result["results"]["distances"][0]
                
                for i, chunk_id in enumerate(ids):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 / (1.0 + distances[i])
                    
                    result = SearchResult(
                        chunk_id=chunk_id,
                        content=documents[i],
                        metadata=metadatas[i],
                        similarity_score=similarity_score
                    )
                    results.append(result)
            
            return SearchResponse(
                success=True,
                query=request.query,
                results=results,
                total_count=len(results),
                access_level=request.access_level
            )
            
        except Exception as e:
            logger.error(f"Search service error: {str(e)}")
            return SearchResponse(
                success=False,
                query=request.query,
                access_level=request.access_level,
                total_count=0,
                error=f"Search service error: {str(e)}"
            )
    
    def get_chunk_by_id(self, chunk_id: str) -> Dict[str, Any]:
        """
        Get a specific chunk by its ID
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            Chunk data or error response
        """
        try:
            chunk_data = self.vector_db.get_chunk_by_id(chunk_id)
            
            if chunk_data:
                return {
                    "success": True,
                    "chunk_id": chunk_data["id"],
                    "content": chunk_data["document"],
                    "metadata": chunk_data["metadata"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Chunk not found: {chunk_id}"
                }
                
        except Exception as e:
            logger.error(f"Error retrieving chunk {chunk_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Error retrieving chunk: {str(e)}"
            }
    
    def delete_documents(self, request: DeleteRequest) -> DeleteResponse:
        """
        Delete documents or specific chunks
        
        Args:
            request: Delete request specifying what to delete
            
        Returns:
            Delete response with results
        """
        try:
            if request.filename:
                # Delete all chunks from a specific file
                success = self.vector_db.delete_by_filename(request.filename)
                if success:
                    return DeleteResponse(
                        success=True,
                        deleted_count=1,  # We don't know exact chunk count
                        filename=request.filename
                    )
                else:
                    return DeleteResponse(
                        success=False,
                        error=f"Failed to delete chunks from file: {request.filename}"
                    )
                    
            elif request.chunk_ids:
                # Delete specific chunks by ID
                success = self.vector_db.delete_chunks(request.chunk_ids)
                if success:
                    return DeleteResponse(
                        success=True,
                        deleted_count=len(request.chunk_ids),
                        chunk_ids=request.chunk_ids
                    )
                else:
                    return DeleteResponse(
                        success=False,
                        error="Failed to delete specified chunks"
                    )
            else:
                return DeleteResponse(
                    success=False,
                    error="Either filename or chunk_ids must be provided"
                )
                
        except Exception as e:
            logger.error(f"Delete service error: {str(e)}")
            return DeleteResponse(
                success=False,
                error=f"Delete service error: {str(e)}"
            )
    
    def list_files(self, access_level: Optional[AccessLevel] = None) -> FileListResponse:
        """
        List all indexed files, optionally filtered by access level
        
        Args:
            access_level: Optional access level filter
            
        Returns:
            File list response
        """
        try:
            access_level_str = access_level.value if access_level else None
            files = self.vector_db.list_files(access_level_str)
            
            return FileListResponse(
                success=True,
                files=files,
                total_count=len(files),
                access_level=access_level
            )
            
        except Exception as e:
            logger.error(f"List files service error: {str(e)}")
            return FileListResponse(
                success=False,
                total_count=0,
                error=f"List files service error: {str(e)}"
            )
    
    def get_collection_stats(self) -> CollectionStatsResponse:
        """
        Get statistics about the document collection
        
        Returns:
            Collection statistics response
        """
        try:
            stats = self.vector_db.get_collection_stats()
            
            if not stats["success"]:
                return CollectionStatsResponse(
                    success=False,
                    collection_name="unknown",
                    error=stats["error"]
                )
            
            # Get file count
            all_files = self.vector_db.list_files()
            
            # TODO: Implement access level counts if needed
            # This would require querying the collection for each access level
            
            return CollectionStatsResponse(
                success=True,
                total_chunks=stats["total_chunks"],
                collection_name=stats["collection_name"],
                total_files=len(all_files)
            )
            
        except Exception as e:
            logger.error(f"Collection stats service error: {str(e)}")
            return CollectionStatsResponse(
                success=False,
                collection_name="unknown",
                error=f"Collection stats service error: {str(e)}"
            )


# Global service instance
_service_instance: Optional[IndexerService] = None


def get_indexer_service() -> IndexerService:
    """
    Get indexer service instance (singleton)
    
    Returns:
        IndexerService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = IndexerService()
        logger.info("Indexer service initialized")
    return _service_instance