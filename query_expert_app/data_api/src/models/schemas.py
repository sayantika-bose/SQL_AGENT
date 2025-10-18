"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    """Request model for executing SQL query"""
    query: str = Field(..., description="SQL SELECT query to execute")
    params: Optional[List[Any]] = Field(None, description="Query parameters")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate that query is a SELECT statement"""
        if not v:
            raise ValueError("Query cannot be empty")
        
        query_stripped = v.strip().upper()
        
        # Only allow SELECT queries
        if not query_stripped.startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 
            'ALTER', 'TRUNCATE', 'REPLACE', 'EXEC', 'EXECUTE'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_stripped:
                raise ValueError(f"Query contains prohibited keyword: {keyword}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "SELECT * FROM users WHERE id = ?",
                "params": [1]
            }
        }


class QueryResponse(BaseModel):
    """Response model for query execution"""
    success: bool = Field(..., description="Whether the query was successful")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query results")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [{"id": 1, "username": "john_doe", "email": "john@example.com"}],
                "row_count": 1
            }
        }


class TableSchema(BaseModel):
    """Schema information for a table column"""
    cid: int = Field(..., description="Column ID")
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column type")
    notnull: int = Field(..., description="NOT NULL constraint (0 or 1)")
    dflt_value: Optional[Any] = Field(None, description="Default value")
    pk: int = Field(..., description="Primary key (0 or 1)")


class SchemaResponse(BaseModel):
    """Response model for database schema"""
    success: bool = Field(..., description="Whether the request was successful")
    tables: Dict[str, List[TableSchema]] = Field(..., description="Table schemas")
    error: Optional[str] = Field(None, description="Error message if failed")


class TableListResponse(BaseModel):
    """Response model for listing tables"""
    success: bool = Field(..., description="Whether the request was successful")
    tables: List[str] = Field(..., description="List of table names")
    count: int = Field(..., description="Number of tables")


class TableDataResponse(BaseModel):
    """Response model for table data"""
    success: bool = Field(..., description="Whether the request was successful")
    table_name: str = Field(..., description="Table name")
    data: List[Dict[str, Any]] = Field(..., description="Table data")
    row_count: int = Field(..., description="Number of rows returned")
    total_rows: Optional[int] = Field(None, description="Total rows in table")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")


class TableInfoResponse(BaseModel):
    """Response model for table information"""
    success: bool = Field(..., description="Whether the request was successful")
    table_name: str = Field(..., description="Table name")
    columns: List[TableSchema] = Field(..., description="Column information")
    row_count: int = Field(..., description="Total number of rows")


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")