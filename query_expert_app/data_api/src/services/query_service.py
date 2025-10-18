"""
Service layer for query operations
"""
from typing import List, Dict, Any, Optional
import logging

from data_api.src.core.database import DatabaseConnection
from data_api.src.utils.validators import QueryValidator, QuerySanitizer
from data_api.src.core.config import get_settings

logger = logging.getLogger(__name__)


class QueryService:
    """Service for handling database queries"""
    
    def __init__(self, db: DatabaseConnection):
        """
        Initialize query service.
        
        Args:
            db: Database connection instance
        """
        self.db = db
        self.validator = QueryValidator()
        self.sanitizer = QuerySanitizer()
        self.settings = get_settings()
    
    def execute_select_query(
        self,
        query: str,
        params: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a SELECT query with validation.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            Dictionary with query results
            
        Raises:
            ValueError: If query validation fails
        """
        # Sanitize query
        sanitized_query = self.sanitizer.sanitize_query(query)
        
        # Validate query
        is_valid, error_message = self.validator.validate_query(
            sanitized_query,
            max_length=self.settings.max_query_length
        )
        
        if not is_valid:
            logger.warning(f"Query validation failed: {error_message}")
            raise ValueError(error_message)
        
        # Execute query
        try:
            params_tuple = tuple(params) if params else None
            data = self.db.execute_select(
                sanitized_query,
                params_tuple,
                timeout=self.settings.query_timeout
            )
            
            logger.info(f"Query executed successfully, returned {len(data)} rows")
            
            return {
                "success": True,
                "data": data,
                "row_count": len(data)
            }
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def get_table_data(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get data from a specific table.
        
        Args:
            table_name: Name of the table
            limit: Maximum number of rows to return
            offset: Number of rows to skip
            columns: List of columns to select (None for all)
            
        Returns:
            Dictionary with table data
        """
        # Validate limit and offset
        is_valid, error_message = self.validator.validate_limit_offset(limit, offset)
        if not is_valid:
            raise ValueError(error_message)
        
        # Sanitize table name
        safe_table_name = self.validator.sanitize_table_name(table_name)
        
        # Check if table exists
        if not self.db.table_exists(safe_table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Build query
        if columns:
            # Sanitize column names
            safe_columns = [self.validator.sanitize_table_name(col) for col in columns]
            columns_str = ", ".join(safe_columns)
        else:
            columns_str = "*"
        
        query = f"SELECT {columns_str} FROM {safe_table_name} LIMIT ? OFFSET ?"
        
        # Execute query
        data = self.db.execute_select(query, (limit, offset))
        
        # Get total row count
        total_rows = self.db.get_row_count(safe_table_name)
        
        return {
            "success": True,
            "table_name": table_name,
            "data": data,
            "row_count": len(data),
            "total_rows": total_rows,
            "limit": limit,
            "offset": offset
        }
    
    def search_table(
        self,
        table_name: str,
        search_column: str,
        search_value: Any,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Search for records in a table.
        
        Args:
            table_name: Name of the table
            search_column: Column to search in
            search_value: Value to search for
            limit: Maximum number of rows to return
            
        Returns:
            Dictionary with search results
        """
        # Sanitize inputs
        safe_table_name = self.validator.sanitize_table_name(table_name)
        safe_column = self.validator.sanitize_table_name(search_column)
        
        # Check if table exists
        if not self.db.table_exists(safe_table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Build query
        query = f"SELECT * FROM {safe_table_name} WHERE {safe_column} = ? LIMIT ?"
        
        # Execute query
        data = self.db.execute_select(query, (search_value, limit))
        
        return {
            "success": True,
            "table_name": table_name,
            "search_column": search_column,
            "search_value": search_value,
            "data": data,
            "row_count": len(data)
        }