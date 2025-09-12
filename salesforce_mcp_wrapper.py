"""
Salesforce MCP Server Integration for LangChain

This module provides a wrapper to integrate the Salesforce MCP Server 
with LangChain agents, converting MCP tools to LangChain tools.
"""

import os
import asyncio
import subprocess
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.sessions import StdioConnection
from pydantic import BaseModel, Field


class SalesforceConnectionConfig(BaseModel):
    """Configuration for Salesforce MCP connection."""
    connection_type: str = Field(default="User_Password", description="Type of Salesforce connection")
    username: Optional[str] = Field(default=None, description="Salesforce username")
    password: Optional[str] = Field(default=None, description="Salesforce password")
    security_token: Optional[str] = Field(default=None, description="Salesforce security token")
    instance_url: Optional[str] = Field(default="https://login.salesforce.com", description="Salesforce instance URL")
    client_id: Optional[str] = Field(default=None, description="OAuth Client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth Client Secret")


class SalesforceMCPWrapper:
    """
    Wrapper class to manage Salesforce MCP Server integration with LangChain.
    
    This class handles:
    - Creating MCP connection configuration
    - Loading Salesforce MCP tools using langchain-mcp-adapters
    - Converting tools for use in LangChain agents
    """
    
    def __init__(self, config: Optional[SalesforceConnectionConfig] = None):
        self.config = config or self._load_config_from_env()
        self.tools: List[BaseTool] = []
        self.is_initialized = False
        
    def _load_config_from_env(self) -> SalesforceConnectionConfig:
        """Load Salesforce configuration from environment variables."""
        # Handle both SALESFORCE_INSTANCE_URL and SALESFORCE_LOGIN_URL
        instance_url = os.getenv("SALESFORCE_INSTANCE_URL") or os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
        
        return SalesforceConnectionConfig(
            connection_type=os.getenv("SALESFORCE_CONNECTION_TYPE", "User_Password"),
            username=os.getenv("SALESFORCE_USERNAME"),
            password=os.getenv("SALESFORCE_PASSWORD"),
            security_token=os.getenv("SALESFORCE_SECURITY_TOKEN", ""),  # Default to empty string
            instance_url=instance_url,
            client_id=os.getenv("SALESFORCE_CLIENT_ID"),
            client_secret=os.getenv("SALESFORCE_CLIENT_SECRET"),
        )
    
    def _create_mcp_connection(self) -> StdioConnection:
        """
        Create an MCP connection configuration for the Salesforce server.
        
        Returns:
            StdioConnection configuration for the MCP server
        """
        # Prepare environment variables for the MCP server
        env = os.environ.copy()
        env.update({
            "SALESFORCE_CONNECTION_TYPE": self.config.connection_type,
        })
        
        # Add connection-specific environment variables
        if self.config.connection_type == "User_Password":
            if self.config.username:
                env["SALESFORCE_USERNAME"] = self.config.username
            if self.config.password:
                env["SALESFORCE_PASSWORD"] = self.config.password
            if self.config.security_token:
                env["SALESFORCE_SECURITY_TOKEN"] = self.config.security_token
            if self.config.instance_url:
                env["SALESFORCE_INSTANCE_URL"] = self.config.instance_url
                # Also set SALESFORCE_LOGIN_URL for compatibility
                env["SALESFORCE_LOGIN_URL"] = self.config.instance_url
                
        elif self.config.connection_type == "OAuth_2.0_Client_Credentials":
            if self.config.client_id:
                env["SALESFORCE_CLIENT_ID"] = self.config.client_id
            if self.config.client_secret:
                env["SALESFORCE_CLIENT_SECRET"] = self.config.client_secret
            if self.config.instance_url:
                env["SALESFORCE_INSTANCE_URL"] = self.config.instance_url
                
        elif self.config.connection_type == "Salesforce_CLI":
            # No additional env vars needed for CLI auth
            pass
        
        return StdioConnection(
            transport="stdio",
            command="npx",
            args=["@tsmztech/mcp-server-salesforce"],
            env=env,
            cwd=Path.cwd()
        )
    
    async def load_salesforce_tools(self) -> List[BaseTool]:
        """
        Load Salesforce MCP tools using langchain-mcp-adapters.
        
        Returns:
            List of LangChain-compatible tools
        """
        try:
            # Create MCP connection
            connection = self._create_mcp_connection()
            
            # Load tools using langchain-mcp-adapters
            self.tools = await load_mcp_tools(session=None, connection=connection)
            
            print(f"✅ Loaded {len(self.tools)} Salesforce tools")
            if self.tools:
                print("📋 Available Salesforce tools:")
                for i, tool in enumerate(self.tools, 1):
                    print(f"   {i}. {tool.name}: {tool.description[:100]}...")
            
            self.is_initialized = True
            return self.tools
            
        except Exception as e:
            print(f"❌ Error loading Salesforce tools: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    async def initialize(self) -> bool:
        """
        Initialize the Salesforce MCP integration.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load tools using MCP adapters
            tools = await self.load_salesforce_tools()
            
            if tools:
                print("✅ Salesforce MCP integration initialized successfully")
                return True
            else:
                print("⚠️  No Salesforce tools were loaded")
                return False
            
        except Exception as e:
            print(f"❌ Error initializing Salesforce MCP integration: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """Cleanup resources."""
        self.tools = []
        self.is_initialized = False
        print("🧹 Salesforce MCP wrapper cleaned up")
    
    def get_tools(self) -> List[BaseTool]:
        """Get the loaded Salesforce tools."""
        return self.tools
    
    def __del__(self):
        """Cleanup on object destruction."""
        if self.is_initialized:
            self.cleanup()


async def create_salesforce_tools_async(config: Optional[SalesforceConnectionConfig] = None) -> List[BaseTool]:
    """
    Async function to create and initialize Salesforce tools.
    
    Args:
        config: Salesforce connection configuration
        
    Returns:
        List of Salesforce tools ready for use in LangChain agents
    """
    wrapper = SalesforceMCPWrapper(config)
    if await wrapper.initialize():
        return wrapper.get_tools()
    return []


def create_salesforce_tools(config: Optional[SalesforceConnectionConfig] = None) -> List[BaseTool]:
    """
    Convenience function to create and initialize Salesforce tools synchronously.
    
    Args:
        config: Salesforce connection configuration
        
    Returns:
        List of Salesforce tools ready for use in LangChain agents
    """
    try:
        # Run the async function
        return asyncio.run(create_salesforce_tools_async(config))
    except Exception as e:
        print(f"❌ Failed to create Salesforce tools: {str(e)}")
        return []


# Example usage and configuration validation
def validate_salesforce_config() -> bool:
    """Validate that required Salesforce configuration is present."""
    wrapper = SalesforceMCPWrapper()
    config = wrapper.config
    
    if config.connection_type == "User_Password":
        # Check for required fields - security_token can be empty for some orgs
        if not config.username:
            print("❌ Missing SALESFORCE_USERNAME")
            return False
        if not config.password:
            print("❌ Missing SALESFORCE_PASSWORD")
            return False
        # security_token can be empty/None for trusted IP ranges
        print(f"✅ User/Password auth configured for user: {config.username}")
    
    elif config.connection_type == "OAuth_2.0_Client_Credentials":
        required_fields = ["client_id", "client_secret", "instance_url"]
        missing = [field for field in required_fields if not getattr(config, field)]
        if missing:
            print(f"❌ Missing required fields for OAuth auth: {', '.join(missing)}")
            return False
    
    elif config.connection_type == "Salesforce_CLI":
        # CLI auth doesn't require additional config
        print("✅ Salesforce CLI auth configured")
        pass
    
    else:
        print(f"❌ Invalid connection type: {config.connection_type}")
        return False
    
    print("✅ Salesforce configuration is valid")
    return True
