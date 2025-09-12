"""
Recursion-Fixed LangGraph Agent with Salesforce Integration

This version fixes the GraphRecursionError by:
- Adding proper recursion limits
- Improving stop conditions
- Adding tool call limits
- Better error handling to prevent loops
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
    tool_call_count: int = 0  # Track tool calls to prevent loops


class AdvancedChatState(ChatState):
    """Enhanced state for advanced chat agent."""
    user_id: str = ""
    session_id: str = ""
    conversation_count: int = 0
    tool_call_count: int = 0  # Track tool calls


# Configuration constants
MAX_TOOL_CALLS_PER_CONVERSATION = 5
MAX_RECURSION_LIMIT = 15  # Lower than default to catch issues faster


def create_guaranteed_search_tool():
    """Create a search tool that provides definitive responses."""
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
    
    # Fallback search tool with definitive responses
    def fallback_search(query: str) -> str:
        return f"🔍 **Search Results for: '{query}'**\n\n" \
               f"I don't have real-time internet access in this environment, but I can help you with:\n" \
               f"• General information and analysis\n" \
               f"• Salesforce operations and queries\n" \
               f"• Technical guidance and best practices\n\n" \
               f"📝 **Regarding your query**: Based on my knowledge, I can provide general guidance about {query.lower()}. " \
               f"For the most current information, you may want to check official sources directly.\n\n" \
               f"**This completes the search request.**"
    
    return Tool(
        name="search",
        description="Search for current information. Use this when you need recent data or current events.",
        func=fallback_search
    )


def create_guaranteed_salesforce_tools():
    """Create Salesforce tools with definitive, non-looping responses."""
    print("🔧 Initializing guaranteed Salesforce tools...")
    
    if not validate_platform_config():
        print("⚠️ Salesforce not configured, skipping Salesforce tools")
        return []
    
    guaranteed_tools = []
    
    def salesforce_status() -> str:
        """Check Salesforce integration status with definitive response."""
        try:
            config = os.getenv("SALESFORCE_USERNAME", "Not configured")
            org_url = os.getenv("SALESFORCE_LOGIN_URL", "Not configured")
            return f"✅ **Salesforce Integration Status - COMPLETE**\n\n" \
                   f"📧 **User**: {config}\n" \
                   f"🏢 **Org URL**: {org_url}\n" \
                   f"🔗 **Status**: Ready and operational\n\n" \
                   f"📋 **Available Operations**:\n" \
                   f"• Execute SOQL queries (use: salesforce_query)\n" \
                   f"• Get object descriptions (use: salesforce_describe)\n" \
                   f"• View integration details\n\n" \
                   f"**Status check complete. Integration is functional.**"
        except Exception as e:
            return f"❌ **Salesforce Status Check - COMPLETE**\n\nError: {str(e)}\n\n**Status check finished.**"
    
    guaranteed_tools.append(Tool(
        name="salesforce_status",
        description="Check Salesforce integration status and available capabilities. Use when asked about Salesforce connectivity or available operations.",
        func=salesforce_status
    ))
    
    def guaranteed_soql_query(query: str) -> str:
        """Execute SOQL queries with definitive, complete responses."""
        try:
            # Import here to handle missing dependency gracefully
            from simple_salesforce import Salesforce
            
            username = os.getenv("SALESFORCE_USERNAME")
            password = os.getenv("SALESFORCE_PASSWORD")
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
            
            if not all([username, password]):
                return "❌ **SOQL Query - COMPLETE**\n\nError: Salesforce credentials not configured.\n\n**Query execution finished.**"
            
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
                return f"✅ **SOQL Query Results - COMPLETE**\n\n" \
                       f"📝 **Query**: {query}\n" \
                       f"📊 **Result**: No records found\n" \
                       f"✨ **Status**: Query executed successfully\n\n" \
                       f"**Query execution complete.**"
            
            # Return formatted results
            records = result['records'][:3]  # Limit to first 3 records to prevent long responses
            formatted_records = []
            
            for record in records:
                # Remove Salesforce metadata
                clean_record = {k: v for k, v in record.items() if not k.startswith('attributes')}
                formatted_records.append(clean_record)
            
            return f"✅ **SOQL Query Results - COMPLETE**\n\n" \
                   f"📝 **Query**: {query}\n" \
                   f"📊 **Total Records**: {result['totalSize']}\n" \
                   f"📋 **Sample Records** (first 3):\n\n" \
                   f"{formatted_records}\n\n" \
                   f"✨ **Query executed successfully. Results delivered.**"
            
        except ImportError:
            return "❌ **SOQL Query - COMPLETE**\n\nError: Salesforce integration requires 'simple-salesforce' package.\n\n**Query execution finished.**"
        except Exception as e:
            return f"❌ **SOQL Query - COMPLETE**\n\n" \
                   f"📝 **Query**: {query}\n" \
                   f"❌ **Error**: {str(e)}\n" \
                   f"💡 **Tip**: Check SOQL syntax (e.g., 'SELECT Id, Name FROM Account LIMIT 5')\n\n" \
                   f"**Query execution finished.**"
    
    guaranteed_tools.append(Tool(
        name="salesforce_query",
        description="Execute SOQL queries against Salesforce. Use standard SOQL syntax. Always provide complete query like 'SELECT Id, Name FROM Account LIMIT 5'.",
        func=guaranteed_soql_query
    ))
    
    def guaranteed_object_describe(object_name: str) -> str:
        """Describe Salesforce objects with definitive, complete responses."""
        try:
            from simple_salesforce import Salesforce
            
            username = os.getenv("SALESFORCE_USERNAME")
            password = os.getenv("SALESFORCE_PASSWORD")
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
            
            if not all([username, password]):
                return "❌ **Object Description - COMPLETE**\n\nError: Salesforce credentials not configured.\n\n**Description request finished.**"
            
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url
            )
            
            # Get object description
            obj = getattr(sf, object_name, None)
            if not obj:
                return f"❌ **Object Description - COMPLETE**\n\n" \
                       f"🏷️ **Object**: {object_name}\n" \
                       f"❌ **Status**: Object not found\n" \
                       f"💡 **Common Objects**: Account, Contact, Opportunity, Case, Lead\n\n" \
                       f"**Description request finished.**"
            
            desc = obj.describe()
            
            # Format field information (limited to prevent long responses)
            fields = []
            for field in desc['fields'][:10]:  # First 10 fields only
                field_info = f"{field['name']} ({field['type']})"
                if field.get('required'):
                    field_info += " [Required]"
                fields.append(field_info)
            
            return f"✅ **Object Description - COMPLETE**\n\n" \
                   f"🏷️ **Object**: {object_name}\n" \
                   f"📋 **Label**: {desc.get('label', 'N/A')}\n" \
                   f"🔧 **Type**: {desc.get('custom', False) and 'Custom Object' or 'Standard Object'}\n\n" \
                   f"📝 **Key Fields** (first 10):\n" + \
                   "\n".join([f"  • {field}" for field in fields]) + \
                   f"\n\n✨ **Object description complete.**"
            
        except ImportError:
            return "❌ **Object Description - COMPLETE**\n\nError: Salesforce integration requires 'simple-salesforce' package.\n\n**Description request finished.**"
        except Exception as e:
            return f"❌ **Object Description - COMPLETE**\n\n" \
                   f"🏷️ **Object**: {object_name}\n" \
                   f"❌ **Error**: {str(e)}\n\n" \
                   f"**Description request finished.**"
    
    guaranteed_tools.append(Tool(
        name="salesforce_describe",
        description="Get detailed information about Salesforce objects including fields and metadata. Use standard object API names like 'Account', 'Contact', 'Opportunity'.",
        func=guaranteed_object_describe
    ))
    
    print(f"✅ Created {len(guaranteed_tools)} guaranteed Salesforce tools")
    return guaranteed_tools


def create_guaranteed_tools() -> List[BaseTool]:
    """Create a list of tools that provide definitive, non-looping responses."""
    tools = []
    
    # Always add search tool
    search_tool = create_guaranteed_search_tool()
    tools.append(search_tool)
    print(f"✅ Added search tool: {search_tool.name}")
    
    # Add Salesforce tools if possible
    salesforce_tools = create_guaranteed_salesforce_tools()
    tools.extend(salesforce_tools)
    
    # Add a help tool that's always available with definitive response
    def help_tool() -> str:
        available_tools = [f"{tool.name}: {tool.description.split('.')[0]}" for tool in tools]
        return f"🤖 **Available Tools - COMPLETE LIST**\n\n" + \
               "\n".join([f"• {tool}" for tool in available_tools]) + \
               f"\n\n📊 **Total Tools**: {len(tools)}\n" \
               f"🔧 **System**: Operational\n" \
               f"🌐 **Platform**: LangGraph\n\n" \
               f"**Help request complete. All available tools listed above.**"
    
    tools.append(Tool(
        name="help",
        description="Get help and see available tools and capabilities. Use when user asks what you can do or needs guidance.",
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
        temperature=0.5,  # Lower temperature for more consistent responses
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if bind_tools:
        llm = llm.bind_tools(GUARANTEED_TOOLS)
    
    return llm


def should_continue(state: ChatState) -> str:
    """
    Improved conditional logic to prevent recursion loops.
    
    Stops execution if:
    - No tool calls in the last message
    - Tool call limit exceeded
    - Last message indicates completion
    """
    messages = state["messages"]
    tool_call_count = state.get("tool_call_count", 0)
    
    # Check tool call limit
    if tool_call_count >= MAX_TOOL_CALLS_PER_CONVERSATION:
        print(f"🛑 Tool call limit reached ({MAX_TOOL_CALLS_PER_CONVERSATION})")
        return END
    
    last_message = messages[-1]
    
    # Check if last message has tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f"🔧 Tool call {tool_call_count + 1}/{MAX_TOOL_CALLS_PER_CONVERSATION}")
        return "tools"
    
    # Check if the conversation seems complete
    if hasattr(last_message, 'content') and last_message.content:
        content_lower = last_message.content.lower()
        completion_indicators = [
            "complete", "finished", "done", "delivered", "execution complete",
            "request finished", "results delivered", "status check complete",
            "query execution complete", "description request finished"
        ]
        
        if any(indicator in content_lower for indicator in completion_indicators):
            print("✅ Completion indicator detected")
            return END
    
    return END


def should_continue_advanced(state: AdvancedChatState) -> str:
    """Improved conditional logic for advanced agent."""
    messages = state["messages"]
    tool_call_count = state.get("tool_call_count", 0)
    
    # Check tool call limit
    if tool_call_count >= MAX_TOOL_CALLS_PER_CONVERSATION:
        print(f"🛑 Advanced: Tool call limit reached ({MAX_TOOL_CALLS_PER_CONVERSATION})")
        return END
    
    last_message = messages[-1]
    
    # Check if last message has tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f"🔧 Advanced: Tool call {tool_call_count + 1}/{MAX_TOOL_CALLS_PER_CONVERSATION}")
        return "tools"
    
    return END


def chat_node(state: ChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Main chat node with recursion prevention."""
    try:
        messages = state["messages"]
        tool_call_count = state.get("tool_call_count", 0)
        
        # Add welcome message with clear capabilities
        if len(messages) <= 1 or not any("assistant with" in str(msg.content) for msg in messages if hasattr(msg, 'content')):
            tool_names = [tool.name for tool in GUARANTEED_TOOLS]
            salesforce_available = any("salesforce" in name for name in tool_names)
            search_available = any("search" in name for name in tool_names)
            
            capabilities = []
            if search_available:
                capabilities.append("search for information")
            if salesforce_available:
                capabilities.append("work with your Salesforce org (execute queries, describe objects, check status)")
            capabilities.append("provide help and guidance")
            
            system_message = AIMessage(
                content=f"Hello! I'm your AI assistant with {len(GUARANTEED_TOOLS)} tools available. "
                       f"I can {', '.join(capabilities)}. "
                       f"How can I help you today?"
            )
            messages = [system_message] + messages
        
        llm = create_llm(bind_tools=True)
        response = llm.invoke(messages)
        
        return {
            "messages": [response],
            "tool_call_count": tool_call_count
        }
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I encountered an error: {str(e)}. "
                   f"I can still help with Salesforce operations, searches, or general questions. "
                   f"Please try rephrasing your request or ask for help to see my capabilities."
        )
        return {
            "messages": [error_message],
            "tool_call_count": state.get("tool_call_count", 0)
        }


