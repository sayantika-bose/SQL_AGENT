"""
Router for table data endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import logging

from data_api.src.core.database import get_db, DatabaseConnection
from data_api.src.services.query_service import QueryService
from data_api.src.models.schemas import TableDataResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_query_service(db: DatabaseConnection = Depends(get_db)) -> QueryService:
    """Dependency to get query service"""
    return QueryService(db)


@router.get("/{table_name}", response_model=TableDataResponse, tags=["Table"])
async def get_table_data(
    table_name: str,
    limit: int = Query(100, ge=1, le=10000, description="Maximum number of rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    columns: Optional[str] = Query(None, description="Comma-separated list of columns to select"),
    service: QueryService = Depends(get_query_service)
):
    """
    Get data from a specific table with pagination.
    
    - **table_name**: Name of the table
    - **limit**: Maximum number of rows (1-10000, default: 100)
    - **offset**: Number of rows to skip (default: 0)
    - **columns**: Comma-separated column names (optional, default: all columns)
    
    Returns paginated table data.
    """
    try:
        # Parse columns if provided
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
        
        result = service.get_table_data(
            table_name=table_name,
            limit=limit,
            offset=offset,
            columns=column_list
        )
        
        return TableDataResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Invalid request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Failed to get table data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{table_name}/search", tags=["Table"])
async def search_table(
    table_name: str,
    column: str = Query(..., description="Column to search in"),
    value: str = Query(..., description="Value to search for"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum number of rows"),
    service: QueryService = Depends(get_query_service)
):
    """
    Search for records in a table.
    
    - **table_name**: Name of the table
    - **column**: Column to search in
    - **value**: Value to search for
    - **limit**: Maximum number of rows (1-10000, default: 100)
    
    Returns matching records.
    """
    try:
        result = service.search_table(
            table_name=table_name,
            search_column=column,
            search_value=value,
            limit=limit
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid search request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{table_name}/count", tags=["Table"])
async def get_table_count(
    table_name: str,
    db: DatabaseConnection = Depends(get_db)
):
    """
    Get the total number of rows in a table.
    
    - **table_name**: Name of the table
    
    Returns the row count.
    """
    try:
        from data_api.src.utils.validators import QueryValidator
        
        validator = QueryValidator()
        safe_table_name = validator.sanitize_table_name(table_name)
        
        if not db.table_exists(safe_table_name):
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist")
        
        count = db.get_row_count(safe_table_name)
        
        return {
            "success": True,
            "table_name": table_name,
            "count": count
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Failed to get table count: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))