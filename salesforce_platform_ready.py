"""
Platform-ready Salesforce MCP integration for LangGraph deployment.

This module provides platform-compatible alternatives for MCP integration,
handling potential Node.js and subprocess restrictions.
"""

import os
import asyncio
import subprocess
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.tools import BaseTool, Tool
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.sessions import StdioConnection, StreamableHttpConnection
from pydantic import BaseModel, Field


class PlatformSalesforceConfig(BaseModel):
    """Platform-ready configuration for Salesforce MCP connection."""
    connection_type: str = Field(default="User_Password")
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    security_token: Optional[str] = Field(default="")
    instance_url: Optional[str] = Field(default="https://login.salesforce.com")
    client_id: Optional[str] = Field(default=None)
    client_secret: Optional[str] = Field(default=None)


class PlatformSalesforceMCPWrapper:
    """
    Platform-ready Salesforce MCP wrapper that handles deployment constraints.
    
    Features:
    - Automatic fallback to manual tool creation if MCP server fails
    - Platform environment detection
    - Error resilience for production deployment
    """
    
    def __init__(self, config: Optional[PlatformSalesforceConfig] = None):
        self.config = config or self._load_config_from_env()
        self.tools: List[BaseTool] = []
        self.is_initialized = False
        self.platform_mode = self._detect_platform_mode()
        
    def _load_config_from_env(self) -> PlatformSalesforceConfig:
        """Load configuration from environment variables."""
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL") or os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
        
        # Also try SALESFORCE_TOKEN (Claude Desktop format)
        security_token = os.getenv("SALESFORCE_SECURITY_TOKEN") or os.getenv("SALESFORCE_TOKEN", "")
        
        return PlatformSalesforceConfig(
            connection_type=os.getenv("SALESFORCE_CONNECTION_TYPE", "User_Password"),
            username=os.getenv("SALESFORCE_USERNAME"),
            password=os.getenv("SALESFORCE_PASSWORD"),
            security_token=security_token,
            instance_url=instance_url,
            client_id=os.getenv("SALESFORCE_CLIENT_ID"),
            client_secret=os.getenv("SALESFORCE_CLIENT_SECRET"),
        )
    
    def _detect_platform_mode(self) -> str:
        """Detect if running on LangGraph platform or locally."""
        # Check for common platform environment indicators
        if os.getenv("LANGGRAPH_ENV") or os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("VERCEL_ENV"):
            return "platform"
        elif not shutil.which("node") and not shutil.which("npx"):
            return "platform_no_nodejs"
        else:
            return "local"
    
    async def _try_mcp_integration(self) -> List[BaseTool]:
        """Attempt to load tools via MCP server."""
        try:
            if self.platform_mode == "platform_no_nodejs":
                print("⚠️  Node.js not available, skipping MCP server approach")
                return []
                
            connection = StdioConnection(
                transport="stdio",
                command="npx",
                args=["@tsmztech/mcp-server-salesforce"],
                env=self._get_env_vars(),
                cwd=Path.cwd()
            )
            
            tools = await load_mcp_tools(session=None, connection=connection)
            print(f"✅ Successfully loaded {len(tools)} tools via MCP server")
            return tools
            
        except Exception as e:
            print(f"⚠️  MCP server approach failed: {str(e)}")
            return []
    
    def _get_env_vars(self) -> Dict[str, str]:
        """Get environment variables for MCP server."""
        env = os.environ.copy()
        env.update({
            "SALESFORCE_CONNECTION_TYPE": self.config.connection_type,
        })
        
        if self.config.connection_type == "User_Password":
            if self.config.username:
                env["SALESFORCE_USERNAME"] = self.config.username
            if self.config.password:
                env["SALESFORCE_PASSWORD"] = self.config.password
            if self.config.security_token:
                env["SALESFORCE_SECURITY_TOKEN"] = self.config.security_token
                env["SALESFORCE_TOKEN"] = self.config.security_token  # Claude Desktop format
            if self.config.instance_url:
                env["SALESFORCE_INSTANCE_URL"] = self.config.instance_url
                env["SALESFORCE_LOGIN_URL"] = self.config.instance_url
                
        return env
    
    def _create_fallback_tools(self) -> List[BaseTool]:
        """Create basic Salesforce tools as fallback when MCP server is unavailable."""
        print("🔧 Creating fallback Salesforce tools...")
        
        fallback_tools = []
        
        # Basic SOQL Query tool
        def soql_query_tool(query: str) -> str:
            """Execute SOQL queries against Salesforce."""
            try:
                # Import simple-salesforce for direct API access
                from simple_salesforce import Salesforce
                
                # Create Salesforce connection
                if self.config.connection_type == "User_Password":
                    sf = Salesforce(
                        username=self.config.username,
                        password=self.config.password,
                        security_token=self.config.security_token,
                        instance_url=self.config.instance_url
                    )
                else:
                    return "❌ Fallback mode only supports User/Password authentication"
                
                # Execute query
                result = sf.query(query)
                return f"✅ Query successful. Found {result['totalSize']} records: {result['records'][:5]}"
                
            except ImportError:
                return "❌ simple-salesforce package required for fallback mode. Install with: pip install simple-salesforce"
            except Exception as e:
                return f"❌ Query failed: {str(e)}"
        
        fallback_tools.append(Tool(
            name="salesforce_query",
            description="Execute SOQL queries against Salesforce. Use standard SOQL syntax.",
            func=soql_query_tool
        ))
        
        # Object Description tool
        def describe_object_tool(object_name: str) -> str:
            """Get object metadata from Salesforce."""
            try:
                from simple_salesforce import Salesforce
                
                if self.config.connection_type == "User_Password":
                    sf = Salesforce(
                        username=self.config.username,
                        password=self.config.password,
                        security_token=self.config.security_token,
                        instance_url=self.config.instance_url
                    )
                else:
                    return "❌ Fallback mode only supports User/Password authentication"
                
                # Get object description
                obj = getattr(sf, object_name)
                desc = obj.describe()
                
                fields = [f"{field['name']} ({field['type']})" for field in desc['fields'][:10]]
                return f"✅ Object: {object_name}\nFields: {', '.join(fields)}"
                
            except ImportError:
                return "❌ simple-salesforce package required for fallback mode"
            except Exception as e:
                return f"❌ Describe failed: {str(e)}"
        
        fallback_tools.append(Tool(
            name="salesforce_describe",
            description="Get metadata and field information for Salesforce objects.",
            func=describe_object_tool
        ))
        
        print(f"✅ Created {len(fallback_tools)} fallback Salesforce tools")
        return fallback_tools
    
    async def initialize(self) -> bool:
        """Initialize Salesforce integration with platform compatibility."""
        try:
            print(f"🚀 Initializing Salesforce integration (mode: {self.platform_mode})")
            
            # Try MCP server approach first
            mcp_tools = await self._try_mcp_integration()
            
            if mcp_tools:
                self.tools = mcp_tools
                print("✅ Using MCP server integration")
            else:
                # Fall back to direct API tools
                print("🔄 Falling back to direct API integration")
                self.tools = self._create_fallback_tools()
            
            if self.tools:
                self.is_initialized = True
                print(f"✅ Salesforce integration ready with {len(self.tools)} tools")
                return True
            else:
                print("❌ No Salesforce tools available")
                return False
                
        except Exception as e:
            print(f"❌ Error initializing Salesforce integration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """Get available Salesforce tools."""
        return self.tools
    
    def is_ready(self) -> bool:
        """Check if integration is ready."""
        return self.is_initialized and len(self.tools) > 0


async def create_platform_ready_salesforce_tools(config: Optional[PlatformSalesforceConfig] = None) -> List[BaseTool]:
    """
    Create platform-ready Salesforce tools with automatic fallback.
    
    Args:
        config: Salesforce configuration
        
    Returns:
        List of Salesforce tools ready for platform deployment
    """
    wrapper = PlatformSalesforceMCPWrapper(config)
    if await wrapper.initialize():
        return wrapper.get_tools()
    return []


def validate_platform_config() -> bool:
    """Validate configuration for platform deployment."""
    wrapper = PlatformSalesforceMCPWrapper()
    config = wrapper.config
    
    print(f"🔍 Platform mode: {wrapper.platform_mode}")
    
    if not config.username or not config.password:
        print("❌ Missing required Salesforce credentials")
        return False
    
    print(f"✅ Configuration valid for user: {config.username}")
    return True


# Export for easy import
__all__ = [
    'PlatformSalesforceMCPWrapper',
    'PlatformSalesforceConfig', 
    'create_platform_ready_salesforce_tools',
    'validate_platform_config'
]
