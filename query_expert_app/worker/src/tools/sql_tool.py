"""
SQL Agent Tool - A comprehensive BaseTool for answering questions from database
"""
import json
import httpx
from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
import logging

from common.config.config_manager import get_common_settings

logger = logging.getLogger(__name__)


class SQLAgentInput(BaseModel):
    """Input schema for SQL Agent Tool"""
    question: str = Field(
        description="Natural language question about the database data. "
                    "Examples: 'How many users are there?', 'What are the top 5 products by price?', "
                    "'Show me all orders from the last month'"
    )


class SQLAgentTool(BaseTool):
    """
    SQL Agent Tool that can intelligently answer questions about database data.
    
    This tool:
    1. Analyzes the user's question
    2. Explores database schema
    3. Generates appropriate SQL queries
    4. Executes queries (read-only)
    5. Interprets results
    6. Provides natural language answers
    """
    
    name: str = "sql_database_agent"
    description: str = (
        "Use this tool to answer questions about data in the database. "
        "It can understand natural language questions, explore the database schema, "
        "generate and execute SQL queries, and provide clear answers. "
        "This tool has read-only access and can only retrieve data, not modify it. "
        "Examples: 'How many users are registered?', 'What are the most expensive products?', "
        "'Show me orders with status completed'"
    )
    args_schema: Type[BaseModel] = SQLAgentInput
    return_direct: bool = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = get_common_settings()
        self.data_api_url = self.config.data_api_url
        self.schema_cache: Optional[Dict[str, Any]] = None
        self.tables_cache: Optional[List[str]] = None
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Data API"""
        try:
            with httpx.Client(timeout=30.0) as client:
                url = f"{self.data_api_url}{endpoint}"
                
                if method.upper() == "GET":
                    response = client.get(url, params=params)
                elif method.upper() == "POST":
                    response = client.post(url, json=json_data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_schema(self) -> Dict[str, Any]:
        """Get database schema (cached)"""
        if self.schema_cache is None:
            result = self._make_request("GET", "/api/schema/")
            if result.get("success"):
                self.schema_cache = result.get("tables", {})
            else:
                logger.error(f"Failed to get schema: {result.get('error')}")
                self.schema_cache = {}
        return self.schema_cache
    
    def _get_tables(self) -> List[str]:
        """Get list of tables (cached)"""
        if self.tables_cache is None:
            result = self._make_request("GET", "/api/schema/tables")
            if result.get("success"):
                self.tables_cache = result.get("tables", [])
            else:
                logger.error(f"Failed to get tables: {result.get('error')}")
                self.tables_cache = []
        return self.tables_cache
    
    def _get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed table information"""
        return self._make_request("GET", f"/api/schema/table/{table_name}")
    
    def _get_table_sample(self, table_name: str, limit: int = 3) -> Dict[str, Any]:
        """Get sample data from table"""
        return self._make_request("GET", f"/api/table/{table_name}", params={"limit": limit, "offset": 0})
    
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute SQL SELECT query"""
        return self._make_request("POST", "/api/query/execute", json_data={"query": query})
    
    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze the question to understand intent"""
        question_lower = question.lower()
        
        analysis = {
            "needs_schema": False,
            "needs_sample": False,
            "likely_tables": [],
            "question_type": "general",
            "keywords": []
        }
        
        # Check if question asks about structure
        if any(word in question_lower for word in ["table", "column", "schema", "structure", "what data"]):
            analysis["needs_schema"] = True
            analysis["question_type"] = "schema"
        
        # Check if question asks about counts/aggregations
        if any(word in question_lower for word in ["how many", "count", "total", "sum", "average", "max", "min"]):
            analysis["question_type"] = "aggregation"
        
        # Check if question asks for specific records
        if any(word in question_lower for word in ["show", "list", "get", "find", "display", "what are"]):
            analysis["question_type"] = "retrieval"
            analysis["needs_sample"] = True
        
        # Try to identify relevant tables from question
        tables = self._get_tables()
        for table in tables:
            if table.lower() in question_lower or table.lower()[:-1] in question_lower:
                analysis["likely_tables"].append(table)
        
        return analysis
    
    def _generate_schema_summary(self) -> str:
        """Generate a human-readable schema summary"""
        schema = self._get_schema()
        if not schema:
            return "No tables found in database."
        
        summary = "Database Schema:\n\n"
        for table_name, columns in schema.items():
            summary += f"Table: {table_name}\n"
            summary += "Columns:\n"
            for col in columns:
                col_info = f"  - {col['name']} ({col['type']})"
                if col.get('pk'):
                    col_info += " [PRIMARY KEY]"
                if col.get('notnull'):
                    col_info += " [NOT NULL]"
                summary += col_info + "\n"
            summary += "\n"
        
        return summary
    
    def _build_query_from_analysis(self, question: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Build SQL query based on question analysis"""
        question_lower = question.lower()
        
        # If specific tables identified, use them
        if analysis["likely_tables"]:
            table = analysis["likely_tables"][0]
            
            # Count queries
            if "how many" in question_lower or "count" in question_lower:
                return f"SELECT COUNT(*) as count FROM {table}"
            
            # Top/best queries
            if "top" in question_lower or "best" in question_lower or "most" in question_lower:
                # Try to identify number
                import re
                numbers = re.findall(r'\d+', question)
                limit = int(numbers[0]) if numbers else 5
                
                # Try to identify sort column
                schema = self._get_schema()
                table_cols = schema.get(table, [])
                
                # Common sort columns
                sort_col = None
                for col in table_cols:
                    col_name = col['name'].lower()
                    if any(word in question_lower for word in ['price', 'amount', 'total', 'cost']) and 'price' in col_name or 'amount' in col_name:
                        sort_col = col['name']
                        break
                
                if sort_col:
                    return f"SELECT * FROM {table} ORDER BY {sort_col} DESC LIMIT {limit}"
                else:
                    return f"SELECT * FROM {table} LIMIT {limit}"
            
            # Recent queries
            if "recent" in question_lower or "latest" in question_lower or "last" in question_lower:
                schema = self._get_schema()
                table_cols = schema.get(table, [])
                
                # Find date/timestamp column
                date_col = None
                for col in table_cols:
                    col_name = col['name'].lower()
                    if any(word in col_name for word in ['date', 'time', 'created', 'updated']):
                        date_col = col['name']
                        break
                
                if date_col:
                    return f"SELECT * FROM {table} ORDER BY {date_col} DESC LIMIT 10"
                else:
                    return f"SELECT * FROM {table} LIMIT 10"
            
            # Status/filter queries
            if "status" in question_lower or "where" in question_lower:
                # Try to extract status value
                import re
                # Look for quoted strings or specific status words
                status_match = re.search(r"'([^']+)'|\"([^\"]+)\"|status\s+(\w+)", question_lower)
                if status_match:
                    status = status_match.group(1) or status_match.group(2) or status_match.group(3)
                    return f"SELECT * FROM {table} WHERE status = '{status}' LIMIT 10"
            
            # Default: show sample
            return f"SELECT * FROM {table} LIMIT 10"
        
        return None
    
    def _format_results(self, results: Dict[str, Any], question: str) -> str:
        """Format query results into natural language"""
        if not results.get("success"):
            return f"Error: {results.get('error', 'Unknown error occurred')}"
        
        data = results.get("data", [])
        row_count = results.get("row_count", 0)
        
        if row_count == 0:
            return "No data found matching your question."
        
        # For count queries
        if len(data) == 1 and 'count' in data[0]:
            return f"Result: {data[0]['count']}"
        
        # For single row results
        if row_count == 1:
            row = data[0]
            result = "Found 1 record:\n"
            for key, value in row.items():
                result += f"  {key}: {value}\n"
            return result
        
        # For multiple rows
        if row_count <= 10:
            result = f"Found {row_count} records:\n\n"
            for idx, row in enumerate(data, 1):
                result += f"Record {idx}:\n"
                for key, value in row.items():
                    result += f"  {key}: {value}\n"
                result += "\n"
            return result
        
        # For large result sets, show summary
        result = f"Found {row_count} records. Here are the first few:\n\n"
        for idx, row in enumerate(data[:5], 1):
            result += f"Record {idx}:\n"
            for key, value in row.items():
                result += f"  {key}: {value}\n"
            result += "\n"
        result += f"\n(Showing 5 of {row_count} total records)"
        return result
    
    def _run(
        self,
        question: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """
        Execute the SQL agent tool.
        
        Args:
            question: Natural language question about the database
            run_manager: Callback manager
            
        Returns:
            Natural language answer to the question
        """
        try:
            logger.info(f"SQL Agent processing question: {question}")
            
            # Step 1: Analyze the question
            analysis = self._analyze_question(question)
            logger.info(f"Question analysis: {analysis}")
            
            # Step 2: Handle schema questions
            if analysis["question_type"] == "schema":
                if "tables" in question.lower() or "what tables" in question.lower():
                    tables = self._get_tables()
                    return f"The database contains {len(tables)} tables: {', '.join(tables)}"
                else:
                    return self._generate_schema_summary()
            
            # Step 3: Get schema if needed
            schema = self._get_schema()
            if not schema:
                return "Error: Unable to access database schema."
            
            # Step 4: Identify relevant tables
            if not analysis["likely_tables"]:
                # If no tables identified, list available tables
                tables = self._get_tables()
                return (f"I couldn't identify which table to query. "
                       f"Available tables are: {', '.join(tables)}. "
                       f"Please specify which table you're interested in.")
            
            # Step 5: Get sample data if needed
            if analysis["needs_sample"]:
                table = analysis["likely_tables"][0]
                sample = self._get_table_sample(table, limit=2)
                logger.info(f"Got sample from {table}")
            
            # Step 6: Generate and execute query
            query = self._build_query_from_analysis(question, analysis)
            
            if not query:
                # Fallback: show table info
                table = analysis["likely_tables"][0]
                info = self._get_table_info(table)
                if info.get("success"):
                    return (f"Table '{table}' has {info.get('row_count', 0)} rows "
                           f"with {len(info.get('columns', []))} columns. "
                           "Please ask a more specific question.")
                else:
                    return "I need more information to answer your question. Please be more specific."
            
            logger.info(f"Executing query: {query}")
            results = self._execute_query(query)
            
            # Step 7: Format and return results
            answer = self._format_results(results, question)
            logger.info(f"Answer generated: {len(answer)} characters")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error in SQL Agent: {str(e)}", exc_info=True)
            return f"Error processing question: {str(e)}"
    
    async def _arun(
        self,
        question: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async version - not implemented, falls back to sync"""
        return self._run(question, run_manager)