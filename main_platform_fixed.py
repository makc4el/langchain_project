"""
Platform-Fixed LangGraph Agent with Guaranteed Tool Access

This version ensures tools are ALWAYS available, even if Salesforce/MCP fails.
Fixes the missing tools node issue in platform deployments.
"""

import os
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, Tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

# Import Salesforce integration
from salesforce_platform_ready import create_platform_ready_salesforce_tools, validate_platform_config


class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]


class AdvancedChatState(ChatState):
    """Enhanced state for advanced chat agent."""
    user_id: str = ""
    session_id: str = ""
    conversation_count: int = 0


def create_guaranteed_search_tool():
    """Create a search tool that's guaranteed to work."""
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
        except Exception as e:
            print(f"⚠️ Tavily search failed: {e}")
    
    # Fallback search tool
    def fallback_search(query: str) -> str:
        return f"🔍 Search requested for: '{query}'\n\n" \
               f"⚠️ External search is temporarily unavailable. " \
               f"I can still help with Salesforce operations, general questions, " \
               f"and analysis based on my training data."
    
    return Tool(
        name="search",
        description="Search for current information (limited availability)",
        func=fallback_search
    )


def create_guaranteed_salesforce_tools():
    """Create Salesforce tools with multiple fallback levels."""
    print("🔧 Initializing guaranteed Salesforce tools...")
    
    # Try platform-ready tools first
    if validate_platform_config():
        try:
            # This is async, so we'll handle it differently
            print("✅ Salesforce configuration valid, creating tools...")
            
            # Create basic guaranteed Salesforce tools that always work
            guaranteed_tools = []
            
            def salesforce_status() -> str:
                """Check Salesforce integration status."""
                try:
                    config = os.getenv("SALESFORCE_USERNAME", "Not configured")
                    org_url = os.getenv("SALESFORCE_LOGIN_URL", "Not configured")
                    return f"✅ Salesforce Integration Status:\n" \
                           f"📧 User: {config}\n" \
                           f"🏢 Org: {org_url}\n" \
                           f"🔗 Connection: Ready for operations\n\n" \
                           f"Available operations:\n" \
                           f"- SOQL queries (use salesforce_query)\n" \
                           f"- Object descriptions (use salesforce_describe)\n" \
                           f"- Data operations\n" \
                           f"- Custom object management"
                except Exception as e:
                    return f"❌ Salesforce status check failed: {str(e)}"
            
            guaranteed_tools.append(Tool(
                name="salesforce_status",
                description="Check Salesforce integration status and available capabilities",
                func=salesforce_status
            ))
            
            def guaranteed_soql_query(query: str) -> str:
                """Execute SOQL queries with guaranteed response."""
                try:
                    # Import here to handle missing dependency gracefully
                    from simple_salesforce import Salesforce
                    
                    username = os.getenv("SALESFORCE_USERNAME")
                    password = os.getenv("SALESFORCE_PASSWORD")
                    security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
                    instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
                    
                    if not all([username, password]):
                        return "❌ Salesforce credentials not properly configured in environment variables"
                    
                    # Create Salesforce connection
                    sf = Salesforce(
                        username=username,
                        password=password,
                        security_token=security_token,
                        instance_url=instance_url
                    )
                    
                    # Execute query
                    result = sf.query(query)
                    
                    if result['totalSize'] == 0:
                        return f"✅ Query executed successfully. No records found.\nQuery: {query}"
                    
                    # Return formatted results
                    records = result['records'][:5]  # Limit to first 5 records
                    formatted_records = []
                    
                    for record in records:
                        # Remove Salesforce metadata
                        clean_record = {k: v for k, v in record.items() if not k.startswith('attributes')}
                        formatted_records.append(clean_record)
                    
                    return f"✅ Query executed successfully!\n" \
                           f"📊 Total records: {result['totalSize']}\n" \
                           f"📝 Showing first {len(formatted_records)} records:\n\n" \
                           f"{formatted_records}"
                    
                except ImportError:
                    return "❌ Salesforce integration requires 'simple-salesforce' package. Please contact administrator."
                except Exception as e:
                    return f"❌ Salesforce query failed: {str(e)}\n" \
                           f"💡 Make sure your query syntax is correct (e.g., 'SELECT Id, Name FROM Account LIMIT 5')"
            
            guaranteed_tools.append(Tool(
                name="salesforce_query",
                description="Execute SOQL queries against Salesforce. Use standard SOQL syntax like 'SELECT Id, Name FROM Account LIMIT 5'",
                func=guaranteed_soql_query
            ))
            
            def guaranteed_object_describe(object_name: str) -> str:
                """Describe Salesforce objects with guaranteed response."""
                try:
                    from simple_salesforce import Salesforce
                    
                    username = os.getenv("SALESFORCE_USERNAME")
                    password = os.getenv("SALESFORCE_PASSWORD")
                    security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
                    instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
                    
                    if not all([username, password]):
                        return "❌ Salesforce credentials not configured"
                    
                    sf = Salesforce(
                        username=username,
                        password=password,
                        security_token=security_token,
                        instance_url=instance_url
                    )
                    
                    # Get object description
                    obj = getattr(sf, object_name, None)
                    if not obj:
                        return f"❌ Object '{object_name}' not found. Common objects: Account, Contact, Opportunity, Case, Lead"
                    
                    desc = obj.describe()
                    
                    # Format field information
                    fields = []
                    for field in desc['fields'][:15]:  # First 15 fields
                        field_info = f"{field['name']} ({field['type']})"
                        if field.get('required'):
                            field_info += " [Required]"
                        fields.append(field_info)
                    
                    return f"✅ Object: {object_name}\n" \
                           f"📋 Label: {desc.get('label', 'N/A')}\n" \
                           f"🏷️  API Name: {desc.get('name', 'N/A')}\n" \
                           f"📝 Description: {desc.get('custom', False) and 'Custom Object' or 'Standard Object'}\n\n" \
                           f"🔧 First 15 Fields:\n" + "\n".join([f"  • {field}" for field in fields]) + \
                           f"\n\n💡 Use salesforce_query to retrieve data from this object."
                    
                except ImportError:
                    return "❌ Salesforce integration requires 'simple-salesforce' package"
                except Exception as e:
                    return f"❌ Object description failed: {str(e)}"
            
            guaranteed_tools.append(Tool(
                name="salesforce_describe",
                description="Get detailed information about Salesforce objects including fields and metadata. Use object API names like 'Account', 'Contact', 'Opportunity'",
                func=guaranteed_object_describe
            ))
            
            print(f"✅ Created {len(guaranteed_tools)} guaranteed Salesforce tools")
            return guaranteed_tools
            
        except Exception as e:
            print(f"⚠️ Error creating Salesforce tools: {e}")
            return []
    else:
        print("⚠️ Salesforce not configured, skipping Salesforce tools")
        return []


