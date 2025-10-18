"""
Utility functions for query validation and sanitization
"""
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class QueryValidator:
    """Validator for SQL queries"""
    
    # Prohibited keywords that indicate write operations
    PROHIBITED_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 
        'ALTER', 'TRUNCATE', 'REPLACE', 'EXEC', 'EXECUTE',
        'PRAGMA', 'ATTACH', 'DETACH'
    ]
    
    # Allowed keywords for read operations
    ALLOWED_KEYWORDS = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT',
        'INNER', 'OUTER', 'ON', 'GROUP', 'BY', 'HAVING',
        'ORDER', 'LIMIT', 'OFFSET', 'AS', 'DISTINCT',
        'UNION', 'INTERSECT', 'EXCEPT', 'CASE', 'WHEN',
        'THEN', 'ELSE', 'END', 'IN', 'NOT', 'AND', 'OR',
        'LIKE', 'BETWEEN', 'IS', 'NULL', 'EXISTS'
    ]
    
    @staticmethod
    def is_select_query(query: str) -> bool:
        """
        Check if query is a SELECT statement.
        
        Args:
            query: SQL query string
            
        Returns:
            True if query starts with SELECT, False otherwise
        """
        query_stripped = query.strip().upper()
        return query_stripped.startswith('SELECT')
    
    @staticmethod
    def contains_prohibited_keywords(query: str) -> tuple[bool, Optional[str]]:
        """
        Check if query contains prohibited keywords.
        
        Args:
            query: SQL query string
            
        Returns:
            Tuple of (contains_prohibited, keyword)
        """
        query_upper = query.upper()
        
        for keyword in QueryValidator.PROHIBITED_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, query_upper):
                return True, keyword
        
        return False, None
    
    @staticmethod
    def validate_query(query: str, max_length: int = 10000) -> tuple[bool, Optional[str]]:
        """
        Validate SQL query for safety and correctness.
        
        Args:
            query: SQL query string
            max_length: Maximum allowed query length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if query is empty
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        # Check query length
        if len(query) > max_length:
            return False, f"Query exceeds maximum length of {max_length} characters"
        
        # Check if it's a SELECT query
        if not QueryValidator.is_select_query(query):
            return False, "Only SELECT queries are allowed"
        
        # Check for prohibited keywords
        has_prohibited, keyword = QueryValidator.contains_prohibited_keywords(query)
        if has_prohibited:
            return False, f"Query contains prohibited keyword: {keyword}"
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'--',  # SQL comments
            r'/\*',  # Multi-line comments
            r'xp_',  # SQL Server extended procedures
            r'sp_',  # SQL Server stored procedures
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Query contains suspicious pattern: {pattern}"
        
        return True, None
    
    @staticmethod
    def sanitize_table_name(table_name: str) -> str:
        """
        Sanitize table name to prevent SQL injection.
        
        Args:
            table_name: Table name to sanitize
            
        Returns:
            Sanitized table name
        """
        # Remove any characters that aren't alphanumeric or underscore
        sanitized = re.sub(r'[^\w]', '', table_name)
        
        if not sanitized:
            raise ValueError("Invalid table name")
        
        return sanitized
    
    @staticmethod
    def validate_limit_offset(limit: int, offset: int) -> tuple[bool, Optional[str]]:
        """
        Validate LIMIT and OFFSET parameters.
        
        Args:
            limit: LIMIT value
            offset: OFFSET value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if limit < 1:
            return False, "LIMIT must be at least 1"
        
        if limit > 10000:
            return False, "LIMIT cannot exceed 10000"
        
        if offset < 0:
            return False, "OFFSET cannot be negative"
        
        return True, None


class QuerySanitizer:
    """Sanitizer for SQL queries"""
    
    @staticmethod
    def remove_comments(query: str) -> str:
        """
        Remove SQL comments from query.
        
        Args:
            query: SQL query string
            
        Returns:
            Query without comments
        """
        # Remove single-line comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        
        # Remove multi-line comments
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        return query
    
    @staticmethod
    def normalize_whitespace(query: str) -> str:
        """
        Normalize whitespace in query.
        
        Args:
            query: SQL query string
            
        Returns:
            Query with normalized whitespace
        """
        # Replace multiple whitespace with single space
        query = re.sub(r'\s+', ' ', query)
        
        # Strip leading/trailing whitespace
        query = query.strip()
        
        return query
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize SQL query.
        
        Args:
            query: SQL query string
            
        Returns:
            Sanitized query
        """
        query = QuerySanitizer.remove_comments(query)
        query = QuerySanitizer.normalize_whitespace(query)
        return query