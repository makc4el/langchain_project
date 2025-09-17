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
from salesforce_tools import get_all_salesforce_tools

class ChatState(TypedDict):
    """State for the chat agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    salesforce_instance_url: Optional[str]
    salesforce_access_token: Optional[str]
    salesforce_auth_code: Optional[str]
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

# Get Salesforce tools
salesforce_tools = get_all_salesforce_tools()


def extract_salesforce_credentials(message_content: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract Salesforce credentials from user message
    
    Returns:
        tuple: (instance_url, access_token, auth_code)
    """
    instance_url = None
    access_token = None
    auth_code = None
    
    # Look for instance URL patterns - Updated to handle various Salesforce domains
    instance_patterns = [
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
    
    # Look for access token patterns - Updated to handle underscores, equals signs, and other characters
    token_patterns = [
        r"access.*?token.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"accessToken.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)", 
        r"token.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
    ]
    
    for pattern in token_patterns:
        match = re.search(pattern, message_content, re.IGNORECASE)
        if match:
            token = match.group(1)
            # More flexible token validation - just check minimum length
            if len(token) > 15:
                access_token = token
                break
    
    # Look for auth code patterns (OAuth flow)
    auth_code_patterns = [
        r"auth.*?code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"authCode.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"authorization.*?code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
        r"code.*?[:\s]+([A-Za-z0-9\.\!\-_=+/]+)",
    ]
    
    for pattern in auth_code_patterns:
        match = re.search(pattern, message_content, re.IGNORECASE)
        if match:
            code = match.group(1)
            # Auth codes are typically shorter than access tokens
            if len(code) > 10 and not access_token:  # Only use auth code if no access token
                auth_code = code
                break
    
    logger.info(f"Extracted credentials - instanceUrl: {instance_url}, accessToken present: {bool(access_token)}, authCode present: {bool(auth_code)}")
    return instance_url, access_token, auth_code


def needs_salesforce_credentials(message_content: str) -> bool:
    """Check if user is asking about Salesforce functionality"""
    salesforce_keywords = [
        'salesforce', 'soql', 'account', 'contact', 'opportunity', 'lead',
        'case', 'query salesforce', 'salesforce data', 'crm', 'sfdc'
    ]
    
    content_lower = message_content.lower()
    return any(keyword in content_lower for keyword in salesforce_keywords)