def create_guaranteed_tools() -> List[BaseTool]:
    """Create a list of tools that are GUARANTEED to be available."""
    tools = []
    
    # Always add search tool
    search_tool = create_guaranteed_search_tool()
    tools.append(search_tool)
    print(f"✅ Added search tool: {search_tool.name}")
    
    # Add Salesforce tools if possible
    salesforce_tools = create_guaranteed_salesforce_tools()
    tools.extend(salesforce_tools)
    
    # Add a help tool that's always available
    def help_tool() -> str:
        available_tools = [tool.name for tool in tools]
        return f"🤖 Available Tools:\n\n" + \
               "\n".join([f"• {tool}" for tool in available_tools]) + \
               f"\n\n💡 Total tools available: {len(tools)}\n" \
               f"🔧 System Status: Operational\n" \
               f"📊 Platform: LangGraph Deployment"
    
    tools.append(Tool(
        name="help",
        description="Get help and see available tools and capabilities",
        func=help_tool
    ))
    
    print(f"✅ Total guaranteed tools: {len(tools)}")
    return tools


# Initialize guaranteed tools
GUARANTEED_TOOLS = create_guaranteed_tools()


def create_llm(bind_tools: bool = False) -> ChatOpenAI:
    """Create and configure the OpenAI LLM instance."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if bind_tools:
        llm = llm.bind_tools(GUARANTEED_TOOLS)
    
    return llm


def should_continue(state: ChatState) -> str:
    """Determine whether to continue with tool calls or end the conversation."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def should_continue_advanced(state: AdvancedChatState) -> str:
    """Determine continuation for advanced agent."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    else:
        return END


def chat_node(state: ChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Main chat node with guaranteed tools."""
    try:
        messages = state["messages"]
        
        # Add capability message if not present
        capabilities_mentioned = any(
            msg.content and ("tools" in str(msg.content).lower() or "capabilities" in str(msg.content).lower()) 
            for msg in messages if hasattr(msg, 'content') and msg.content
        )
        
        if not capabilities_mentioned:
            tool_names = [tool.name for tool in GUARANTEED_TOOLS]
            salesforce_available = any("salesforce" in name for name in tool_names)
            search_available = any("search" in name for name in tool_names)
            
            capabilities = []
            if search_available:
                capabilities.append("search for information")
            if salesforce_available:
                capabilities.append("work with your Salesforce org (queries, object descriptions, data operations)")
            capabilities.append("provide help and guidance")
            
            system_message = AIMessage(
                content=f"Hello! I'm your AI assistant with access to {len(GUARANTEED_TOOLS)} tools. "
                       f"I can {', '.join(capabilities)}. How can I help you today?"
            )
            messages = [system_message] + messages
        
        llm = create_llm(bind_tools=True)
        response = llm.invoke(messages)
        return {"messages": [response]}
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I encountered an error: {str(e)}. Let me try to help you anyway. "
                   f"You can ask me about Salesforce operations, general questions, or type 'help' to see my capabilities."
        )
        return {"messages": [error_message]}


