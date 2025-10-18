"""
Task for handling user questions with LangGraph agent and SQL Agent Tool.
"""
from typing import Dict, Any
import logging

from worker.src.core.celery_app import celery_app, update_task_progress
from common.enum.task_enum import TaskType

from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

from worker.src.tools.sql_tool import SQLAgentTool

logger = logging.getLogger(__name__)


def get_ollama_model(model_name: str = "gpt-oss:20b-cloud") -> OllamaLLM:
    """Get Ollama LLM model instance."""
    return OllamaLLM(model=model_name)


def create_agent_graph():
    """Create the LangGraph agent with SQL Agent Tool."""
    
    # Initialize LLM
    llm = get_ollama_model()
    
    # Initialize SQL Agent Tool
    sql_agent = SQLAgentTool()
    tools = [sql_agent]
    
    # Bind tools to LLM
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
    Process a user question using LangGraph agent with SQL Agent Tool.
    
    The SQL Agent Tool can:
    - Understand natural language questions about database data
    - Automatically explore database schema
    - Generate and execute appropriate SQL queries
    - Interpret results and provide clear answers
    
    Args:
        question_data: Dictionary containing:
            - question (str): User's question about the database
            - context (dict, optional): Additional context
        
    Returns:
        Dictionary with:
            - success (bool): Whether processing was successful
            - question (str): Original question
            - response (str): Agent's answer
            - error (str, optional): Error message if failed
    
    Examples:
        >>> process_user_question({"question": "How many users are registered?"})
        >>> process_user_question({"question": "What are the top 5 most expensive products?"})
        >>> process_user_question({"question": "Show me all completed orders"})
    """
    question = question_data.get("question", "")
    if not question:
        return {"error": "No question provided", "success": False}
    
    update_task_progress(10, "Received question, initializing agent")
    
    try:
        # Create the agent graph
        agent = create_agent_graph()
        update_task_progress(30, "Agent initialized with SQL Agent Tool")
        
        # Prepare messages with system prompt
        system_message = SystemMessage(
            content="""You are an intelligent assistant that helps users understand and query their database.

You have access to a powerful SQL Agent Tool that can:
- Answer questions about database structure (tables, columns, schema)
- Execute read-only SQL queries to retrieve data
- Analyze and interpret query results
- Provide clear, natural language answers

How to use the tool:
- Use the 'sql_database_agent' tool for ANY question about the database or its data
- Pass the user's question directly to the tool
- The tool will handle schema exploration, query generation, and result formatting
- Trust the tool's analysis and present its findings to the user

Guidelines:
- Always use the SQL Agent Tool for database-related questions
- Don't try to write SQL queries yourself - let the tool handle it
- Present the tool's results in a clear, user-friendly manner
- If the tool returns an error, explain it to the user and suggest alternatives
- For complex questions, you may need to call the tool multiple times

Example workflow:
1. User asks: "How many orders are there?"
2. Use sql_database_agent with question: "How many orders are there?"
3. Present the tool's answer to the user

Remember: The SQL Agent Tool is intelligent and can understand complex questions, 
so pass the user's question directly to it without modification."""
        )
        human_message = HumanMessage(content=question)
        
        # Invoke the agent
        logger.info(f"Processing question: {question}")
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
        logger.info(f"Successfully processed question with {len(messages)} messages")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        error_message = f"Error processing question: {str(e)}"
        return {
            "error": error_message,
            "success": False
        }