"""
Dynamic Salesforce Tool Discovery
Automatically discovers and creates LangChain tools from the MCP server
"""

import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.tools import Tool
import json

from mcp_client import mcp_client


class DynamicSalesforceToolManager:
    """Dynamically discovers and creates LangChain tools from MCP server"""
    
    def __init__(self):
        self._tools_cache: Dict[str, Tool] = {}
        self._mcp_tools_schema: List[Dict[str, Any]] = []
    
    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover all available tools from MCP server"""
        try:
            tools = await mcp_client.list_tools()
            self._mcp_tools_schema = tools
            return tools
        except Exception as e:
            print(f"Failed to discover MCP tools: {e}")
            return []
    
    def _create_tool_function(self, tool_name: str, tool_schema: Dict[str, Any]):
        """Create a dynamic function for an MCP tool"""
        
        async def dynamic_tool_function(**kwargs) -> str:
            """Dynamically generated tool function"""
            try:
                if not mcp_client.credentials:
                    return "❌ Salesforce credentials not set. Please provide your credentials first."
                
                # Call the MCP tool directly with the provided arguments
                result = await mcp_client.call_tool(tool_name, kwargs)
                
                if isinstance(result, dict):
                    if result.get('isError'):
                        error_content = result.get('content', [])
                        if error_content and isinstance(error_content[0], dict):
                            return f"❌ {error_content[0].get('text', 'Unknown error')}"
                        return f"❌ Tool execution failed: {result}"
                    
                    # Handle successful response - improved parsing
                    result_data = result.get("result", {})
                    
                    # Handle case where result might be a list
                    if isinstance(result_data, list):
                        content = result_data
                    else:
                        content = result_data.get("content", [])
                    
                    if content and len(content) > 0:
                        first_item = content[0]
                        if isinstance(first_item, dict):
                            message = first_item.get("text", "Success")
                            return f"✅ {message}"
                        else:
                            return f"✅ {first_item}"
                    
                    # For tools that return simple success without content
                    if 'result' in result:
                        return "✅ Tool executed successfully"
                    
                    return "✅ Operation completed"
                
                return str(result)
                
            except Exception as e:
                return f"❌ Error executing tool: {str(e)}"
        
        # Convert async function to sync for LangChain compatibility
        def sync_tool_function(**kwargs) -> str:
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(dynamic_tool_function(**kwargs))
            except RuntimeError:
                return asyncio.run(dynamic_tool_function(**kwargs))
        
        return sync_tool_function
    
    async def create_langchain_tools(self) -> List[Tool]:
        """Create LangChain tools dynamically from MCP server"""
        
        # Discover available tools
        mcp_tools = await self.discover_tools()
        langchain_tools = []
        
        for tool_schema in mcp_tools:
            if not isinstance(tool_schema, dict):
                continue
                
            tool_name = tool_schema.get('name')
            tool_description = tool_schema.get('description', '')
            
            if not tool_name:
                continue
            
            try:
                # Create the dynamic function
                tool_function = self._create_tool_function(tool_name, tool_schema)
                
                # Create LangChain tool
                langchain_tool = Tool(
                    name=tool_name,
                    description=tool_description,
                    func=tool_function
                )
                
                langchain_tools.append(langchain_tool)
                self._tools_cache[tool_name] = langchain_tool
                
            except Exception as e:
                print(f"❌ Failed to create tool {tool_name}: {e}")
        
        return langchain_tools
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool by name"""
        return self._tools_cache.get(tool_name)
    
    def list_available_tools(self) -> List[str]:
        """List names of all available tools"""
        return list(self._tools_cache.keys())


# Global instance
dynamic_tool_manager = DynamicSalesforceToolManager()


async def get_all_salesforce_tools():
    """
    Get all Salesforce tools dynamically from MCP server
    
    This replaces the old static tool definitions with dynamic discovery.
    All tools are automatically discovered from the MCP server without
    needing manual definitions.
    """
    return await dynamic_tool_manager.create_langchain_tools()


def get_all_salesforce_tools_sync():
    """
    Synchronous wrapper for getting all Salesforce tools
    Used when async context is not available
    """
    try:
        # Try to get the existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context, can't use run_until_complete
            raise RuntimeError("Cannot call sync wrapper from async context")
        else:
            return loop.run_until_complete(get_all_salesforce_tools())
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(get_all_salesforce_tools())


# Backwards compatibility for existing code
async def create_salesforce_manage_field_tool_async() -> Tool:
    """
    Get the field management tool specifically (async version)
    
    This maintains backwards compatibility while using the dynamic system
    """
    tools = await get_all_salesforce_tools()
    
    # Find the field management tool
    for tool in tools:
        if tool.name == 'salesforce_manage_field':
            return tool
    
    # Fallback - create a simple tool that explains the issue
    def no_tool_found(**kwargs) -> str:
        return "❌ Field management tool not found. Please ensure the MCP server is running and accessible."
    
    return Tool(
        name="salesforce_manage_field",
        description="Field management tool (dynamic discovery failed)",
        func=no_tool_found
    )


def create_salesforce_manage_field_tool() -> Tool:
    """
    Get the field management tool specifically (sync version)
    
    This maintains backwards compatibility while using the dynamic system
    """
    try:
        # Check if we're in an async context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in async context - return a tool that handles this properly
            def async_context_tool(**kwargs) -> str:
                return "❌ This tool requires async context. Use create_salesforce_manage_field_tool_async() instead."
            
            return Tool(
                name="salesforce_manage_field",
                description="Field management tool (requires async context)",
                func=async_context_tool
            )
        else:
            # We can safely run async code
            tools = loop.run_until_complete(get_all_salesforce_tools())
    except RuntimeError:
        # No event loop - create one
        tools = asyncio.run(get_all_salesforce_tools())
    
    # Find the field management tool
    for tool in tools:
        if tool.name == 'salesforce_manage_field':
            return tool
    
    # Fallback - create a simple tool that explains the issue
    def no_tool_found(**kwargs) -> str:
        return "❌ Field management tool not found. Please ensure the MCP server is running and accessible."
    
    return Tool(
        name="salesforce_manage_field",
        description="Field management tool (dynamic discovery failed)",
        func=no_tool_found
    )


# Export the main function for backwards compatibility
__all__ = [
    'get_all_salesforce_tools',
    'get_all_salesforce_tools_sync', 
    'create_salesforce_manage_field_tool',
    'dynamic_tool_manager'
]