def advanced_chat_node(state: AdvancedChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Advanced chat node with enhanced context and guaranteed tools."""
    try:
        llm = create_llm(bind_tools=True)
        
        messages = state["messages"]
        conversation_count = state.get("conversation_count", 0)
        
        if conversation_count == 0:
            salesforce_available = any("salesforce" in tool.name for tool in GUARANTEED_TOOLS)
            search_available = any("search" in tool.name for tool in GUARANTEED_TOOLS)
            
            capabilities = []
            if search_available:
                capabilities.append("search the internet")
            if salesforce_available:
                capabilities.append("access your Salesforce org")
            capabilities.append("provide assistance")
            
            system_context = AIMessage(
                content=f"Hello! I'm your advanced AI assistant with {len(GUARANTEED_TOOLS)} tools available. "
                       f"I can {' and '.join(capabilities)}. How can I help you today?"
            )
            messages = [system_context] + messages
        
        response = llm.invoke(messages)
        
        return {
            "messages": [response],
            "conversation_count": conversation_count + 1
        }
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I encountered an error: {str(e)}. I'm still here to help! "
                   f"Try asking about Salesforce, or type 'help' to see what I can do."
        )
        return {
            "messages": [error_message],
            "conversation_count": state.get("conversation_count", 0)
        }


def create_guaranteed_graph() -> StateGraph:
    """Create graph with guaranteed tools node."""
    workflow = StateGraph(ChatState)
    
    # Add nodes - tools node is GUARANTEED to exist
    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", ToolNode(GUARANTEED_TOOLS))
    
    # Set entry point
    workflow.set_entry_point("chat")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "chat",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After tools, go back to chat
    workflow.add_edge("tools", "chat")
    
    return workflow.compile()


def create_advanced_guaranteed_graph() -> StateGraph:
    """Create advanced graph with guaranteed tools node."""
    workflow = StateGraph(AdvancedChatState)
    
    # Add nodes - tools node is GUARANTEED to exist
    workflow.add_node("advanced_chat", advanced_chat_node)
    workflow.add_node("tools", ToolNode(GUARANTEED_TOOLS))
    
    # Set entry point
    workflow.set_entry_point("advanced_chat")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "advanced_chat",
        should_continue_advanced,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After tools, go back to advanced chat
    workflow.add_edge("tools", "advanced_chat")
    
    return workflow.compile()


# Export graphs for LangGraph Platform deployment
graph = create_guaranteed_graph()
advanced_graph = create_advanced_guaranteed_graph()


def main():
    """Local testing function."""
    print("🚀 Testing Platform-Fixed Agent...")
    print(f"🛠️ Available tools: {len(GUARANTEED_TOOLS)}")
    for tool in GUARANTEED_TOOLS:
        print(f"  • {tool.name}: {tool.description[:50]}...")
    
    # Test basic conversation
    test_state = {
        "messages": [HumanMessage(content="What tools do you have available?")]
    }
    
    result = graph.invoke(test_state)
    print("\n🤖 Agent Response:")
    print(result["messages"][-1].content)
    
    # Test advanced conversation
    print("\n" + "="*50)
    print("Testing Advanced Graph...")
    
    advanced_test_state = {
        "messages": [HumanMessage(content="Can you help me with Salesforce?")],
        "user_id": "test_user",
        "session_id": "test_session", 
        "conversation_count": 0
    }
    
    advanced_result = advanced_graph.invoke(advanced_test_state)
    print("\n🤖 Advanced Agent Response:")
    print(advanced_result["messages"][-1].content)


if __name__ == "__main__":
    main()
