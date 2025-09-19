#!/usr/bin/env python3
"""
Debug Advanced Agent Tool Usage

This script simulates the exact scenario the user reported to understand
why the agent is using tavily_search instead of Salesforce tools.
"""

import asyncio
import json
import logging
from langchain_core.messages import HumanMessage
from main import create_advanced_graph

# Configure detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test credentials (placeholders)
TEST_CREDENTIALS = {
    "instanceUrl": "https://your-org.my.salesforce.com",
    "accessToken": "your_access_token_here",
    "tokenType": "Bearer",
    "refreshToken": "your_refresh_token_here",
    "scope": "refresh_token api",
    "authCode": "your_auth_code_here"
}

async def debug_advanced_agent():
    """Debug why advanced agent uses tavily_search instead of Salesforce tools"""
    print("🔍 DEBUGGING ADVANCED AGENT TOOL USAGE")
    print("=" * 50)
    
    # Create the advanced agent
    agent = create_advanced_graph()
    
    print("\n📍 STEP 1: Provide credentials to authenticate")
    print("-" * 40)
    
    # Initial state with credentials
    credentials_json = json.dumps(TEST_CREDENTIALS, indent=2)
    
    auth_state = {
        "messages": [
            HumanMessage(content="Hello!"),
            HumanMessage(content=credentials_json)
        ],
        "user_id": "debug_user",
        "session_id": "debug_session", 
        "conversation_count": 0,
        "salesforce_authenticated": False,
        "salesforce_instance_url": None,
        "salesforce_access_token": None
    }
    
    print("👤 USER: Providing credentials...")
    result1 = await agent.ainvoke(auth_state)
    
    print(f"🔍 Authentication result: {result1.get('salesforce_authenticated', False)}")
    print(f"🌐 Instance URL: {result1.get('salesforce_instance_url', 'None')}")
    
    if not result1.get('salesforce_authenticated', False):
        print("❌ Authentication failed - cannot test Lead creation")
        return
    
    print("\n📍 STEP 2: Request Lead creation (the exact scenario)")
    print("-" * 40)
    
    # Add the Lead creation request
    lead_state = {
        **result1,
        "messages": result1["messages"] + [HumanMessage(content="create new random lead record in my salesforce org")]
    }
    
    print("👤 USER: create new random lead record in my salesforce org")
    print("\n🔍 DEBUGGING INFO:")
    print("- Agent should use 'dml' tool with operation: 'insert'")
    print("- Agent should NOT use 'tavily_search'")
    print("- Watch the logs for tool selection...")
    
    result2 = await agent.ainvoke(lead_state)
    
    print("\n🤖 AGENT RESPONSE:")
    for msg in result2["messages"][len(result1["messages"]):]:
        if hasattr(msg, 'content') and msg.content:
            print(f"   {msg.content[:300]}{'...' if len(msg.content) > 300 else ''}")
    
    # Analyze the response for tool usage
    agent_response = result2["messages"][-1].content.lower()
    
    print(f"\n📊 ANALYSIS:")
    print("-" * 20)
    
    if "created" in agent_response and ("lead" in agent_response or "record" in agent_response):
        print("✅ SUCCESS: Agent appears to have created a Lead record")
    elif "tavily" in agent_response or "search" in agent_response:
        print("❌ PROBLEM: Agent used search instead of Salesforce tools")
    elif "cannot" in agent_response or "don't have" in agent_response:
        print("⚠️  ISSUE: Agent claims it cannot create records")
    else:
        print("❓ UNCLEAR: Response doesn't clearly indicate what happened")
    
    return result2

async def main():
    """Main debug function"""
    print("🚀 ADVANCED AGENT DEBUGGING")
    print("Investigating why agent uses tavily_search instead of Salesforce tools")
    print("=" * 70)
    
    try:
        result = await debug_advanced_agent()
        
        print("\n" + "=" * 70)
        print("📋 DEBUGGING SUMMARY:")
        print("=" * 70)
        print("Expected behavior: Agent should use 'dml' tool to create Lead")
        print("Problem behavior: Agent uses 'tavily_search' to research how to create Lead")
        print("\nIf this test shows the problem, we need to fix tool loading in production.")
        
    except Exception as e:
        print(f"\n❌ Debug test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
