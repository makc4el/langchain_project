"""
CORRECTLY FIXED Dynamic Salesforce Tools

This implements the PROPER architecture:
- MCP Server defines tools
- AI Agent discovers tools dynamically  
- No tool duplication in AI agent
- Single source of truth: MCP server
"""

import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.tools import Tool, StructuredTool
from langchain_core.pydantic_v1 import BaseModel, Field

from mcp_client import mcp_client


# Pydantic schemas for structured tools
class DMLInput(BaseModel):
    """Input schema for DML operations (insert, update, delete)"""
    operation: str = Field(description="DML operation: 'insert', 'update', or 'delete'")
    objectName: str = Field(description="Salesforce object name (e.g., 'Lead', 'Account', 'Contact')")
    records: List[Dict[str, Any]] = Field(description="List of records to process")

class QueryInput(BaseModel):
    """Input schema for SOQL queries"""
    query: str = Field(description="SOQL query string")

class SearchInput(BaseModel):
    """Input schema for Salesforce search"""
    searchTerm: str = Field(description="Search term to find across Salesforce objects")

class DescribeInput(BaseModel):
    """Input schema for describe operations"""
    objectName: str = Field(description="Salesforce object name to describe")

class FieldManagementInput(BaseModel):
    """Input schema for field management operations"""
    operation: str = Field(description="Operation: 'create' or 'update'")
    objectName: str = Field(description="Salesforce object name")
    fieldName: str = Field(description="Field name (without __c suffix)")
    type: Optional[str] = Field(None, description="Field type (Text, Number, Date, etc.)")
    label: Optional[str] = Field(None, description="Field label")
    required: Optional[bool] = Field(None, description="Whether field is required")
    unique: Optional[bool] = Field(None, description="Whether field is unique")
    length: Optional[int] = Field(None, description="Field length for text fields")
    description: Optional[str] = Field(None, description="Field description")


class ProperDynamicToolManager:
    """Properly implemented dynamic tool discovery"""
    
    def __init__(self):
        self._tools_cache: Dict[str, Any] = {}  # Can hold both Tool and StructuredTool
    
    async def discover_and_create_tools(self) -> List[Any]:  # Returns both Tool and StructuredTool
        """
        Discover tools from MCP server and create LangChain tools
        
        This is the CORRECT approach - single source of truth is MCP server
        """
        try:
            # Step 1: Discover tools from MCP server (no credentials needed for this)
            mcp_tools = await mcp_client.list_tools()
            langchain_tools = []
            
            for tool_schema in mcp_tools:
                if not isinstance(tool_schema, dict):
                    continue
                    
                tool_name = tool_schema.get('name')
                tool_description = tool_schema.get('description', '')
                
                if not tool_name:
                    continue
                
                # Create dynamic LangChain tool that calls MCP directly
                langchain_tool = self._create_langchain_tool(tool_name, tool_description)
                langchain_tools.append(langchain_tool)
                self._tools_cache[tool_name] = langchain_tool
            
            return langchain_tools
            
        except Exception as e:
            print(f"Dynamic tool discovery failed: {e}")
            return []
    
    def _get_input_schema(self, tool_name: str):
        """Get the appropriate input schema for a tool"""
        tool_schemas = {
            'dml': DMLInput,
            'salesforce_dml_records': DMLInput,  # Legacy name support
            'query': QueryInput,
            'salesforce_query': QueryInput,
            'search': SearchInput,
            'search_all': SearchInput,
            'salesforce_search': SearchInput,
            'describe': DescribeInput,
            'salesforce_describe': DescribeInput,
            'salesforce_manage_field': FieldManagementInput,
            'manage_field': FieldManagementInput
        }
        return tool_schemas.get(tool_name)

    def _create_langchain_tool(self, tool_name: str, tool_description: str):
        """Create a LangChain StructuredTool that calls MCP directly"""
        
        def tool_function(**kwargs) -> str:
            """Function that calls MCP server directly"""
            
            # Check credentials first
            if not mcp_client.credentials:
                return (
                    "❌ Salesforce credentials not set. Please set credentials using:\n"
                    "mcp_client.set_credentials('instance_url', auth_code='your_code')\n"
                    "Get fresh OAuth code from your Salesforce org."
                )
            
            # Call MCP tool directly (this is the RIGHT way)
            try:
                # Use asyncio to call the async MCP function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        mcp_client.call_tool(tool_name, kwargs)
                    )
                finally:
                    loop.close()
                
                # Parse MCP response
                if isinstance(result, dict):
                    if result.get('isError'):
                        error_content = result.get('content', [])
                        if error_content and isinstance(error_content[0], dict):
                            error_msg = error_content[0].get('text', 'Unknown error')
                            if "expired authorization code" in error_msg.lower():
                                return "❌ OAuth code expired. Get fresh code from Salesforce."
                            return f"❌ {error_msg}"
                        return f"❌ Tool execution failed"
                    
                    # Success - parse response
                    result_data = result.get("result", {})
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
                    
                    return "✅ Operation completed successfully"
                
                return str(result)
                
            except Exception as e:
                error_msg = str(e)
                if "expired authorization code" in error_msg.lower():
                    return "❌ OAuth code expired. Get fresh code from Salesforce."
                return f"❌ Error: {error_msg}"
        
        # Try to get structured schema for this tool
        input_schema = self._get_input_schema(tool_name)
        
        if input_schema:
            # Create StructuredTool with proper input schema
            return StructuredTool.from_function(
                func=tool_function,
                name=tool_name,
                description=tool_description,
                args_schema=input_schema
            )
        else:
            # Fallback to simple Tool for unknown tools
            return Tool(
                name=tool_name,
                description=tool_description,
                func=tool_function
            )


# Global instance
proper_tool_manager = ProperDynamicToolManager()


async def get_all_salesforce_tools_properly():
    """
    Get all Salesforce tools using CORRECT architecture
    
    - Discovers from MCP server (single source of truth)
    - No tool duplication in AI agent
    - Calls MCP tools directly
    """
    return await proper_tool_manager.discover_and_create_tools()


# Simple credential helper (this is OK to have in AI agent)
def set_salesforce_credentials_helper(instance_url: str, auth_code: str):
    """Helper to set credentials - this is just a wrapper, not a tool"""
    try:
        mcp_client.set_credentials(instance_url, auth_code=auth_code)
        print(f"✅ Credentials set for: {mcp_client.get_current_instance_url()}")
        return True
    except Exception as e:
        print(f"❌ Failed to set credentials: {e}")
        return False


__all__ = [
    'get_all_salesforce_tools_properly',
    'set_salesforce_credentials_helper',
    'proper_tool_manager'
]
