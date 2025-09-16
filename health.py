"""
Health check endpoints for deployment monitoring
"""

import asyncio
import time
from typing import Dict, Any
from mcp_client import mcp_client
from config import config


async def check_mcp_server_health() -> Dict[str, Any]:
    """Check if MCP Salesforce server is accessible"""
    try:
        # Simple health check - try to list tools without credentials
        start_time = time.time()
        
        # Create a test client for health check
        test_payload = {
            "method": "tools/list"
        }
        
        response = await mcp_client.client.post(
            f"{mcp_client.server_url}/health",  # Assuming health endpoint
            json=test_payload,
            timeout=10.0
        )
        
        response_time = time.time() - start_time
        
        return {
            "status": "healthy" if response.status_code < 500 else "degraded",
            "response_time_ms": round(response_time * 1000, 2),
            "status_code": response.status_code,
            "url": mcp_client.server_url
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "url": mcp_client.server_url
        }


async def check_openai_connection() -> Dict[str, Any]:
    """Check if OpenAI API key is configured"""
    return {
        "status": "configured" if config.OPENAI_API_KEY else "missing",
        "key_present": bool(config.OPENAI_API_KEY),
        "key_length": len(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else 0
    }


async def check_tavily_connection() -> Dict[str, Any]:
    """Check if Tavily API key is configured"""
    return {
        "status": "configured" if config.TAVILY_API_KEY else "optional",
        "key_present": bool(config.TAVILY_API_KEY)
    }


async def comprehensive_health_check() -> Dict[str, Any]:
    """Comprehensive health check for all components"""
    start_time = time.time()
    
    # Run all health checks concurrently
    mcp_health, openai_health, tavily_health = await asyncio.gather(
        check_mcp_server_health(),
        check_openai_connection(),
        check_tavily_connection(),
        return_exceptions=True
    )
    
    total_time = time.time() - start_time
    
    # Determine overall status
    overall_status = "healthy"
    if isinstance(mcp_health, Exception) or mcp_health.get("status") == "unhealthy":
        overall_status = "unhealthy"
    elif isinstance(openai_health, Exception) or openai_health.get("status") == "missing":
        overall_status = "degraded"
    elif mcp_health.get("status") == "degraded":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "total_check_time_ms": round(total_time * 1000, 2),
        "components": {
            "mcp_server": mcp_health if not isinstance(mcp_health, Exception) else {"status": "error", "error": str(mcp_health)},
            "openai": openai_health if not isinstance(openai_health, Exception) else {"status": "error", "error": str(openai_health)},
            "tavily": tavily_health if not isinstance(tavily_health, Exception) else {"status": "error", "error": str(tavily_health)}
        },
        "config": {
            "mcp_server_url": config.MCP_SALESFORCE_URL,
            "log_level": config.LOG_LEVEL,
            "pool_timeout": config.POOL_TIMEOUT
        }
    }


# For local testing
async def main():
    """Test health checks locally"""
    print("🏥 Running Health Checks...")
    health_result = await comprehensive_health_check()
    
    print(f"\n📊 Overall Status: {health_result['status'].upper()}")
    print(f"⏱️  Total Check Time: {health_result['total_check_time_ms']}ms")
    
    print("\n🔍 Component Details:")
    for component, details in health_result['components'].items():
        status = details.get('status', 'unknown').upper()
        print(f"  • {component}: {status}")
        if 'error' in details:
            print(f"    Error: {details['error']}")
        if 'response_time_ms' in details:
            print(f"    Response Time: {details['response_time_ms']}ms")


if __name__ == "__main__":
    asyncio.run(main())
