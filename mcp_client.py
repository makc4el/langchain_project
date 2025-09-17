"""
MCP Client for Salesforce Integration

This module provides an HTTP client to interact with the deployed MCP Salesforce server
"""

import os
import json
import httpx
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

# Import configuration
from config import config

logger = logging.getLogger(__name__)


class SalesforceCredentials(BaseModel):
    """Salesforce credentials for MCP server authentication"""
    instanceUrl: str
    accessToken: Optional[str] = None
    authCode: Optional[str] = None


class MCPSalesforceClient:
    """HTTP client for the deployed MCP Salesforce server with resilience"""
    
    def __init__(self, server_url: Optional[str] = None):
        # Use provided URL, then config, then environment, then fallback
        if server_url:
            self.server_url = server_url.rstrip('/')
        else:
            # Use config first, then fallback to environment variable
            self.server_url = (
                config.MCP_SALESFORCE_SERVER_URL or
                os.getenv('MCP_SALESFORCE_SERVER_URL') or
                'https://mcp-server-salesforce-production.up.railway.app'
            ).rstrip('/')
        
        self.credentials: Optional[SalesforceCredentials] = None
        
        # Enhanced HTTP client configuration for production
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30.0,   # Connection timeout
                read=120.0,     # Read timeout for long operations
                write=30.0,     # Write timeout
                pool=60.0       # Pool timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=300  # 5 minutes
            ),
            headers={
                'User-Agent': 'LangChain-Salesforce-MCP-Client/1.0',
                'Accept': 'application/json',
                'Connection': 'keep-alive'
            },
            follow_redirects=True
        )
        
        self.max_retries = 5  # Increased for production reliability
        self.retry_delay = 2.0
        self.backoff_factor = 1.5  # Exponential backoff
        
        logger.info(f"MCP Client initialized with server URL: {self.server_url}")
        logger.info(f"Client configuration: max_retries={self.max_retries}, timeout=120s")
    
    def set_credentials(self, instance_url: str, access_token: Optional[str] = None, auth_code: Optional[str] = None):
        """Set Salesforce credentials for API calls"""
        if not access_token and not auth_code:
            raise ValueError("Either access_token or auth_code must be provided")
        
        self.credentials = SalesforceCredentials(
            instanceUrl=instance_url,
            accessToken=access_token,
            authCode=auth_code
        )
        logger.info(f"Credentials set for instance: {instance_url}, using {'access token' if access_token else 'auth code'}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers including Salesforce credentials"""
        if not self.credentials:
            raise ValueError("Salesforce credentials not set. Call set_credentials() first.")
        
        return {
            "Content-Type": "application/json",
            "X-Salesforce-Credentials": json.dumps(self.credentials.dict())
        }
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server with enhanced retry logic and error handling"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                payload = {
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    }
                }
                
                logger.info(f"Calling MCP tool '{tool_name}' (attempt {attempt + 1}/{self.max_retries})")
                
                response = await self.client.post(
                    f"{self.server_url}/mcp",
                    json=payload,
                    headers=self._get_headers()
                )
                
                # Enhanced error handling for different status codes
                if response.status_code == 200:
                    logger.info(f"Successfully called MCP tool '{tool_name}'")
                    return response.json()
                elif response.status_code == 401:
                    raise ValueError(f"Authentication failed for MCP server. Check your API key or Salesforce credentials.")
                elif response.status_code == 403:
                    raise ValueError(f"Access forbidden. Check your Salesforce permissions.")
                elif response.status_code == 429:
                    # Rate limited - use exponential backoff
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    raise Exception(f"MCP server error: {response.status_code} - {response.text}")
                else:
                    # Client error - don't retry
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_message = error_json.get('error', error_text)
                    except:
                        error_message = error_text
                    raise ValueError(f"MCP server error: {response.status_code} - {error_message}")
            
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as e:
                last_exception = e
                logger.warning(f"Network error on attempt {attempt + 1} for tool '{tool_name}': {str(e)}")
                
                if attempt < self.max_retries - 1:
                    backoff_delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.info(f"Retrying in {backoff_delay:.1f} seconds...")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    logger.error(f"All attempts failed for tool '{tool_name}' due to network issues")
                    raise Exception(f"Network error: Failed to connect to MCP server after {self.max_retries} attempts: {str(e)}")
            
            except ValueError as e:
                # Don't retry client errors (4xx) or authentication errors
                logger.error(f"Client error for tool '{tool_name}': {str(e)}")
                raise e
            
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for tool '{tool_name}': {str(e)}")
                
                if attempt < self.max_retries - 1:
                    backoff_delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.info(f"Retrying in {backoff_delay:.1f} seconds...")
                    await asyncio.sleep(backoff_delay)
                    continue
                else:
                    logger.error(f"All attempts failed for tool '{tool_name}'")
        
        raise Exception(f"Failed to call MCP tool '{tool_name}' after {self.max_retries} attempts: {str(last_exception)}")
    
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
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the MCP server is healthy and reachable"""
        try:
            response = await self.client.get(
                f"{self.server_url}/health",
                timeout=10.0  # Quick health check timeout
            )
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"MCP server health check passed: {health_data.get('status', 'unknown')}")
                return health_data
            else:
                logger.warning(f"MCP server health check failed: HTTP {response.status_code}")
                return {
                    "status": "unhealthy", 
                    "error": f"HTTP {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"MCP server health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "server_url": self.server_url
            }
    
    async def test_connection(self) -> bool:
        """Test if we can connect to the MCP server"""
        try:
            health = await self.health_check()
            return health.get("status") == "ok"
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        try:
            await self.client.aclose()
            logger.info("MCP client closed successfully")
        except Exception as e:
            logger.warning(f"Error closing MCP client: {str(e)}")


# Global MCP client instance
mcp_client = MCPSalesforceClient()
