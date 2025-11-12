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
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
        

from common.config.config_manager import get_common_settings
from worker.src.utils.prompt_loader import load_prompt

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
    
    # Use class variable for config (loaded once)
    _config = None
    _data_api_url = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Load config as class variable to avoid Pydantic field issues
        if SQLAgentTool._config is None:
            SQLAgentTool._config = get_common_settings()
            SQLAgentTool._data_api_url = SQLAgentTool._config.data_api.url
        
        # Instance-specific caches
        object.__setattr__(self, '_schema_cache', None)
        object.__setattr__(self, '_tables_cache', None)
    
    @property
    def data_api_url(self) -> str:
        """Get Data API URL"""
        return SQLAgentTool._data_api_url
    
    @property
    def schema_cache(self) -> Optional[Dict[str, Any]]:
        """Get schema cache"""
        return object.__getattribute__(self, '_schema_cache')
    
    @schema_cache.setter
    def schema_cache(self, value: Optional[Dict[str, Any]]):
        """Set schema cache"""
        object.__setattr__(self, '_schema_cache', value)
    
    @property
    def tables_cache(self) -> Optional[List[str]]:
        """Get tables cache"""
        return object.__getattribute__(self, '_tables_cache')
    
    @tables_cache.setter
    def tables_cache(self, value: Optional[List[str]]):
        """Set tables cache"""
        object.__setattr__(self, '_tables_cache', value)
    
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
                url = f"http://localhost:8001{endpoint}"
                
                logger.info(f"data_api url:{url}")
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
        """Analyze the question using LLM to understand intent"""
        
        # Initialize LLM
        llm = ChatOllama(
            model="gpt-oss:120b-cloud",
            temperature=0
        )
        
        # Get available tables for context
        tables = self._get_tables()
        tables_str = ", ".join(tables) if tables else "No tables available"
        
        # Load prompts from Jinja2 templates
        system_prompt = load_prompt("sql_analyzer_system.j2")
        human_prompt = load_prompt(
            "sql_analyzer_human.j2",
            question=question,
            tables_str=tables_str
        )
        
        system_message = SystemMessage(content=system_prompt)
        human_message = HumanMessage(content=human_prompt)
        
        # Get LLM analysis
        response = llm.invoke([system_message, human_message])
        
        # Parse LLM response
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        analysis = json.loads(content)
        
        logger.info(f"LLM Analysis: {analysis}")
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
    
    def _get_relevant_schema(self, likely_tables: List[str]) -> Dict[str, Any]:
        """Get schema information only for likely tables"""
        full_schema = self._get_schema()
        relevant_schema = {}
        
        for table_name in likely_tables:
            if table_name in full_schema:
                relevant_schema[table_name] = full_schema[table_name]
            else:
                logger.warning(f"Table '{table_name}' not found in schema")
        
        return relevant_schema
    
    def _generate_query_with_llm(self, question: str, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate SQL query using LLM based on question and analysis"""
        try:
            # Initialize LLM
            llm = ChatOllama(
                model="gpt-oss:120b-cloud",
                temperature=0
            )
            
            # Get schema information only for likely tables
            likely_tables = analysis.get("likely_tables", [])
            if not likely_tables:
                logger.warning("No likely tables identified for query generation")
                return {
                    "query": None,
                    "explanation": "No relevant tables identified for the question",
                    "confidence": 0.0
                }
            
            relevant_schema = self._get_relevant_schema(likely_tables)
            
            # Get sample data if needed and available
            sample_data = None
            sample_table = None
            if analysis.get("needs_sample") and likely_tables:
                sample_table = likely_tables[0]
                sample_result = self._get_table_sample(sample_table, limit=2)
                if sample_result.get("success"):
                    sample_data = sample_result.get("data", [])
            
            # Load prompts from Jinja2 templates
            system_prompt = load_prompt("sql_generator_system.j2")
            human_prompt = load_prompt(
                "sql_generator_human.j2",
                question=question,
                analysis=analysis,
                schema=relevant_schema,  # Only relevant tables
                sample_data=sample_data,
                sample_table=sample_table
            )
            
            system_message = SystemMessage(content=system_prompt)
            human_message = HumanMessage(content=human_prompt)
            
            # Get LLM response
            response = llm.invoke([system_message, human_message])
            content = response.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Parse LLM response
            query_result = json.loads(content)
            
            logger.info(f"LLM Query Generation: {query_result}")
            return query_result
            
        except Exception as e:
            logger.error(f"Error generating query with LLM: {str(e)}")
            return {
                "query": None,
                "explanation": f"Error generating query: {str(e)}",
                "confidence": 0.0
            }
    
    
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
            
            # Step 2: Generate query using LLM
            query_result = self._generate_query_with_llm(question, analysis)
            query = None
            
            if query_result and query_result.get("query"):
                query = query_result["query"]
                explanation = query_result.get("explanation", "")
                confidence = query_result.get("confidence", 0.0)
                
                logger.info(f"Generated query: {query}")
                logger.info(f"Explanation: {explanation}")
                logger.info(f"Confidence: {confidence}")
                
                # Only use query if confidence is reasonable
                if confidence < 0.5:
                    logger.warning(f"Low confidence query ({confidence}): {query}")
                    query = None
            
            if not query:
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