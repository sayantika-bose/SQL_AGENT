"""
Router for schema endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from data_api.src.core.database import get_db, DatabaseConnection
from data_api.src.services.schema_service import SchemaService
from data_api.src.models.schemas import SchemaResponse, TableListResponse, TableInfoResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def get_schema_service(db: DatabaseConnection = Depends(get_db)) -> SchemaService:
    """Dependency to get schema service"""
    return SchemaService(db)


@router.get("/", response_model=SchemaResponse, tags=["Schema"])
async def get_database_schema(service: SchemaService = Depends(get_schema_service)):
    """
    Get the complete database schema for all tables.
    
    Returns information about all tables and their columns including:
    - Column names
    - Data types
    - Constraints (NOT NULL, PRIMARY KEY)
    - Default values
    """
    try:
        schemas = service.get_all_schemas()
        
        # Convert to response format
        from data_api.src.models.schemas import TableSchema
        formatted_schemas = {}
        for table_name, columns in schemas.items():
            formatted_schemas[table_name] = [
                TableSchema(**col) for col in columns
            ]
        
        return SchemaResponse(
            success=True,
            tables=formatted_schemas
        )
        
    except Exception as e:
        logger.error(f"Failed to get schema: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=TableListResponse, tags=["Schema"])
async def list_tables(service: SchemaService = Depends(get_schema_service)):
    """
    Get a list of all tables in the database.
    
    Returns a list of table names.
    """
    try:
        tables = service.get_all_tables()
        
        return TableListResponse(
            success=True,
            tables=tables,
            count=len(tables)
        )
        
    except Exception as e:
        logger.error(f"Failed to list tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/{table_name}", response_model=TableInfoResponse, tags=["Schema"])
async def get_table_info(
    table_name: str,
    service: SchemaService = Depends(get_schema_service)
):
    """
    Get detailed information about a specific table.
    
    - **table_name**: Name of the table
    
    Returns:
    - Table schema (columns, types, constraints)
    - Row count
    - Column count
    """
    try:
        from data_api.src.models.schemas import TableSchema
        
        table_info = service.get_table_info(table_name)
        
        # Format response
        return TableInfoResponse(
            success=True,
            table_name=table_info["table_name"],
            columns=[TableSchema(**col) for col in table_info["columns"]],
            row_count=table_info["row_count"]
        )
        
    except ValueError as e:
        logger.warning(f"Table not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except Exception as e:
        logger.error(f"Failed to get table info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))