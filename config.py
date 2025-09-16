"""
Configuration module for enhanced deployment stability
"""

import os
from typing import Optional


class Config:
    """Configuration class with deployment optimizations"""
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    
    # LangSmith Configuration
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")
    LANGCHAIN_API_KEY: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "salesforce-ai-agent")
    
    # Database Configuration with resilience
    POSTGRES_HOST: Optional[str] = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DB")
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    
    # Connection resilience settings
    POOL_TIMEOUT: int = int(os.getenv("POOL_TIMEOUT", "60"))  # Increased from default 30
    CONNECTION_RETRIES: int = int(os.getenv("CONNECTION_RETRIES", "5"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))
    
    # Application settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # MCP Server Configuration
    MCP_SALESFORCE_URL: str = os.getenv(
        "MCP_SALESFORCE_URL", 
        "https://mcp-server-salesforce-production.up.railway.app"
    )
    
    @classmethod
    def validate_required_keys(cls) -> list[str]:
        """Validate that required API keys are present"""
        missing_keys = []
        
        if not cls.OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")
            
        return missing_keys
    
    @classmethod
    def get_database_url(cls) -> Optional[str]:
        """Get database URL if all components are available"""
        if all([cls.POSTGRES_HOST, cls.POSTGRES_DB, cls.POSTGRES_USER, cls.POSTGRES_PASSWORD]):
            return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        return None


# Global config instance
config = Config()
