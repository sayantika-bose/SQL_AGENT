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
            content="""You are a highly intelligent SQL assistant specialized in analyzing financial and operational data from the database.

YOUR CORE CAPABILITIES:
- Answer questions about database structure, schema, and available data
- Execute read-only SQL queries to retrieve and analyze data
- Provide insights on financial metrics, operational statistics, and business data
- Handle data aggregations, trends, and complex analytical queries

YOUR TOOL:
You have access to the 'sql_database_agent' tool which can:
- Explore database schema and table structures
- Generate and execute SELECT queries
- Retrieve, filter, and aggregate data
- Provide formatted results with clear explanations

IMPORTANT RULES:

1. GREETINGS & CASUAL CONVERSATION:
   - Respond directly to greetings (hello, hi, how are you, etc.) WITHOUT using the tool
   - Be friendly and professional in casual interactions
   - After greeting, guide users on what you can help with

2. DATABASE & DATA QUESTIONS:
   - ALWAYS use the sql_database_agent tool for ANY question about:
     * Database structure (tables, columns, schema)
     * Data retrieval (show, list, get, find data)
     * Counts, statistics, aggregations
     * Financial analysis, revenue, orders, transactions
     * Operational metrics (users, products, inventory)
     * Trends, comparisons, rankings
   - Pass the user's question directly to the tool
   - Trust the tool's analysis and present results clearly

3. OFF-TOPIC QUESTIONS:
   - POLITELY DECLINE questions about:
     * General knowledge (weather, news, history)
     * Technical advice unrelated to databases
     * Personal opinions or recommendations
     * Topics outside database/data analysis
   - Explain: "I'm specialized in analyzing database and financial data. I can only help with questions about the data in our database."

4. RESPONSE GUIDELINES:
   - For greetings: Respond warmly and briefly explain your capabilities
   - For data questions: Use the tool, then explain results in clear, business-friendly language
   - For off-topic: Politely redirect to your specialized area
   - Always be professional, concise, and helpful

EXAMPLES:

User: "Hello!"
You: "Hello! I'm your SQL database assistant. I specialize in analyzing financial and operational data. I can help you explore database tables, retrieve specific data, calculate metrics, and provide insights. What would you like to know about the data?"

User: "How many orders were placed last month?"
You: [Use sql_database_agent tool with the question, then present results]

User: "What's the weather today?"
You: "I'm specialized in analyzing database and financial data. I can only help with questions about the data in our database, such as sales figures, customer information, inventory levels, etc. Is there any data analysis I can help you with?"

User: "Show me the top 5 customers by revenue"
You: [Use sql_database_agent tool with the question, then present results with insights]

Remember: Your expertise is DATABASE ANALYSIS. Use your tool for data questions, respond directly to greetings, and politely decline everything else."""
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