"""
Task for handling user questions with LangGraph agent and SQL tool.
"""
import json
from typing import Dict, Any, Optional
import httpx
import logging

from worker.src.core.celery_app import celery_app, update_task_progress
from common.enum.task_enum import TaskType
from common.config.config_manager import get_common_settings

from langchain_ollama import OllamaLLM
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Get configuration
config = get_common_settings()
DATA_API_URL = getattr(config, 'data_api_url', 'http://localhost:8001')


@tool
def execute_sql_query(query: str) -> str:
    """
    Execute a SQL query on the SQLite database.
    
    Args:
        query: SQL query to execute (SELECT, INSERT, UPDATE, DELETE)
        
    Returns:
        JSON string with query results or error message
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{DATA_API_URL}/api/query/execute",
                json={"query": query}
            )
            response.raise_for_status()
            return json.dumps(response.json())
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}")
        return json.dumps({"error": str(e), "success": False})


@tool
def get_database_schema() -> str:
    """
    Get the schema of all tables in the database.
    
    Returns:
        JSON string with table schemas
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{DATA_API_URL}/api/schema")
            response.raise_for_status()
            return json.dumps(response.json())
    except Exception as e:
        logger.error(f"Error getting database schema: {str(e)}")
        return json.dumps({"error": str(e), "success": False})


def get_ollama_model(model_name: str = "gpt-oss:20b-cloud") -> OllamaLLM:
    """Get Ollama LLM model instance."""
    return OllamaLLM(model=model_name)


def create_agent_graph():
    """Create the LangGraph agent with SQL tools."""
    
    # Initialize LLM
    llm = get_ollama_model()
    
    # Bind tools to LLM
    tools = [execute_sql_query, get_database_schema]
    llm_with_tools = llm.bind_tools(tools)
    
    # Define the agent function
    def call_model(state: MessagesState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define the graph
    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    
    # Add edges
    workflow.add_edge(START, "agent")
    
    def should_continue(state: MessagesState):
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END
    
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


@celery_app.task(name=TaskType.ASK_QUESTION)
def process_user_question(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a user question using LangGraph agent with SQL capabilities.
    
    Args:
        question_data: Dictionary containing the user's question and any context
        
    Returns:
        Dictionary with the agent response
    """
    question = question_data.get("question", "")
    if not question:
        return {"error": "No question provided", "success": False}
    
    update_task_progress(10, "Received question, initializing agent")
    
    try:
        # Create the agent graph
        agent = create_agent_graph()
        update_task_progress(30, "Agent initialized, processing question")
        
        # Prepare messages with system prompt
        system_message = SystemMessage(
            content="""You are a helpful SQL assistant. You have access to a SQLite database.
            When users ask questions about data, use the available tools to:
            1. Check the database schema if needed
            2. Execute appropriate SQL queries
            3. Provide clear, helpful answers based on the results
            
            Always explain what you're doing and interpret the results for the user."""
        )
        human_message = HumanMessage(content=question)
        
        # Invoke the agent
        result = agent.invoke({
            "messages": [system_message, human_message]
        })
        
        update_task_progress(90, "Question processed, preparing response")
        
        # Extract the final response
        messages = result["messages"]
        final_response = messages[-1].content if messages else "No response generated"
        
        response_data = {
            "question": question,
            "response": final_response,
            "success": True,
            "message_count": len(messages)
        }
        
        update_task_progress(100, "Response ready")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        error_message = f"Error processing question: {str(e)}"
        return {
            "error": error_message,
            "success": False
        }