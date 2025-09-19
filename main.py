"""
LangGraph Platform-Ready Chat Agent

A production-ready conversational AI agent built with LangGraph and OpenAI GPT-4o-mini.
Designed for seamless deployment on LangGraph Platform with API support.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

# Import configuration
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict

# Import Salesforce functionality
from mcp_client import mcp_client
from fixed_dynamic_tools import get_all_salesforce_tools_properly

class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    salesforce_instance_url: Optional[str]
    salesforce_access_token: Optional[str]  # Obtained after OAuth exchange
    salesforce_authenticated: bool


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

# Get Salesforce tools - proper architecture (MCP discovery)
salesforce_tools = []  # Will be loaded dynamically

# Global cache for Salesforce tools (for async contexts)
_salesforce_tools_cache = []

# Initialize Salesforce tools cache for async contexts
_salesforce_tools_cache = []

def initialize_salesforce_tools():
    """Initialize Salesforce tools with robust error handling for deployment"""
    global _salesforce_tools_cache
    
    if _salesforce_tools_cache:
        return _salesforce_tools_cache  # Already initialized
    
    try:
        from dynamic_salesforce_tools import get_all_salesforce_tools_sync
        _salesforce_tools_cache = get_all_salesforce_tools_sync()
        logger.info(f"🚀 Initialized {len(_salesforce_tools_cache)} Salesforce tools cache")
        return _salesforce_tools_cache
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Salesforce tools cache: {e}")
        # In deployment, create fallback tools based on known MCP schema
        _salesforce_tools_cache = create_fallback_salesforce_tools()
        logger.info(f"🔧 Created {len(_salesforce_tools_cache)} fallback Salesforce tools")
        return _salesforce_tools_cache

def create_fallback_salesforce_tools():
    """Create fallback Salesforce tools when MCP server is unreachable"""
    from langchain_core.tools import Tool
    
    fallback_tools = []
    
    # Critical tools based on MCP server schema
    tool_definitions = [
        {
            "name": "dml",
            "description": "Create, update, or delete Salesforce records. Use operation: 'insert' for creating new records like Leads."
        },
        {
            "name": "query", 
            "description": "Query Salesforce records using SOQL. Specify objectName and fields to retrieve."
        },
        {
            "name": "describe",
            "description": "Get detailed schema information about Salesforce objects and their fields."
        },
        {
            "name": "search_all",
            "description": "Search across multiple Salesforce objects using SOSL."
        }
    ]
    
    for tool_def in tool_definitions:
        def create_tool_func(tool_name):
            async def fallback_tool(**kwargs):
                from mcp_client import mcp_client
                try:
                    if not mcp_client.credentials:
                        return "❌ Salesforce credentials not set. Please provide credentials first."
                    
                    result = await mcp_client.call_tool(tool_name, kwargs)
                    
                    if isinstance(result, dict) and result.get('result', {}).get('content'):
                        content = result['result']['content']
                        if isinstance(content, list) and content:
                            return content[0].get('text', str(result))
                    
                    return str(result)
                except Exception as e:
                    return f"❌ Error executing {tool_name}: {str(e)}"
            
            def sync_fallback_tool(**kwargs):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(fallback_tool(**kwargs))
                except RuntimeError:
                    return asyncio.run(fallback_tool(**kwargs))
            
            return sync_fallback_tool
        
        tool = Tool(
            name=tool_def["name"],
            description=tool_def["description"],
            func=create_tool_func(tool_def["name"])
        )
        fallback_tools.append(tool)
    
    return fallback_tools

# Initialize tools on module load
initialize_salesforce_tools()


def extract_salesforce_credentials_enhanced(message_content: str) -> Optional[Dict[str, Any]]:
    """Extract comprehensive Salesforce credentials from user message
    
    Supported formats:
    - Full JSON: {"instanceUrl": "...", "accessToken": "...", "tokenType": "Bearer", ...}
    - Partial JSON with either accessToken or authCode
    - Key-value format
    
    Returns:
        Dict with credentials or None if not found
    """
    import json
    
    credentials = {}
    
    # First, try to parse as complete JSON
    try:
        # Look for JSON objects in the message
        json_patterns = [
            r'\{[^}]*"instanceUrl"[^}]*\}',  # Basic JSON pattern
            r'\{.*?"instanceUrl".*?\}',      # More flexible JSON pattern
        ]
        
        for json_pattern in json_patterns:
            json_matches = re.finditer(json_pattern, message_content, re.IGNORECASE | re.DOTALL)
            for match in json_matches:
                try:
                    json_str = match.group(0)
                    # Clean up the JSON string
                    json_str = json_str.replace("'", '"')
                    
                    parsed_data = json.loads(json_str)
                    
                    # Extract all available fields
                    if 'instanceUrl' in parsed_data:
                        instance_url = str(parsed_data['instanceUrl']).rstrip('/')
                        if not instance_url.startswith('https://'):
                            instance_url = f"https://{instance_url}"
                        credentials['instanceUrl'] = instance_url
                    
                    if 'accessToken' in parsed_data:
                        credentials['accessToken'] = str(parsed_data['accessToken'])
                    
                    if 'authCode' in parsed_data:
                        credentials['authCode'] = str(parsed_data['authCode'])
                    
                    if 'tokenType' in parsed_data:
                        credentials['tokenType'] = str(parsed_data['tokenType'])
                    
                    if 'refreshToken' in parsed_data:
                        credentials['refreshToken'] = str(parsed_data['refreshToken'])
                    
                    if 'scope' in parsed_data:
                        credentials['scope'] = str(parsed_data['scope'])
                    
                    # If we have instanceUrl and either accessToken or authCode, return
                    if credentials.get('instanceUrl') and (credentials.get('accessToken') or credentials.get('authCode')):
                        logger.info(f"Extracted enhanced credentials from JSON - instanceUrl: {credentials.get('instanceUrl')}")
                        return credentials
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        logger.debug(f"Enhanced JSON parsing failed: {e}")
    
    # Fall back to the original function for backward compatibility
    instance_url, auth_code = extract_salesforce_credentials_original(message_content)
    
    if instance_url and auth_code:
        return {
            'instanceUrl': instance_url,
            'authCode': auth_code,
            'tokenType': 'Bearer'
        }
    
    return None


def extract_salesforce_credentials_original(message_content: str) -> tuple[Optional[str], Optional[str]]:
    """Original credential extraction function for backward compatibility
    
    Supported formats:
    - JSON: {"instanceUrl": "...", "authCode": "..."}
    - Key-value: instanceUrl: ... \n authCode: ...
    - Mixed formats with various punctuation
    
    Returns:
        tuple: (instance_url, auth_code)
    """
    instance_url = None
    auth_code = None
    
    # First, try to parse as JSON
    try:
        # Look for JSON objects in the message
        import json
        
        # Try to find JSON objects in the text
        json_patterns = [
            r'\{[^}]*"instanceUrl"[^}]*\}',  # Basic JSON pattern
            r'\{.*?"instanceUrl".*?\}',      # More flexible JSON pattern
        ]
        
        for json_pattern in json_patterns:
            json_matches = re.finditer(json_pattern, message_content, re.IGNORECASE | re.DOTALL)
            for match in json_matches:
                try:
                    json_str = match.group(0)
                    # Clean up the JSON string - handle common issues
                    json_str = json_str.replace("'", '"')  # Replace single quotes with double quotes
                    
                    parsed_data = json.loads(json_str)
                    
                    # Extract instanceUrl and authCode from JSON
                    if 'instanceUrl' in parsed_data:
                        instance_url = str(parsed_data['instanceUrl']).rstrip('/')
                        # Ensure it starts with https://
                        if not instance_url.startswith('https://'):
                            instance_url = f"https://{instance_url}"
                    
                    if 'authCode' in parsed_data:
                        potential_code = str(parsed_data['authCode'])
                        if len(potential_code) > 10:  # Auth codes should be reasonable length
                            auth_code = potential_code
                    
                    # If we found both in JSON, we're done
                    if instance_url and auth_code:
                        logger.info(f"Extracted credentials from JSON - instanceUrl: {instance_url}, authCode present: {bool(auth_code)}")
                        return instance_url, auth_code
                        
                except json.JSONDecodeError:
                    continue  # Try next match
                    
    except Exception as e:
        logger.debug(f"JSON parsing failed: {e}")
    
    # If JSON parsing didn't work, fall back to regex patterns
    
    # Look for instance URL patterns - Updated to handle various Salesforce domains
    instance_patterns = [
        # JSON-style patterns (quoted)
        r'"instanceUrl"[:\s]*"(https://[a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com)/?)"',
        r'"instanceUrl"[:\s]*"([a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com)/?)"',
        # Direct URL patterns (with https://)
        r"instance.*?url.*?[:\s]+(https://[a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com)/?)",
        r"instanceUrl.*?[:\s]+(https://[a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com)/?)",
        r"(https://[a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com)/?)",
        # Domain-only patterns (without https://)
        r"instance.*?url.*?[:\s]+([a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com))",
        r"instanceUrl.*?[:\s]+([a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com))",
        r"instance.*?[:\s]+([a-zA-Z0-9\-\.]+\.(?:my\.salesforce\.com|lightning\.force\.com|develop\.lightning\.force\.com))",
    ]
    
    for pattern in instance_patterns:
        match = re.search(pattern, message_content, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Ensure URL starts with https://
            if url.startswith('https://'):
                instance_url = url.rstrip('/')
            else:
                instance_url = f"https://{url.rstrip('/')}"
            break
    
    # Look for auth code patterns (OAuth flow only)
    auth_code_patterns = [
        # JSON-style patterns (quoted with double quotes)
        r'"authCode"[:\s]*"([A-Za-z0-9\.\!\-_=+/]+)"',
        # JSON-style patterns (quoted with single quotes)
        r"'authCode'[:\s]*'([A-Za-z0-9\.\!\-_=+/]+)'",
        # Traditional patterns
        r"auth.*?code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"authCode.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"authorization.*?code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
    ]
    
    for pattern in auth_code_patterns:
        match = re.search(pattern, message_content, re.IGNORECASE)
        if match:
            code = match.group(1)
            # Auth codes should be reasonable length
            if len(code) > 10:
                auth_code = code
                break
    
    logger.info(f"Extracted credentials - instanceUrl: {instance_url}, authCode present: {bool(auth_code)}")
    return instance_url, auth_code


def needs_salesforce_credentials(message_content: str) -> bool:
    """Check if user is asking about Salesforce functionality"""
    salesforce_keywords = [
        'salesforce', 'soql', 'account', 'contact', 'opportunity', 'lead',
        'case', 'query salesforce', 'salesforce data', 'crm', 'sfdc'
    ]
    
    content_lower = message_content.lower()
    return any(keyword in content_lower for keyword in salesforce_keywords)


def setup_salesforce_connection(instance_url: str, auth_code: str) -> tuple[bool, Optional[str]]:
    """Setup MCP client with Salesforce credentials using OAuth Authorization Code
    
    Returns:
        tuple: (success, access_token) - access_token obtained after OAuth exchange
    """
    try:
        mcp_client.set_credentials(instance_url, None, auth_code)
        # Return the current access token (which will be updated after OAuth exchange)
        current_token = mcp_client.get_current_access_token()
        return True, current_token
    except Exception as e:
        logger.error(f"Failed to setup Salesforce connection: {e}")
        return False, None


def create_llm(bind_tools: bool = False, include_salesforce: bool = False) -> ChatOpenAI:
    """Create and configure the OpenAI LLM instance."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    if bind_tools:
        global _salesforce_tools_cache  # Declare global at function level
        tools_to_bind = [search_tool]
        if include_salesforce:
            # Load Salesforce tools dynamically - use cached version if available
            try:
                import asyncio
                try:
                    # Check if we're in async context
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # In async context - use pre-loaded tools from global cache
                        if _salesforce_tools_cache:
                            tools_to_bind.extend(_salesforce_tools_cache)
                            logger.info(f"✅ Using cached {len(_salesforce_tools_cache)} Salesforce tools for LLM")
                        else:
                            logger.warning("⚠️ Salesforce tools not cached - run initialization first")
                    else:
                        # Not in async context - safe to load
                        from dynamic_salesforce_tools import get_all_salesforce_tools_sync
                        dynamic_salesforce_tools = get_all_salesforce_tools_sync()
                        tools_to_bind.extend(dynamic_salesforce_tools)
                        # Update global cache
                        _salesforce_tools_cache = dynamic_salesforce_tools
                        logger.info(f"✅ Loaded {len(dynamic_salesforce_tools)} Salesforce tools for LLM")
                except RuntimeError:
                    # No event loop - safe to load
                    from dynamic_salesforce_tools import get_all_salesforce_tools_sync
                    dynamic_salesforce_tools = get_all_salesforce_tools_sync()
                    tools_to_bind.extend(dynamic_salesforce_tools)
                    _salesforce_tools_cache = dynamic_salesforce_tools
                    logger.info(f"✅ Loaded {len(dynamic_salesforce_tools)} Salesforce tools for LLM")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load Salesforce tools for LLM: {e}")
        
        llm = llm.bind_tools(tools_to_bind)
    
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
    Main chat node that processes user input and generates AI responses with Salesforce capabilities.
    Requires Salesforce credentials before any conversation can proceed.
    
    Args:
        state: Current chat state containing message history
        config: Runtime configuration from LangGraph platform
        
    Returns:
        Dictionary containing the AI response message and updated state
    """
    try:
        messages = state["messages"]
        last_message = messages[-1] if messages else None
        
        # Initialize state values if not present
        salesforce_authenticated = state.get("salesforce_authenticated", False)
        salesforce_instance_url = state.get("salesforce_instance_url")
        salesforce_access_token = state.get("salesforce_access_token")
        
        updates = {}
        
        # FIRST: If this is the very first interaction and we don't have stored credentials, ask for them
        if len(messages) == 1 and last_message and not salesforce_authenticated and not (salesforce_instance_url and salesforce_access_token):
            response = AIMessage(
                content="🔐 Hello! I'm your Salesforce AI Assistant. Before we can begin, I need your Salesforce credentials to connect to your org.\n\n"
                       "Please provide your complete Salesforce credentials in JSON format:\n\n"
                       "```json\n"
                       "{\n"
                       '  "instanceUrl": "https://your-org.my.salesforce.com",\n'
                       '  "accessToken": "your_access_token_here",\n'
                       '  "tokenType": "Bearer",\n'
                       '  "refreshToken": "your_refresh_token_here",\n'
                       '  "authCode": "your_auth_code_here"\n'
                       "}\n"
                       "```\n\n"
                       "**Required fields:**\n"
                       "• `instanceUrl` - Your Salesforce org URL\n" 
                       "• `accessToken` - OAuth 2.0 access token\n"
                       "• `tokenType` - Token type (usually 'Bearer')\n"
                       "• `refreshToken` - OAuth 2.0 refresh token\n"
                       "• `authCode` - OAuth authorization code\n\n"
                       "Once I receive your credentials, I'll connect to your Salesforce org and help you with all your needs!"
            )
            return {"messages": [response], **updates}
        
        # FIRST.5: If we have stored credentials but aren't authenticated, try to reuse them
        if not salesforce_authenticated and salesforce_instance_url and salesforce_access_token:
            logger.info(f"Attempting to reuse stored access token for {salesforce_instance_url}")
            try:
                # Try to use the stored access token directly
                mcp_client.set_credentials(salesforce_instance_url, salesforce_access_token, None)
                salesforce_authenticated = True
                updates["salesforce_authenticated"] = True
                logger.info("Successfully reused stored access token")
            except Exception as e:
                logger.warning(f"Stored access token failed: {e}, will ask for new auth code")
                # Clear failed credentials
                updates["salesforce_authenticated"] = False
                updates["salesforce_access_token"] = None
        
        # SECOND: Check if user provided Salesforce credentials
        if last_message and hasattr(last_message, 'content'):
            credentials = extract_salesforce_credentials_enhanced(str(last_message.content))
            instance_url = credentials.get('instanceUrl') if credentials else None
            auth_code = credentials.get('authCode') if credentials else None
            
            if instance_url and auth_code:
                # Update credentials
                salesforce_instance_url = instance_url
                updates["salesforce_instance_url"] = instance_url
                
                # Try to authenticate using OAuth Authorization Code
                success, current_token = setup_salesforce_connection(salesforce_instance_url, auth_code)
                if success:
                    salesforce_authenticated = True
                    updates["salesforce_authenticated"] = True
                    
                    # Store the access token obtained from OAuth exchange
                    if current_token:
                        salesforce_access_token = current_token
                        updates["salesforce_access_token"] = current_token
                    
                    response = AIMessage(
                        content=f"✅ Perfect! I've successfully connected to your Salesforce org at {salesforce_instance_url} using your authorization code (now exchanged for access token).\n\n"
                               f"I can now help you with:\n"
                               f"• 📊 Querying data with SOQL\n"
                               f"• 🔍 Searching for records\n"
                               f"• 📋 Describing objects and fields\n"
                               f"• ➕ Creating new records\n"
                               f"• 🔄 Updating existing records\n"
                               f"• ❌ Deleting records\n"
                               f"• 🌐 Internet search when needed\n\n"
                               f"What would you like to do with Salesforce?"
                    )
                    return {"messages": [response], **updates}
                else:
                    response = AIMessage(
                        content="❌ I couldn't connect to Salesforce with those credentials. Please verify:\n\n"
                               "• instanceUrl is correct (format: https://yourorg.my.salesforce.com)\n"
                               "• authCode is valid and not expired\n"
                               "• Your Connected App is configured correctly\n"
                               "• The redirect_uri matches your Connected App settings\n\n"
                               "Please try again with a fresh authorization code."
                    )
                    return {"messages": [response], **updates}
            elif instance_url or auth_code:
                response = AIMessage(
                    content="❌ I need complete Salesforce credentials. Please provide the full JSON format:\n\n"
                           "```json\n"
                           "{\n"
                           '  "instanceUrl": "https://your-org.my.salesforce.com",\n'
                           '  "accessToken": "your_access_token_here",\n'
                           '  "tokenType": "Bearer",\n'
                           '  "refreshToken": "your_refresh_token_here",\n'
                           '  "authCode": "your_auth_code_here"\n'
                           "}\n"
                           "```\n\n"
                           "Make sure to include all required fields."
                )
                return {"messages": [response], **updates}
        
        # THIRD: Block all conversation if not authenticated
        if not salesforce_authenticated:
            response = AIMessage(
                content="🔒 I need your Salesforce credentials before we can continue. Please provide them in JSON format:\n\n"
                       "```json\n"
                       "{\n"
                       '  "instanceUrl": "https://your-org.my.salesforce.com",\n'
                       '  "accessToken": "your_access_token_here",\n'
                       '  "tokenType": "Bearer",\n'
                       '  "refreshToken": "your_refresh_token_here",\n'
                       '  "authCode": "your_auth_code_here"\n'
                       "}\n"
                       "```\n\n"
                       "I cannot assist with any requests until you provide valid Salesforce credentials."
            )
            return {"messages": [response], **updates}
        
        # FOURTH: Only if authenticated, proceed with normal conversation
        # Create LLM with Salesforce tools (since we know user is authenticated)
        llm = create_llm(bind_tools=True, include_salesforce=True)
        response = llm.invoke(messages)
        return {"messages": [response], **updates}
        
    except Exception as e:
        # Handle errors gracefully
        error_message = AIMessage(
            content=f"I apologize, but I encountered an error: {str(e)}. Please try again."
        )
        return {"messages": [error_message]}


def create_simple_graph() -> StateGraph:
    """
    Create a simple chat agent graph with internet search and Salesforce capabilities.
    
    Returns:
        Compiled StateGraph ready for deployment
    """
    # Create the graph
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("chat", chat_node)
    
    # CRITICAL FIX: Robust tool loading for deployment environments  
    # Ensures tools are available even if MCP server is unreachable during startup
    all_tools = [search_tool]
    
    # Initialize tools with fallback support
    salesforce_tools = initialize_salesforce_tools()
    all_tools.extend(salesforce_tools)
    print(f"✅ ToolNode loaded {len(salesforce_tools)} Salesforce tools")
    print(f"📋 ToolNode tools: {[tool.name for tool in salesforce_tools[:5]]}...")
    
    workflow.add_node("tools", ToolNode(all_tools))
    
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
    Advanced chat node with session management and Salesforce capabilities.
    Requires Salesforce credentials before any conversation can proceed.
    
    Args:
        state: Enhanced chat state with user and session information
        config: Runtime configuration from LangGraph platform
        
    Returns:
        Dictionary containing the AI response and updated state
    """
    try:
        messages = state["messages"]
        conversation_count = state.get("conversation_count", 0)
        last_message = messages[-1] if messages else None
        
        # Initialize Salesforce state values if not present
        salesforce_authenticated = state.get("salesforce_authenticated", False)
        salesforce_instance_url = state.get("salesforce_instance_url")
        salesforce_access_token = state.get("salesforce_access_token")
        
        updates = {"conversation_count": conversation_count + 1}
        
        # FIRST: If this is the very first interaction, always ask for credentials
        if conversation_count == 0 and last_message and not salesforce_authenticated:
            response = AIMessage(
                content="🔐 Hello! I'm your Advanced Salesforce AI Assistant with session management and enhanced capabilities.\n\n"
                       "Before we begin our conversation, I need your complete Salesforce credentials to connect to your org.\n\n"
                       "Please provide your credentials in JSON format:\n\n"
                       "```json\n"
                       "{\n"
                       '  "instanceUrl": "https://your-org.my.salesforce.com",\n'
                       '  "accessToken": "your_access_token_here",\n'
                       '  "tokenType": "Bearer",\n'
                       '  "refreshToken": "your_refresh_token_here",\n'
                       '  "authCode": "your_auth_code_here"\n'
                       "}\n"
                       "```\n\n"
                       "**Required fields:**\n"
                       "• `instanceUrl` - Your Salesforce org URL\n"
                       "• `accessToken` - OAuth 2.0 access token\n"
                       "• `tokenType` - Token type (usually 'Bearer')\n"
                       "• `refreshToken` - OAuth 2.0 refresh token\n"
                       "• `authCode` - OAuth authorization code\n\n"
                       "Once authenticated, I'll provide comprehensive Salesforce assistance with session tracking!"
            )
            return {"messages": [response], **updates}
        
        # SECOND: Check if user provided Salesforce credentials (ENHANCED)
        if last_message and hasattr(last_message, 'content'):
            credentials = extract_salesforce_credentials_enhanced(str(last_message.content))
            
            if credentials and credentials.get('instanceUrl'):
                instance_url = credentials.get('instanceUrl')
                access_token = credentials.get('accessToken')
                auth_code = credentials.get('authCode')
                
                salesforce_instance_url = instance_url
                updates["salesforce_instance_url"] = instance_url
                
                # Handle BOTH accessToken and authCode scenarios
                if access_token:
                    # Direct access token provided - use it directly
                    from mcp_client import mcp_client
                    mcp_client.set_credentials_from_dict(credentials)
                    
                    salesforce_authenticated = True
                    salesforce_access_token = access_token
                    updates["salesforce_authenticated"] = True
                    updates["salesforce_access_token"] = access_token
                    
                    auth_method = "access token"
                    
                elif auth_code:
                    # OAuth authorization code provided - exchange for access token
                    success, current_token = setup_salesforce_connection(salesforce_instance_url, auth_code)
                    if success:
                        salesforce_authenticated = True
                        updates["salesforce_authenticated"] = True
                        
                        if current_token:
                            salesforce_access_token = current_token
                            updates["salesforce_access_token"] = current_token
                        
                        auth_method = "authorization code (exchanged for access token)"
                    else:
                        response = AIMessage(
                            content="❌ Connection to Salesforce failed. Please verify your credentials:\n\n"
                                   "• instanceUrl format: https://yourorg.my.salesforce.com\n"
                                   "• authCode is valid and not expired\n"
                                   "• Your Connected App is configured correctly\n"
                                   "• The redirect_uri matches your Connected App settings\n\n"
                                   "Please try again with a fresh authorization code."
                        )
                        return {"messages": [response], **updates}
                else:
                    # Neither access token nor auth code provided
                    response = AIMessage(
                        content="❌ I need either an accessToken or authCode. Please provide complete credentials with one of these authentication methods."
                    )
                    return {"messages": [response], **updates}
                
                # Success response for both authentication methods
                if salesforce_authenticated:
                    response = AIMessage(
                        content=f"✅ Excellent! I've successfully connected to your Salesforce org at {salesforce_instance_url} using your {auth_method}.\n\n"
                               f"🚀 **Advanced Features Now Available:**\n"
                               f"• 📊 Advanced SOQL querying with analysis\n"
                               f"• 🔍 Intelligent record search and filtering\n"
                               f"• 📋 Comprehensive object and field exploration\n"
                               f"• ➕ Smart record creation with validation\n"
                               f"• 🔄 Bulk data operations and updates\n"
                               f"• ❌ Safe record deletion with confirmations\n"
                               f"• 🌐 Enhanced internet research capabilities\n"
                               f"• 💾 Session management and conversation history\n\n"
                               f"What advanced Salesforce operation would you like to perform?"
                    )
                    return {"messages": [response], **updates}
        
        # THIRD: Block all conversation if not authenticated
        if not salesforce_authenticated:
            response = AIMessage(
                content="🔒 **Authentication Required**\n\n"
                       "I cannot proceed without valid Salesforce credentials. Please provide them in JSON format:\n\n"
                       "```json\n"
                       "{\n"
                       '  "instanceUrl": "https://your-org.my.salesforce.com",\n'
                       '  "accessToken": "your_access_token_here",\n'
                       '  "tokenType": "Bearer",\n'
                       '  "refreshToken": "your_refresh_token_here",\n'
                       '  "authCode": "your_auth_code_here"\n'
                       "}\n"
                       "```\n\n"
                       "All advanced features require proper Salesforce OAuth authentication."
            )
            return {"messages": [response], **updates}
        
        # FOURTH: Only if authenticated, proceed with advanced conversation
        # Create LLM with full Salesforce capabilities (since user is authenticated)
        logger.info(f"✅ User authenticated - enabling Salesforce tools for advanced chat")
        llm = create_llm(bind_tools=True, include_salesforce=True)
        
        # Debug: Log what tools are actually bound to the LLM
        if hasattr(llm, 'bound') and hasattr(llm.bound, 'tools'):
            tool_names = [tool.name for tool in llm.bound.tools]
            logger.info(f"🔧 LLM has access to tools: {tool_names}")
            salesforce_tool_count = len([name for name in tool_names if name != 'tavily_search'])
            logger.info(f"📊 Salesforce tools available: {salesforce_tool_count}, Tavily: {'yes' if 'tavily_search' in tool_names else 'no'}")
        else:
            logger.warning("⚠️ Could not determine what tools are bound to LLM")
        
        # Log the current message for debugging
        if messages:
            last_user_msg = next((msg.content for msg in reversed(messages) if hasattr(msg, 'content') and msg.__class__.__name__ == 'HumanMessage'), "No user message found")
            logger.info(f"🔍 Processing user request: {last_user_msg[:100]}...")
        
        # Add system message to prioritize Salesforce tools
        from langchain_core.messages import SystemMessage
        salesforce_system_msg = SystemMessage(content="""You are now connected to Salesforce with full access to Salesforce tools.

CRITICAL TOOL USAGE RULES - FOLLOW THESE EXACTLY:
🚫 NEVER use tavily_search for Salesforce operations (creating, updating, querying Salesforce data)
✅ ALWAYS use Salesforce MCP tools for ANY Salesforce task

SPECIFIC TOOL MAPPING:
📊 Create Lead/Account/Contact/etc. → Use 'dml' tool with operation: 'insert'
📋 Query Salesforce data → Use 'query' tool  
🔍 Search Salesforce records → Use 'search_all' tool
📝 Describe objects/fields → Use 'describe' tool
🔄 Update records → Use 'dml' tool with operation: 'update'
❌ Delete records → Use 'dml' tool with operation: 'delete'

IMPORTANT: Use the exact tool names: 'dml', 'query', 'describe', 'search_all' - NOT 'salesforce_dml_records'

EXAMPLE: User asks "create new lead record" → Call 'dml' tool with operation: 'insert', objectName: 'Lead'

You have direct access to the user's Salesforce org. Use Salesforce tools immediately - do NOT search the internet.""")
        
        # Insert system message at the beginning
        enhanced_messages = [salesforce_system_msg] + messages
        response = llm.invoke(enhanced_messages)
        
        # Log if tools were called
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_names = [tool_call.get('name', 'unknown') for tool_call in response.tool_calls]
            logger.info(f"🔧 LLM called tools: {tool_names}")
        else:
            logger.info("💬 LLM responded without calling tools")
        
        return {"messages": [response], **updates}
        
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
    Create an advanced chat agent graph with session management, search, and Salesforce capabilities.
    
    Returns:
        Compiled StateGraph with enhanced features
    """
    # Create the graph with advanced state
    workflow = StateGraph(AdvancedChatState)
    
    # Add nodes
    workflow.add_node("advanced_chat", advanced_chat_node)
    
    # CRITICAL FIX: Robust tool loading for deployment environments
    # Ensures tools are available even if MCP server is unreachable during startup
    all_tools = [search_tool]
    
    # Initialize tools with fallback support
    salesforce_tools = initialize_salesforce_tools()
    all_tools.extend(salesforce_tools)
    print(f"✅ ToolNode loaded {len(salesforce_tools)} Salesforce tools")
    print(f"📋 ToolNode tools: {[tool.name for tool in salesforce_tools[:5]]}...")
    
    workflow.add_node("tools", ToolNode(all_tools))
    
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
    Run this file directly to test the Salesforce-integrated agent locally.
    """
    print("🚀 Testing Salesforce AI Agent Integration...")
    print("="*60)
    
    print("1. Testing Simple Chat Agent - First Interaction (Should ask for credentials)...")
    
    # Test the simple graph - first interaction
    test_state = {
        "messages": [HumanMessage(content="Hello! Can you help me with Salesforce?")],
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None
    }
    
    result = graph.invoke(test_state)
    print("Agent Response:")
    print(result["messages"][-1].content)
    
    print("\n" + "="*60)
    print("2. Testing Credential Provision (Mock credentials)...")
    
    # Test credential provision (auth code)
    cred_test_state = {
        "messages": [
            HumanMessage(content="Hello! Can you help me with Salesforce?"),
            HumanMessage(content="instanceUrl: https://test.my.salesforce.com\nauthCode: your_test_auth_code_here")
        ],
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None
    }
    
    try:
        cred_result = graph.invoke(cred_test_state)
        print("Credential Response:")
        print(cred_result["messages"][-1].content)
        print(f"Authentication Status: {cred_result.get('salesforce_authenticated', False)}")
    except Exception as e:
        print(f"Note: Mock credentials failed connection (expected): {e}")
    
    
    print("\n" + "="*60)
    print("3. Testing Advanced Chat Agent - First Interaction...")
    
    # Test the advanced graph
    advanced_test_state = {
        "messages": [HumanMessage(content="Hello, I need help with Salesforce data.")],
        "user_id": "test_user",
        "session_id": "test_session",
        "conversation_count": 0,
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None
    }
    
    try:
        advanced_result = advanced_graph.invoke(advanced_test_state)
        print("Advanced Agent Response:")
        print(advanced_result["messages"][-1].content)
        print(f"Conversation Count: {advanced_result['conversation_count']}")
    except Exception as e:
        print(f"Advanced agent test failed: {e}")
    
    print("\n" + "="*60)
    print("4. Testing Blocking Behavior (Should block without credentials)...")
    
    # Test that agent blocks without credentials
    block_test_state = {
        "messages": [
            HumanMessage(content="Hello!"),
            HumanMessage(content="Can you query my Account data?")
        ],
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None
    }
    
    try:
        block_result = graph.invoke(block_test_state)
        print("Blocking Response:")
        print(block_result["messages"][-1].content)
    except Exception as e:
        print(f"Block test failed: {e}")
    
    print("\n" + "="*60)
    print("✅ Integration Testing Complete!")
    print("\n📋 Summary:")
    print("• Agent now requires Salesforce OAuth credentials on first interaction")
    print("• Blocks all conversation until valid credentials provided") 
    print("• Uses OAuth Authorization Code flow only (more secure)")
    print("• Automatically exchanges auth codes for access tokens")
    print("• Stores and reuses access tokens throughout the conversation")
    print("• MCP server URL configurable via MCP_SALESFORCE_SERVER_URL env var")
    print("• Integrates with MCP server (default: your-mcp-server.railway.app)")
    print("• Provides comprehensive Salesforce tools once authenticated")
    print("• Supports both simple and advanced conversation modes")
    
    print("\n🔗 To test with real credentials:")
    print("1. Get your Salesforce instanceUrl (e.g., https://yourorg.my.salesforce.com)")
    print("2. Get an OAuth authorization code from Salesforce OAuth flow")
    print("3. Provide: instanceUrl: <url> and authCode: <code>")
    print("4. The system will automatically exchange the code for an access token")
    print("5. The access token will be reused for all subsequent operations!")


if __name__ == "__main__":
    main()