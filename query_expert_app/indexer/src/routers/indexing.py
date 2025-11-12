"""
API endpoints for document indexing operations
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import aiofiles
from pathlib import Path

from indexer.src.services.indexer_service import get_indexer_service
from indexer.src.core.config import get_settings
from indexer.src.models.schemas import (
    IndexingRequest, IndexingResponse,
    DocumentUploadRequest, AccessLevel
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/indexing", tags=["indexing"])


def get_settings_dependency():
    """Dependency to get settings"""
    return get_settings()


def get_indexer_service_dependency():
    """Dependency to get indexer service"""
    return get_indexer_service()


@router.post("/upload", response_model=IndexingResponse)
async def upload_and_index_document(
    file: UploadFile = File(...),
    access_level: AccessLevel = Form(default=AccessLevel.USER),
    chunk_size: Optional[int] = Form(default=None),
    chunk_overlap: Optional[int] = Form(default=None),
    settings = Depends(get_settings_dependency),
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Upload and index a document
    
    This endpoint handles file upload and immediately processes it for indexing.
    The document will be chunked and embedded into the vector database.
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower().lstrip('.')
        if file_extension not in settings.allowed_extensions_list:
            allowed = ", ".join(settings.allowed_extensions_list)
            raise HTTPException(
                status_code=400, 
                detail=f"File type '{file_extension}' not allowed. Supported types: {allowed}"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.max_file_size_bytes:
            max_mb = settings.max_file_size_mb
            raise HTTPException(
                status_code=413, 
                detail=f"File size exceeds maximum allowed size of {max_mb}MB"
            )
        
        # Save uploaded file
        upload_dir = Path(settings.upload_directory)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"File uploaded: {file.filename} ({file_size} bytes)")
        
        # Create indexing request
        indexing_request = IndexingRequest(
            filename=file.filename,
            access_level=access_level,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Process and index the document
        response = indexer_service.index_document(indexing_request)
        
        if response.success:
            logger.info(f"Document indexed successfully: {file.filename}")
            return response
        else:
            # Clean up uploaded file if indexing failed
            try:
                file_path.unlink()
            except:
                pass
            
            # Determine appropriate HTTP status code based on error type
            error_message = response.error.lower()
            
            if any(phrase in error_message for phrase in [
                "no content could be extracted",
                "contains only images",
                "scanned content",
                "failed to create document chunks",
                "too short",
                "only whitespace"
            ]):
                # This is a client error - the file format is not suitable for text extraction
                raise HTTPException(
                    status_code=422, 
                    detail=f"Document processing failed: {response.error}. "
                           f"This file may contain only images, be password-protected, or have no extractable text. "
                           f"Please try uploading a text-based PDF or a different file format."
                )
            else:
                # This is a server error - something went wrong with processing
                raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload and index error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload and index failed: {str(e)}")


@router.post("/index", response_model=IndexingResponse)
async def index_existing_document(
    request: IndexingRequest,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Index an existing uploaded document
    
    This endpoint processes a previously uploaded document for indexing.
    The file must already exist in the upload directory.
    """
    try:
        response = indexer_service.index_document(request)
        
        if response.success:
            logger.info(f"Document indexed: {request.filename}")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.post("/reindex", response_model=IndexingResponse)
async def reindex_document(
    request: IndexingRequest,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Reindex an existing document
    
    This endpoint deletes existing chunks for a document and reprocesses it.
    Useful for updating documents with new chunking parameters or access levels.
    """
    try:
        # First delete existing chunks for this file
        from indexer.src.models.schemas import DeleteRequest
        delete_request = DeleteRequest(filename=request.filename)
        delete_response = indexer_service.delete_documents(delete_request)
        
        if delete_response.success:
            logger.info(f"Existing chunks deleted for reindexing: {request.filename}")
        
        # Then reindex the document
        response = indexer_service.index_document(request)
        
        if response.success:
            logger.info(f"Document reindexed: {request.filename}")
            return response
        else:
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindex document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


@router.get("/status/{filename}")
async def get_indexing_status(
    filename: str,
    indexer_service = Depends(get_indexer_service_dependency)
):
    """
    Get indexing status for a specific file
    
    Returns information about whether a file has been indexed and chunk count.
    """
    try:
        # Check if file exists in the collection
        files_response = indexer_service.list_files()
        
        if not files_response.success:
            raise HTTPException(status_code=500, detail=files_response.error)
        
        is_indexed = filename in files_response.files
        
        chunk_count = 0
        if is_indexed:
            # Get exact chunk count for this file
            from indexer.src.core.vector_db import get_vector_db
            vector_db = get_vector_db()
            chunk_count = vector_db.get_chunk_count_by_filename(filename)
        
        return {
            "filename": filename,
            "is_indexed": is_indexed,
            "chunk_count": chunk_count,
            "status": "indexed" if is_indexed else "not_indexed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get indexing status error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")