"""
Simple Working LangGraph Agent with Salesforce MCP

This version uses a simpler approach that works like Claude Desktop
without complex state management that causes recursion issues.
"""

import os
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv

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

from salesforce_platform_ready import create_platform_ready_salesforce_tools, validate_platform_config


class SimpleState(TypedDict):
    """Simple state for the agent."""
    messages: Annotated[List[BaseMessage], add_messages]


def create_search_tool():
    """Create search tool."""
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        try:
            return TavilySearch(
                max_results=3,
                search_depth="advanced", 
                include_answer=True,
                include_raw_content=False,
                include_images=False,
                tavily_api_key=api_key
            )
        except Exception:
            pass
    
    def fallback_search(query: str) -> str:
        return f"🔍 Search for: '{query}' - External search temporarily unavailable."
    
    from langchain_core.tools import Tool
    return Tool(name="search", description="Search for information", func=fallback_search)


async def initialize_tools() -> List[BaseTool]:
    """Initialize all tools."""
    tools = []
    
    # Add search
    search_tool = create_search_tool()
    tools.append(search_tool)
    
    # Add real Salesforce MCP tools
    if validate_platform_config():
        try:
            print("🔗 Loading REAL Salesforce MCP tools...")
            salesforce_tools = await create_platform_ready_salesforce_tools()
            tools.extend(salesforce_tools)
            print(f"✅ Added {len(salesforce_tools)} Salesforce tools")
        except Exception as e:
            print(f"⚠️ Salesforce tools failed: {str(e)}")
    
    return tools


# Initialize tools at startup
TOOLS = asyncio.run(initialize_tools())


def simple_agent_node(state: SimpleState, config: RunnableConfig) -> Dict[str, Any]:
    """Simple agent node that handles tool calls properly."""
    messages = state["messages"]
    
    # Create LLM with tools
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    ).bind_tools(TOOLS)
    
    # Add system message if this is the start
    if len(messages) == 1:
        dml_available = any("dml" in tool.name.lower() for tool in TOOLS)
        
        system_msg = AIMessage(
            content=f"Hello! I have {len(TOOLS)} tools available. "
                   f"I can search the internet and work with Salesforce "
                   f"{'(including creating/updating records)' if dml_available else '(read-only operations)'}. "
                   f"How can I help?"
        )
        messages = [system_msg] + messages
    
    # Get response from LLM
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue_simple(state: SimpleState) -> str:
    """Simple continuation logic."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, execute them
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end the conversation
    return END


def create_simple_working_graph() -> StateGraph:
    """Create a simple graph that actually works."""
    workflow = StateGraph(SimpleState)
    
    # Add nodes
    workflow.add_node("agent", simple_agent_node)
    workflow.add_node("tools", ToolNode(TOOLS))
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue_simple,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After tools, go back to agent
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Export for platform
graph = create_simple_working_graph()
advanced_graph = graph  # Same graph for now


def main():
    """Test the simple working agent."""
    print(f"🚀 Testing Simple Working Agent with {len(TOOLS)} tools")
    
    # Test Lead creation
    test_state = {
        "messages": [HumanMessage(content="Create a new Lead with FirstName=TestSimple, LastName=TestWorking, Company=Simple Corp, Email=test@simple.com")]
    }
    
    try:
        print("🧪 Testing Lead creation...")
        result = graph.invoke(test_state, config={"recursion_limit": 30})
        
        print("✅ SUCCESS!")
        print(f"💬 Total messages: {len(result['messages'])}")
        
        # Show final response
        final_response = result['messages'][-1].content
        print("\n🤖 Final Response:")
        print("-" * 50)
        print(final_response)
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
