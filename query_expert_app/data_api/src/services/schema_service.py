"""
Service layer for schema operations
"""
from typing import List, Dict, Any
import logging

from data_api.src.core.database import DatabaseConnection
from data_api.src.utils.validators import QueryValidator

logger = logging.getLogger(__name__)


class SchemaService:
    """Service for handling database schema operations"""
    
    def __init__(self, db: DatabaseConnection):
        """
        Initialize schema service.
        
        Args:
            db: Database connection instance
        """
        self.db = db
        self.validator = QueryValidator()
    
    def get_all_tables(self) -> List[str]:
        """
        Get list of all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            tables = self.db.get_tables()
            logger.info(f"Retrieved {len(tables)} tables")
            return tables
        except Exception as e:
            logger.error(f"Failed to get tables: {str(e)}")
            raise
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        # Sanitize table name
        safe_table_name = self.validator.sanitize_table_name(table_name)
        
        # Check if table exists
        if not self.db.table_exists(safe_table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        try:
            schema = self.db.get_table_schema(safe_table_name)
            logger.info(f"Retrieved schema for table: {table_name}")
            return schema
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            raise
    
    def get_all_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get schema information for all tables.
        
        Returns:
            Dictionary mapping table names to their schema information
        """
        try:
            tables = self.get_all_tables()
            schemas = {}
            
            for table in tables:
                schemas[table] = self.get_table_schema(table)
            
            logger.info(f"Retrieved schemas for {len(schemas)} tables")
            return schemas
            
        except Exception as e:
            logger.error(f"Failed to get all schemas: {str(e)}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        # Sanitize table name
        safe_table_name = self.validator.sanitize_table_name(table_name)
        
        # Check if table exists
        if not self.db.table_exists(safe_table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        try:
            schema = self.get_table_schema(table_name)
            row_count = self.db.get_row_count(safe_table_name)
            
            return {
                "table_name": table_name,
                "columns": schema,
                "row_count": row_count,
                "column_count": len(schema)
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {str(e)}")
            raise