"""
Task for handling user questions with LangGraph agent and SQL Agent Tool.
"""
from typing import Dict, Any, Literal
import logging

from worker.src.core.celery_app import celery_app, update_task_progress
from common.enum.task_enum import TaskType

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

from worker.src.tools.sql_tool import SQLAgentTool
from worker.src.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


def get_ollama_model(model_name: str = "gpt-oss:20b-cloud") -> ChatOllama:
    """Get ChatOllama model instance with tool support."""
    return ChatOllama(
        model=model_name,
        temperature=0
    )

def create_agent_graph():
    """Create the LangGraph agent with SQL Agent Tool."""
    
    # Initialize ChatOllama (supports tool calling)
    llm = get_ollama_model()
    
    # Initialize SQL Agent Tool
    sql_agent = SQLAgentTool()
    tools = [sql_agent]
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    
    # Define the agent function
    def call_model(state: MessagesState):
        """Call the LLM with tools"""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Define routing function
    def should_continue(state: MessagesState) -> Literal["tools", END]:
        """Determine whether to continue with tools or end"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, route to tools node
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # Otherwise, end the conversation
        return END
    
    # Build the graph
    workflow = StateGraph(MessagesState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    return workflow.compile()


@celery_app.task(name=TaskType.ASK_QUESTION, bind=True)
def process_user_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
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
    task_id = self.request.id
    
    if not question:
        return {"error": "No question provided", "success": False}
    
    update_task_progress(task_id, "Received question, initializing agent")
    
    try:
        # Create the agent graph
        logger.info("Initializing LangGraph agent with SQL Agent Tool")
        update_task_progress(task_id, "Creating LangGraph agent with SQL capabilities")
        
        agent = create_agent_graph()
        update_task_progress(task_id, "Agent initialized successfully")
        
        # Prepare messages with system prompt
        update_task_progress(task_id, "Preparing system prompt and context")
        
        # Load system prompt from Jinja2 template
        system_prompt = load_prompt("agent_system.j2")
        system_message = SystemMessage(content=system_prompt)
        human_message = HumanMessage(content=question)
        
        # Invoke the agent
        logger.info(f"Processing question: {question}")
        update_task_progress(task_id, f"Fetching information from DB and analyzing...")
        
        result = agent.invoke({
            "messages": [system_message, human_message]
        })
        
        update_task_progress(task_id, "Question processed, extracting response")
        
        # Extract the final response
        messages = result["messages"]
        final_response = messages[-1].content if messages else "No response generated"
        
        update_task_progress(task_id, "Formatting final response")
        
        response_data = {
            "question": question,
            "response": final_response,
            "success": True,
            "message_count": len(messages)
        }
        
        logger.info(f"Successfully processed question with {len(messages)} messages")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        error_message = f"Error processing question: {str(e)}"
        update_task_progress(task_id, f"Error occurred: {str(e)[:100]}")
        return {
            "error": error_message,
            "success": False
        }