def setup_salesforce_connection(instance_url: str, access_token: Optional[str] = None, auth_code: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """Setup MCP client with Salesforce credentials
    
    Returns:
        tuple: (success, current_access_token) - current_access_token may be updated after OAuth exchange
    """
    try:
        mcp_client.set_credentials(instance_url, access_token, auth_code)
        # Return the current access token (which may be updated after OAuth exchange)
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
        tools_to_bind = [search_tool]
        if include_salesforce:
            tools_to_bind.extend(salesforce_tools)
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
        salesforce_auth_code = state.get("salesforce_auth_code")
        
        updates = {}
        
        # FIRST: If this is the very first interaction and we don't have stored credentials, ask for them
        if len(messages) == 1 and last_message and not salesforce_authenticated and not (salesforce_instance_url and salesforce_access_token):
            response = AIMessage(
                content="🔐 Hello! I'm your Salesforce AI Assistant. Before we can begin, I need your Salesforce credentials to connect to your org.\n\n"
                       "Please provide your credentials in one of these formats:\n\n"
                       "**Option 1 - Direct Access Token:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "accessToken: your_access_token_here\n\n"
                       "**Option 2 - OAuth Authorization Code:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "authCode: your_auth_code_here\n\n"
                       "You can get credentials from:\n"
                       "• Setup → Apps → App Manager → New Connected App\n"
                       "• Or through Salesforce OAuth flow\n"
                       "• Or use Salesforce CLI: `sf org display --verbose`\n\n"
                       "Once connected, I'll be able to help you with all your Salesforce needs!"
            )
            return {"messages": [response], **updates}
        
        # FIRST.5: If we have stored credentials but aren't authenticated, try to reuse them
        if not salesforce_authenticated and salesforce_instance_url and salesforce_access_token:
            logger.info(f"Attempting to reuse stored credentials for {salesforce_instance_url}")
            success, current_token = setup_salesforce_connection(salesforce_instance_url, salesforce_access_token, None)
            if success:
                salesforce_authenticated = True
                updates["salesforce_authenticated"] = True
                # Update token if it changed
                if current_token and current_token != salesforce_access_token:
                    updates["salesforce_access_token"] = current_token
                logger.info("Successfully reused stored credentials")
            else:
                logger.warning("Stored credentials failed, will ask for new ones")
                # Clear failed credentials
                updates["salesforce_authenticated"] = False
                updates["salesforce_access_token"] = None
                updates["salesforce_auth_code"] = None
        
        # SECOND: Check if user provided Salesforce credentials
        if last_message and hasattr(last_message, 'content'):
            instance_url, access_token, auth_code = extract_salesforce_credentials(str(last_message.content))
            
            if instance_url or access_token or auth_code:
                # Update credentials
                if instance_url:
                    salesforce_instance_url = instance_url
                    updates["salesforce_instance_url"] = instance_url
                if access_token:
                    salesforce_access_token = access_token
                    updates["salesforce_access_token"] = access_token
                if auth_code:
                    salesforce_auth_code = auth_code
                    updates["salesforce_auth_code"] = auth_code
                
                # Try to authenticate if we have instance URL and either token or code
                if salesforce_instance_url and (salesforce_access_token or salesforce_auth_code):
                    success, current_token = setup_salesforce_connection(salesforce_instance_url, salesforce_access_token, salesforce_auth_code)
                    if success:
                        salesforce_authenticated = True
                        updates["salesforce_authenticated"] = True
                        
                        # Store the current access token (may be updated after OAuth exchange)
                        if current_token:
                            salesforce_access_token = current_token
                            updates["salesforce_access_token"] = current_token
                            # Clear auth code since we now have the access token
                            if salesforce_auth_code:
                                updates["salesforce_auth_code"] = None
                        
                        auth_method = "access token" if salesforce_access_token else "authorization code"
                        if salesforce_auth_code and current_token:
                            auth_method = "authorization code (now exchanged for access token)"
                        
                        response = AIMessage(
                            content=f"✅ Perfect! I've successfully connected to your Salesforce org at {salesforce_instance_url} using your {auth_method}.\n\n"
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
                                   "• accessToken is valid and not expired (if using access token)\n"
                                   "• authCode is valid and not expired (if using OAuth flow)\n\n"
                                   "Please try again with the correct credentials."
                        )
                        return {"messages": [response], **updates}
        
        # THIRD: Block all conversation if not authenticated
        if not salesforce_authenticated:
            response = AIMessage(
                content="🔒 I need your Salesforce credentials before we can continue. Please provide them in one of these formats:\n\n"
                       "**Option 1 - Direct Access Token:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "accessToken: your_access_token_here\n\n"
                       "**Option 2 - OAuth Authorization Code:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "authCode: your_auth_code_here\n\n"
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
    # Include both search and Salesforce tools in the ToolNode
    all_tools = [search_tool] + salesforce_tools
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
        salesforce_auth_code = state.get("salesforce_auth_code")
        
        updates = {"conversation_count": conversation_count + 1}
        
        # FIRST: If this is the very first interaction, always ask for credentials
        if conversation_count == 0 and last_message and not salesforce_authenticated:
            response = AIMessage(
                content="🔐 Hello! I'm your Advanced Salesforce AI Assistant with session management and enhanced capabilities.\n\n"
                       "Before we begin our conversation, I need your Salesforce credentials to connect to your org:\n\n"
                       "Please provide your credentials in one of these formats:\n\n"
                       "**Option 1 - Direct Access Token:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "accessToken: your_access_token_here\n\n"
                       "**Option 2 - OAuth Authorization Code:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "authCode: your_auth_code_here\n\n"
                       "You can obtain credentials from:\n"
                       "• Setup → Apps → App Manager → New Connected App\n"
                       "• Or through Salesforce OAuth flow\n"
                       "• Or use Salesforce CLI: `sf org display --verbose`\n\n"
                       "Once authenticated, I'll provide comprehensive Salesforce assistance with session tracking!"
            )
            return {"messages": [response], **updates}
        
        # SECOND: Check if user provided Salesforce credentials
        if last_message and hasattr(last_message, 'content'):
            instance_url, access_token, auth_code = extract_salesforce_credentials(str(last_message.content))
            
            if instance_url or access_token or auth_code:
                # Update credentials
                if instance_url:
                    salesforce_instance_url = instance_url
                    updates["salesforce_instance_url"] = instance_url
                if access_token:
                    salesforce_access_token = access_token
                    updates["salesforce_access_token"] = access_token
                if auth_code:
                    salesforce_auth_code = auth_code
                    updates["salesforce_auth_code"] = auth_code
                
                # Try to authenticate if we have instance URL and either token or code
                if salesforce_instance_url and (salesforce_access_token or salesforce_auth_code):
                    success, current_token = setup_salesforce_connection(salesforce_instance_url, salesforce_access_token, salesforce_auth_code)
                    if success:
                        salesforce_authenticated = True
                        updates["salesforce_authenticated"] = True
                        
                        # Store the current access token (may be updated after OAuth exchange)
                        if current_token:
                            salesforce_access_token = current_token
                            updates["salesforce_access_token"] = current_token
                            # Clear auth code since we now have the access token
                            if salesforce_auth_code:
                                updates["salesforce_auth_code"] = None
                        
                        auth_method = "access token" if salesforce_access_token else "authorization code"
                        if salesforce_auth_code and current_token:
                            auth_method = "authorization code (now exchanged for access token)"
                        
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
                    else:
                        response = AIMessage(
                            content="❌ Connection to Salesforce failed. Please verify your credentials:\n\n"
                                   "• instanceUrl format: https://yourorg.my.salesforce.com\n"
                                   "• accessToken is valid and not expired (if using access token)\n"
                                   "• authCode is valid and not expired (if using OAuth flow)\n"
                                   "• Your user has appropriate permissions\n\n"
                                   "Please try again with correct credentials."
                        )
                        return {"messages": [response], **updates}
        
        # THIRD: Block all conversation if not authenticated
        if not salesforce_authenticated:
            response = AIMessage(
                content="🔒 **Authentication Required**\n\n"
                       "I cannot proceed without valid Salesforce credentials. Please provide in one of these formats:\n\n"
                       "**Option 1 - Direct Access Token:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "accessToken: your_access_token_here\n\n"
                       "**Option 2 - OAuth Authorization Code:**\n"
                       "instanceUrl: https://yourorg.my.salesforce.com\n"
                       "authCode: your_auth_code_here\n\n"
                       "All advanced features require proper Salesforce authentication."
            )
            return {"messages": [response], **updates}
        
        # FOURTH: Only if authenticated, proceed with advanced conversation
        # Create LLM with full Salesforce capabilities (since user is authenticated)
        llm = create_llm(bind_tools=True, include_salesforce=True)
        response = llm.invoke(messages)
        
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
    # Include both search and Salesforce tools in the ToolNode
    all_tools = [search_tool] + salesforce_tools
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
        "salesforce_access_token": None,
        "salesforce_auth_code": None
    }
    
    result = graph.invoke(test_state)
    print("Agent Response:")
    print(result["messages"][-1].content)
    
    print("\n" + "="*60)
    print("2. Testing Credential Provision (Mock credentials)...")
    
    # Test credential provision (access token)
    cred_test_state = {
        "messages": [
            HumanMessage(content="Hello! Can you help me with Salesforce?"),
            HumanMessage(content="instanceUrl: https://test.my.salesforce.com\naccessToken: mock_token_123456789012345678901234567890")
        ],
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None,
        "salesforce_auth_code": None
    }
    
    try:
        cred_result = graph.invoke(cred_test_state)
        print("Credential Response:")
        print(cred_result["messages"][-1].content)
        print(f"Authentication Status: {cred_result.get('salesforce_authenticated', False)}")
    except Exception as e:
        print(f"Note: Mock credentials failed connection (expected): {e}")
    
    print("\n" + "="*60)
    print("2b. Testing OAuth Code Provision (Mock auth code)...")
    
    # Test auth code provision
    auth_code_test_state = {
        "messages": [
            HumanMessage(content="Hello! Can you help me with Salesforce?"),
            HumanMessage(content="instanceUrl: https://test.my.salesforce.com\nauthCode: mock_auth_code_12345678901234567890")
        ],
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None,
        "salesforce_auth_code": None
    }
    
    try:
        auth_result = graph.invoke(auth_code_test_state)
        print("Auth Code Response:")
        print(auth_result["messages"][-1].content)
        print(f"Authentication Status: {auth_result.get('salesforce_authenticated', False)}")
    except Exception as e:
        print(f"Note: Mock auth code failed connection (expected): {e}")
    
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
        "salesforce_access_token": None,
        "salesforce_auth_code": None
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
        "salesforce_access_token": None,
        "salesforce_auth_code": None
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
    print("• Agent now requires Salesforce credentials on first interaction")
    print("• Blocks all conversation until valid credentials provided") 
    print("• Supports both access tokens and OAuth authorization codes")
    print("• MCP server URL configurable via MCP_SALESFORCE_SERVER_URL env var")
    print("• Integrates with MCP server (default: mcp-server-salesforce-production.up.railway.app)")
    print("• Provides comprehensive Salesforce tools once authenticated")
    print("• Supports both simple and advanced conversation modes")
    
    print("\n🔗 To test with real credentials:")
    print("**Option 1 - Access Token:**")
    print("1. Get your Salesforce instanceUrl (e.g., https://yourorg.my.salesforce.com)")
    print("2. Get a valid access token from Salesforce (sf org display --verbose)")
    print("3. Provide: instanceUrl: <url> and accessToken: <token>")
    print("\n**Option 2 - OAuth Code:**")
    print("1. Get your Salesforce instanceUrl")
    print("2. Get an OAuth authorization code from Salesforce OAuth flow")
    print("3. Provide: instanceUrl: <url> and authCode: <code>")


if __name__ == "__main__":
    main()