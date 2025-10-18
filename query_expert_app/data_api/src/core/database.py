"""
Database connection and management
"""
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from pathlib import Path
import logging

from data_api.src.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """SQLite database connection manager"""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        
    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """
        Get a database connection context manager.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def execute_select(
        self, 
        query: str, 
        params: Optional[Tuple] = None,
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of dictionaries containing query results
        """
        with self.get_connection() as conn:
            conn.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
    
    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the database.
        
        Returns:
            List of table names
        """
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        results = self.execute_select(query)
        return [row['name'] for row in results]
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        query = f"PRAGMA table_info({table_name})"
        return self.execute_select(query)
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table
            
        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT COUNT(*) as count FROM sqlite_master 
            WHERE type='table' AND name=?
        """
        result = self.execute_select(query, (table_name,))
        return result[0]['count'] > 0
    
    def get_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of rows
        """
        if not self.table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.execute_select(query)
        return result[0]['count']


# Global database instance
_db_instance: Optional[DatabaseConnection] = None


def get_db() -> DatabaseConnection:
    """
    Get database instance (singleton).
    
    Returns:
        DatabaseConnection instance
    """
    global _db_instance
    if _db_instance is None:
        settings = get_settings()
        _db_instance = DatabaseConnection(settings.database_path)
        logger.info(f"Database connection initialized: {settings.database_path}")
    return _db_instance


def init_db():
    """Initialize database connection"""
    db = get_db()
    logger.info(f"Database initialized at: {db.db_path}")
    return db