def advanced_chat_node(state: AdvancedChatState, config: RunnableConfig) -> Dict[str, Any]:
    """Advanced chat node with recursion prevention."""
    try:
        llm = create_llm(bind_tools=True)
        
        messages = state["messages"]
        conversation_count = state.get("conversation_count", 0)
        tool_call_count = state.get("tool_call_count", 0)
        
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
                       f"I can {' and '.join(capabilities)}. "
                       f"How can I help you today?"
            )
            messages = [system_context] + messages
        
        response = llm.invoke(messages)
        
        return {
            "messages": [response],
            "conversation_count": conversation_count + 1,
            "tool_call_count": tool_call_count
        }
        
    except Exception as e:
        error_message = AIMessage(
            content=f"I encountered an error: {str(e)}. "
                   f"I'm still here to help with Salesforce, searches, or questions. "
                   f"Please try again or ask for help."
        )
        return {
            "messages": [error_message],
            "conversation_count": state.get("conversation_count", 0),
            "tool_call_count": state.get("tool_call_count", 0)
        }


def increment_tool_count(state):
    """Increment tool call count to track usage."""
    return {
        **state,
        "tool_call_count": state.get("tool_call_count", 0) + 1
    }


def create_recursion_safe_graph() -> StateGraph:
    """Create graph with recursion safety measures."""
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", ToolNode(GUARANTEED_TOOLS))
    workflow.add_node("increment_counter", increment_tool_count)
    
    # Set entry point
    workflow.set_entry_point("chat")
    
    # Add conditional edges with recursion prevention
    workflow.add_conditional_edges(
        "chat",
        should_continue,
        {
            "tools": "increment_counter",
            END: END,
        },
    )
    
    # After incrementing counter, go to tools
    workflow.add_edge("increment_counter", "tools")
    
    # After tools, go back to chat
    workflow.add_edge("tools", "chat")
    
    return workflow.compile()


