"""
LangGraph Platform-Ready Chat Agent

A production-ready conversational AI agent built with LangGraph and OpenAI GPT-4o-mini.
Designed for seamless deployment on LangGraph Platform with API support.
"""

import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]


# Initialize the Tavily search tool
def get_search_tool():
    """Get the Tavily search tool with proper error handling."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        # If no API key, return a dummy tool that explains the issue
        from langchain_core.tools import Tool
        def no_key_search(query: str) -> str:
            return "❌ Search unavailable: TAVILY_API_KEY not set. Please set your Tavily API key in environment variables."
        
        return Tool(
            name="tavily_search",
            description="Search the internet for current information",
            func=no_key_search
        )
    
    return TavilySearch(
        max_results=3,
        search_depth="advanced", 
        include_answer=True,
        include_raw_content=False,
        include_images=False,
        tavily_api_key=api_key
    )

search_tool = get_search_tool()


def create_llm(bind_tools: bool = False) -> ChatOpenAI:
    """Create and configure the OpenAI LLM instance."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if bind_tools:
        # Bind the search tool to the LLM
        llm = llm.bind_tools([search_tool])
    
    return llm


def should_continue(state: ChatState) -> str:
    """
    Determine whether to continue with tool calls or end the conversation.
    
    Args:
        state: Current chat state
        
    Returns:
        Next node name or END
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, we should run the tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def chat_node(state: ChatState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Main chat node that processes user input and generates AI responses with search capabilities.
    
    Args:
        state: Current chat state containing message history
        config: Runtime configuration from LangGraph platform
        
    Returns:
        Dictionary containing the AI response message
    """
    try:
        # Add system message to explain search capabilities
        messages = state["messages"]
        if not any(msg.content and "I can search the internet" in str(msg.content) for msg in messages):
            system_message = AIMessage(
                content="I can search the internet for current information when needed. Just ask me about recent events, news, or current data!"
            )
            messages = [system_message] + messages
        
        llm = create_llm(bind_tools=True)
        response = llm.invoke(messages)
        return {"messages": [response]}
    except Exception as e:
        # Handle errors gracefully
        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
        )
        return {"messages": [error_message]}


def create_simple_graph() -> StateGraph:
    """
    Create a simple chat agent graph with internet search capabilities.
    
    Returns:
        Compiled StateGraph ready for deployment
    """
    # Create the graph
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", ToolNode([search_tool]))
    
    # Set entry point
    workflow.set_entry_point("chat")
    
    # Add conditional logic for tool usage
    workflow.add_conditional_edges(
        "chat",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After running tools, go back to chat
    workflow.add_edge("tools", "chat")
    
    # Compile and return
    return workflow.compile()


class AdvancedChatState(ChatState):
    """Enhanced state for advanced chat agent with session management."""
    user_id: str = ""
    session_id: str = ""
    conversation_count: int = 0


def advanced_chat_node(state: AdvancedChatState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Advanced chat node with session management, enhanced context, and search capabilities.
    
    Args:
        state: Enhanced chat state with user and session information
        config: Runtime configuration from LangGraph platform
        
    Returns:
        Dictionary containing the AI response and updated state
    """
    try:
        llm = create_llm(bind_tools=True)
        
        # Add conversation context if this is a continuing conversation
        messages = state["messages"]
        conversation_count = state.get("conversation_count", 0)
        
        if conversation_count == 0:
            # First message in session with search capabilities
            system_context = AIMessage(
                content="Hello! I'm your advanced AI assistant with internet search capabilities. I can help you with current information, recent events, and research. How can I help you today?"
            )
            messages = [system_context] + messages
        
        response = llm.invoke(messages)
        
        return {
            "messages": [response],
            "conversation_count": conversation_count + 1
        }
        
    except Exception as e:
        # Handle errors gracefully with session context
        user_id = state.get("user_id", "unknown")
        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
        )
        return {
            "messages": [error_message],
            "conversation_count": state.get("conversation_count", 0)
        }


def should_continue_advanced(state: AdvancedChatState) -> str:
    """
    Determine whether to continue with tool calls or end the conversation for advanced agent.
    
    Args:
        state: Current advanced chat state
        
    Returns:
        Next node name or END
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, we should run the tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def create_advanced_graph() -> StateGraph:
    """
    Create an advanced chat agent graph with session management and search capabilities.
    
    Returns:
        Compiled StateGraph with enhanced features
    """
    # Create the graph with advanced state
    workflow = StateGraph(AdvancedChatState)
    
    # Add nodes
    workflow.add_node("advanced_chat", advanced_chat_node)
    workflow.add_node("tools", ToolNode([search_tool]))
    
    # Set entry point
    workflow.set_entry_point("advanced_chat")
    
    # Add conditional logic for tool usage
    workflow.add_conditional_edges(
        "advanced_chat",
        should_continue_advanced,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After running tools, go back to advanced chat
    workflow.add_edge("tools", "advanced_chat")
    
    
    # Compile and return
    return workflow.compile()


# Export graphs for LangGraph Platform deployment
# These variables will be automatically discovered by the platform
graph = create_simple_graph()
advanced_graph = create_advanced_graph()


def main():
    """
    Local testing function - not used in platform deployment.
    Run this file directly to test the agent locally.
    """
    print("Testing Simple Chat Agent with Search Capabilities...")
    
    # Test the simple graph
    test_state = {
        "messages": [HumanMessage(content="Hello! Can you explain what you do?")]
    }
    
    result = graph.invoke(test_state)
    print("Agent Response:", result["messages"][-1].content)
    
    print("\n" + "="*50)
    print("Testing Search Functionality...")
    
    # Test search functionality
    search_test_state = {
        "messages": [HumanMessage(content="What are the latest developments in AI technology in 2024?")]
    }
    
    try:
        search_result = graph.invoke(search_test_state)
        print("Search-enabled Response:")
        for msg in search_result["messages"]:
            if hasattr(msg, 'content') and msg.content:
                print(f"- {msg.content}")
    except Exception as e:
        print(f"Search test failed (likely missing TAVILY_API_KEY): {e}")
    
    print("\n" + "="*50)
    print("Testing Advanced Chat Agent with Search...")
    
    # Test the advanced graph
    advanced_test_state = {
        "messages": [HumanMessage(content="What are the current trends in renewable energy?")],
        "user_id": "test_user",
        "session_id": "test_session",
        "conversation_count": 0
    }
    
    try:
        advanced_result = advanced_graph.invoke(advanced_test_state)
        print("Advanced Agent Response:")
        for msg in advanced_result["messages"]:
            if hasattr(msg, 'content') and msg.content:
                print(f"- {msg.content}")
        print("Conversation Count:", advanced_result["conversation_count"])
    except Exception as e:
        print(f"Advanced search test failed (likely missing TAVILY_API_KEY): {e}")
    
    print("\nNote: To enable search functionality, set TAVILY_API_KEY in your .env file.")


if __name__ == "__main__":
    main()