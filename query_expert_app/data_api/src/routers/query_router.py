
"""
Router for query endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from data_api.src.core.database import get_db, DatabaseConnection
from data_api.src.services.query_service import QueryService
from data_api.src.models.schemas import QueryRequest, QueryResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_query_service(db: DatabaseConnection = Depends(get_db)) -> QueryService:
    """Dependency to get query service"""
    return QueryService(db)


@router.post("/execute", response_model=QueryResponse, tags=["Query"])
async def execute_query(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service)
):
    """
    Execute a SELECT query on the database.
    
    - **query**: SQL SELECT query to execute
    - **params**: Optional list of query parameters
    
    Returns query results or error message.
    
    **Note**: Only SELECT queries are allowed. Any INSERT, UPDATE, DELETE, or other
    modification queries will be rejected.
    """
    try:
        result = service.execute_select_query(request.query, request.params)
        return QueryResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Query validation error: {str(e)}")
        return QueryResponse(
            success=False,
            error=str(e)
        )
        
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        return QueryResponse(
            success=False,
            error=f"Query execution failed: {str(e)}"
        )


@router.post("/validate", tags=["Query"])
async def validate_query(request: QueryRequest):
    """
    Validate a query without executing it.
    
    - **query**: SQL query to validate
    
    Returns validation result.
    """
    try:
        from data_api.src.utils.validators import QueryValidator, QuerySanitizer
        
        validator = QueryValidator()
        sanitizer = QuerySanitizer()
        
        # Sanitize query
        sanitized_query = sanitizer.sanitize_query(request.query)
        
        # Validate query
        is_valid, error_message = validator.validate_query(sanitized_query)
        
        if is_valid:
            return {
                "success": True,
                "message": "Query is valid",
                "sanitized_query": sanitized_query
            }
        else:
            return {
                "success": False,
                "error": error_message
            }
            
    except Exception as e:
        logger.error(f"Query validation error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }