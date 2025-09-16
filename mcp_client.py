"""
MCP Client for Salesforce Integration

This module provides an HTTP client to interact with the deployed MCP Salesforce server
at mcp-server-salesforce-production.up.railway.app
"""

import json
import httpx
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class SalesforceCredentials(BaseModel):
    """Salesforce credentials for MCP server authentication"""
    instanceUrl: str
    accessToken: str


class MCPSalesforceClient:
    """HTTP client for the deployed MCP Salesforce server"""
    
    def __init__(self, server_url: str = "https://mcp-server-salesforce-production.up.railway.app"):
        self.server_url = server_url.rstrip('/')
        self.credentials: Optional[SalesforceCredentials] = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def set_credentials(self, instance_url: str, access_token: str):
        """Set Salesforce credentials for API calls"""
        self.credentials = SalesforceCredentials(
            instanceUrl=instance_url,
            accessToken=access_token
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers including Salesforce credentials"""
        if not self.credentials:
            raise ValueError("Salesforce credentials not set. Call set_credentials() first.")
        
        return {
            "Content-Type": "application/json",
            "X-Salesforce-Credentials": json.dumps(self.credentials.dict())
        }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        try:
            payload = {
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await self.client.post(
                f"{self.server_url}/mcp",
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code != 200:
                raise Exception(f"MCP server error: {response.status_code} - {response.text}")
            
            return response.json()
        
        except Exception as e:
            raise Exception(f"Failed to call MCP tool '{tool_name}': {str(e)}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from the MCP server"""
        try:
            payload = {
                "method": "tools/list"
            }
            
            response = await self.client.post(
                f"{self.server_url}/mcp",
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code != 200:
                raise Exception(f"MCP server error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("result", {}).get("tools", [])
        
        except Exception as e:
            raise Exception(f"Failed to list MCP tools: {str(e)}")
    
    async def query_soql(self, query: str) -> Dict[str, Any]:
        """Execute a SOQL query"""
        return await self.call_tool("query", {"query": query})
    
    async def search_objects(self, search_term: str) -> Dict[str, Any]:
        """Search across Salesforce objects"""
        return await self.call_tool("search", {"searchTerm": search_term})
    
    async def describe_object(self, object_name: str) -> Dict[str, Any]:
        """Describe a Salesforce object"""
        return await self.call_tool("describe", {"objectName": object_name})
    
    async def create_record(self, object_name: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record"""
        return await self.call_tool("dml", {
            "operation": "insert",
            "objectName": object_name,
            "records": [fields]
        })
    
    async def update_record(self, object_name: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record"""
        return await self.call_tool("dml", {
            "operation": "update",
            "objectName": object_name,
            "records": [{**fields, "Id": record_id}]
        })
    
    async def delete_record(self, object_name: str, record_id: str) -> Dict[str, Any]:
        """Delete a record"""
        return await self.call_tool("dml", {
            "operation": "delete",
            "objectName": object_name,
            "records": [{"Id": record_id}]
        })
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global MCP client instance
mcp_client = MCPSalesforceClient()
