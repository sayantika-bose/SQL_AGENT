"""
Task for handling user questions with LangGraph agent and SQL tools.
"""
from typing import Dict, Any
import logging

from worker.src.core.celery_app import celery_app, update_task_progress
from common.enum.task_enum import TaskType

from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

from worker.src.tools.sql_tool import SQL_TOOLS

logger = logging.getLogger(__name__)


def get_ollama_model(model_name: str = "gpt-oss:20b-cloud") -> OllamaLLM:
    """Get Ollama LLM model instance."""
    return OllamaLLM(model=model_name)


def create_agent_graph():
    """Create the LangGraph agent with SQL tools."""
    
    # Initialize LLM
    llm = get_ollama_model()
    
    # Bind SQL tools to LLM
    llm_with_tools = llm.bind_tools(SQL_TOOLS)
    
    # Define the agent function
    def call_model(state: MessagesState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define the graph
    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(SQL_TOOLS))
    
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
            content="""You are a helpful SQL assistant with read-only access to a SQLite database.

Your capabilities:
1. List all tables in the database
2. Get detailed schema information for tables
3. Execute SELECT queries to retrieve data
4. Get sample data from tables
5. Answer questions about the data

Important guidelines:
- Always check the database schema before writing queries
- Use the list_tables tool to discover available tables
- Use get_table_info or get_table_sample to understand table structure
- Only SELECT queries are allowed - you cannot modify data
- Break down complex questions into steps
- Explain your reasoning and the queries you're running
- Format results in a clear, user-friendly way
- If you're unsure about a table structure, check it first

When answering:
1. Understand what the user is asking
2. Determine what data you need
3. Check the schema if needed
4. Write and execute appropriate SQL queries
5. Interpret and present the results clearly"""
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