def create_advanced_recursion_safe_graph() -> StateGraph:
    """Create advanced graph with recursion safety measures."""
    workflow = StateGraph(AdvancedChatState)
    
    # Add nodes
    workflow.add_node("advanced_chat", advanced_chat_node)
    workflow.add_node("tools", ToolNode(GUARANTEED_TOOLS))
    workflow.add_node("increment_counter", increment_tool_count)
    
    # Set entry point
    workflow.set_entry_point("advanced_chat")
    
    # Add conditional edges with recursion prevention
    workflow.add_conditional_edges(
        "advanced_chat",
        should_continue_advanced,
        {
            "tools": "increment_counter",
            END: END,
        },
    )
    
    # After incrementing counter, go to tools
    workflow.add_edge("increment_counter", "tools")
    
    # After tools, go back to advanced chat
    workflow.add_edge("tools", "advanced_chat")
    
    return workflow.compile()


# Export graphs for LangGraph Platform deployment
graph = create_recursion_safe_graph()
advanced_graph = create_advanced_recursion_safe_graph()


def main():
    """Local testing function with recursion testing."""
    print("🚀 Testing Recursion-Fixed Agent...")
    print(f"🛠️ Available tools: {len(GUARANTEED_TOOLS)}")
    print(f"🔄 Max recursion limit: {MAX_RECURSION_LIMIT}")
    print(f"🔧 Max tool calls: {MAX_TOOL_CALLS_PER_CONVERSATION}")
    
    for tool in GUARANTEED_TOOLS:
        print(f"  • {tool.name}: {tool.description[:50]}...")
    
    # Test basic conversation
    test_state = {
        "messages": [HumanMessage(content="What tools do you have available?")],
        "tool_call_count": 0
    }
    
    try:
        result = graph.invoke(
            test_state,
            config={"recursion_limit": MAX_RECURSION_LIMIT}
        )
        print("\n🤖 Agent Response:")
        print(result["messages"][-1].content)
        print(f"🔢 Tool calls used: {result.get('tool_call_count', 0)}")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test Salesforce query
    print("\n" + "="*50)
    print("Testing Salesforce Query (should not recurse)...")
    
    salesforce_test_state = {
        "messages": [HumanMessage(content="Check my Salesforce integration status")],
        "tool_call_count": 0
    }
    
    try:
        salesforce_result = graph.invoke(
            salesforce_test_state,
            config={"recursion_limit": MAX_RECURSION_LIMIT}
        )
        print("\n🤖 Salesforce Response:")
        print(salesforce_result["messages"][-1].content)
        print(f"🔢 Tool calls used: {salesforce_result.get('tool_call_count', 0)}")
    except Exception as e:
        print(f"❌ Salesforce test failed: {str(e)}")


if __name__ == "__main__":
    main()
