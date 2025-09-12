"""
Platform-Ready LangGraph Agent with Salesforce Integration

This version is optimized for deployment on LangGraph Platform with fallback mechanisms.
"""

import os
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

# Import platform-ready Salesforce integration
from salesforce_platform_ready import create_platform_ready_salesforce_tools, validate_platform_config


class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]


# Initialize search tool
def get_search_tool():
    """Get the Tavily search tool with proper error handling."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
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


# Global variables for tools
search_tool = get_search_tool()
salesforce_tools: List[BaseTool] = []
all_tools: List[BaseTool] = []


async def initialize_platform_tools():
    """Initialize tools for platform deployment."""
    global salesforce_tools, all_tools
    
    print("🔧 Initializing platform-ready tools...")
    
    # Initialize Salesforce tools
    if validate_platform_config():
        try:
            salesforce_tools = await create_platform_ready_salesforce_tools()
            print(f"✅ Loaded {len(salesforce_tools)} Salesforce tools")
        except Exception as e:
            print(f"⚠️  Salesforce tools unavailable: {str(e)}")
            salesforce_tools = []
    else:
        print("⚠️  Salesforce not configured, skipping Salesforce tools")
        salesforce_tools = []
    
    # Combine all tools
    all_tools = [search_tool] + salesforce_tools
    print(f"🛠️  Total tools available: {len(all_tools)}")
    
    return all_tools


def get_tools_sync():
    """Get tools synchronously for graph initialization."""
    global all_tools
    if not all_tools:
        # Try to load tools if not already loaded
        try:
            tools = asyncio.run(initialize_platform_tools())
            return tools
        except Exception as e:
            print(f"⚠️  Using basic tools only: {str(e)}")
            return [search_tool]
    return all_tools


def create_llm(bind_tools: bool = False) -> ChatOpenAI:
    """Create and configure the OpenAI LLM instance."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if bind_tools:
        tools = get_tools_sync()
        llm = llm.bind_tools(tools)
    
    return llm


def should_continue(state: ChatState) -> str:
    """Determine whether to continue with tool calls or end the conversation."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def chat_node(state: ChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Main chat node with platform-ready tool integration."""
    try:
        messages = state["messages"]
        tools = get_tools_sync()
        
        # Add capability message if not present
        capabilities_mentioned = any(
            msg.content and ("search" in str(msg.content).lower() or "salesforce" in str(msg.content).lower()) 
            for msg in messages if hasattr(msg, 'content') and msg.content
        )
        
        if not capabilities_mentioned:
            capabilities = ["search the internet for current information"]
            
            # Check for Salesforce tools
            has_salesforce = any("salesforce" in tool.name.lower() for tool in tools)
            if has_salesforce:
                capabilities.append("interact with Salesforce data and operations")
            
            system_message = AIMessage(
                content=f"I can {' and '.join(capabilities)}. How can I help you today?"
            )
            messages = [system_message] + messages
        
        llm = create_llm(bind_tools=True)
        response = llm.invoke(messages)
        return {"messages": [response]}
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
        )
        return {"messages": [error_message]}


class AdvancedChatState(ChatState):
    """Enhanced state for advanced chat agent."""
    user_id: str = ""
    session_id: str = ""
    conversation_count: int = 0


def advanced_chat_node(state: AdvancedChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Advanced chat node with enhanced context and platform compatibility."""
    try:
        llm = create_llm(bind_tools=True)
        tools = get_tools_sync()
        
        messages = state["messages"]
        conversation_count = state.get("conversation_count", 0)
        
        if conversation_count == 0:
            capabilities = ["search the internet"]
            has_salesforce = any("salesforce" in tool.name.lower() for tool in tools)
            if has_salesforce:
                capabilities.append("work with Salesforce data")
                
            system_context = AIMessage(
                content=f"Hello! I'm your AI assistant. I can {' and '.join(capabilities)}. How can I help you today?"
            )
            messages = [system_context] + messages
        
        response = llm.invoke(messages)
        
        return {
            "messages": [response],
            "conversation_count": conversation_count + 1
        }
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
        )
        return {
            "messages": [error_message],
            "conversation_count": state.get("conversation_count", 0)
        }


def should_continue_advanced(state: AdvancedChatState) -> str:
    """Determine continuation for advanced agent."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def create_platform_graph() -> StateGraph:
    """Create platform-ready graph."""
    workflow = StateGraph(ChatState)
    tools = get_tools_sync()
    
    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("chat")
    
    workflow.add_conditional_edges(
        "chat",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    workflow.add_edge("tools", "chat")
    
    return workflow.compile()


def create_advanced_platform_graph() -> StateGraph:
    """Create advanced platform-ready graph."""
    workflow = StateGraph(AdvancedChatState)
    tools = get_tools_sync()
    
    workflow.add_node("advanced_chat", advanced_chat_node)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("advanced_chat")
    
    workflow.add_conditional_edges(
        "advanced_chat",
        should_continue_advanced,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    workflow.add_edge("tools", "advanced_chat")
    
    return workflow.compile()


# Export graphs for LangGraph Platform deployment
graph = create_platform_graph()
advanced_graph = create_advanced_platform_graph()


def main():
    """Local testing function."""
    print("🚀 Testing Platform-Ready Agent...")
    
    # Initialize tools
    tools = asyncio.run(initialize_platform_tools())
    print(f"✅ Initialized with {len(tools)} tools")
    
    # Test basic conversation
    test_state = {
        "messages": [HumanMessage(content="What capabilities do you have?")]
    }
    
    result = graph.invoke(test_state)
    print("🤖 Agent Response:", result["messages"][-1].content)


if __name__ == "__main__":
    main()
