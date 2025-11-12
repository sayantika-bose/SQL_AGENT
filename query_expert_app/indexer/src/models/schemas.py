"""
Pydantic models for the Indexer service API
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file types"""
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    MD = "md"


class AccessLevel(str, Enum):
    """Access levels for documents"""
    ADMINISTRATOR = "administrator"
    USER = "user"
    GUEST = "guest"


# Request Models
class IndexingRequest(BaseModel):
    """Request model for document indexing"""
    filename: str = Field(..., description="Name of the file to index")
    access_level: AccessLevel = Field(default=AccessLevel.USER, description="Access level for the document")
    chunk_size: Optional[int] = Field(default=None, description="Custom chunk size")
    chunk_overlap: Optional[int] = Field(default=None, description="Custom chunk overlap")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str = Field(..., description="Search query text")
    access_level: AccessLevel = Field(..., description="User's access level")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional search filters")


class DeleteRequest(BaseModel):
    """Request model for document deletion"""
    filename: Optional[str] = Field(default=None, description="Filename to delete all chunks from")
    chunk_ids: Optional[List[str]] = Field(default=None, description="Specific chunk IDs to delete")


class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    access_level: AccessLevel = Field(default=AccessLevel.USER, description="Access level for the document")
    chunk_size: Optional[int] = Field(default=None, description="Custom chunk size")
    chunk_overlap: Optional[int] = Field(default=None, description="Custom chunk overlap")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# Response Models
class DocumentMetadata(BaseModel):
    """Document metadata model"""
    filename: str
    file_type: FileType
    access_level: AccessLevel
    file_size: int
    uploaded_at: datetime
    total_chunks: int
    chunk_size: int
    chunk_overlap: int
    custom_metadata: Optional[Dict[str, Any]] = None


class ChunkMetadata(BaseModel):
    """Chunk metadata model"""
    chunk_id: str
    filename: str
    file_type: FileType
    access_level: AccessLevel
    chunk_index: int
    chunk_size: int
    start_char: int
    end_char: int
    created_at: datetime


class DocumentChunk(BaseModel):
    """Document chunk model"""
    chunk_id: str
    content: str
    metadata: ChunkMetadata


class SearchResult(BaseModel):
    """Search result model"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk content")
    metadata: Dict[str, Any] = Field(..., description="Chunk metadata")
    similarity_score: float = Field(..., description="Similarity score (0-1)")


class IndexingResponse(BaseModel):
    """Response model for document indexing"""
    success: bool = Field(..., description="Whether the operation was successful")
    filename: str = Field(..., description="Name of the processed file")
    chunks_created: Optional[int] = Field(default=None, description="Number of chunks created")
    document_metadata: Optional[DocumentMetadata] = Field(default=None, description="Document metadata")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SearchResponse(BaseModel):
    """Response model for document search"""
    success: bool = Field(..., description="Whether the search was successful")
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(default=[], description="Search results")
    total_count: int = Field(..., description="Total number of results")
    access_level: AccessLevel = Field(..., description="Access level used for search")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ChunkResponse(BaseModel):
    """Response model for chunk retrieval"""
    success: bool = Field(..., description="Whether the operation was successful")
    chunk_id: str = Field(..., description="Chunk identifier")
    content: Optional[str] = Field(default=None, description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Chunk metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class DeleteResponse(BaseModel):
    """Response model for document deletion"""
    success: bool = Field(..., description="Whether the deletion was successful")
    deleted_count: Optional[int] = Field(default=None, description="Number of items deleted")
    filename: Optional[str] = Field(default=None, description="Filename that was deleted")
    chunk_ids: Optional[List[str]] = Field(default=None, description="Chunk IDs that were deleted")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class FileListResponse(BaseModel):
    """Response model for file listing"""
    success: bool = Field(..., description="Whether the operation was successful")
    files: List[str] = Field(default=[], description="List of indexed filenames")
    total_count: int = Field(..., description="Total number of files")
    access_level: Optional[AccessLevel] = Field(default=None, description="Access level filter used")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class CollectionStatsResponse(BaseModel):
    """Response model for collection statistics"""
    success: bool = Field(..., description="Whether the operation was successful")
    total_chunks: int = Field(..., description="Total number of chunks in collection")
    total_files: Optional[int] = Field(default=None, description="Total number of files")
    collection_name: str = Field(..., description="Name of the collection/index")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Overall service status")
    version: str = Field(..., description="Service version")
    database_status: str = Field(..., description="Database connection status")
    total_chunks: int = Field(..., description="Total chunks in database")
    embedding_model: str = Field(..., description="Embedding model being used")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional health details")


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    code: Optional[str] = Field(default=None, description="Error code")


class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: str = Field(..., description="Error message")
    validation_errors: List[Dict[str, Any]] = Field(..., description="Validation error details")