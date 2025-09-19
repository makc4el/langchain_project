#!/usr/bin/env python3
"""
Test the chat agent with real credentials provided via chat
"""

import asyncio
import json
import logging
from langchain_core.messages import HumanMessage
from main import create_simple_agent  # Import your main chat agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PLACEHOLDER CREDENTIALS - Replace with your real credentials as they would be provided in chat
CREDENTIAL_MESSAGE = """{
  "success": true,
  "instanceUrl": "https://your-org.my.salesforce.com",
  "accessToken": "your_access_token_here",
  "tokenType": "Bearer",
  "refreshToken": "your_refresh_token_here",
  "scope": "refresh_token api",
  "authCode": "your_auth_code_here"
}"""

async def test_chat_with_credentials():
    """Test the chat agent by providing credentials through the chat interface"""
    print("💬 TESTING CHAT AGENT WITH REAL CREDENTIALS")
    print("=" * 60)
    
    # Create the agent
    agent = create_simple_agent()
    
    # Initial state
    initial_state = {
        "messages": [],
        "salesforce_instance_url": None,
        "salesforce_access_token": None,
        "salesforce_authenticated": False
    }
    
    print("🤖 Starting conversation...")
    print("\n" + "="*50)
    
    # Step 1: Initial greeting (should ask for credentials)
    print("👤 USER: Hello! I need help with Salesforce.")
    
    user_message = HumanMessage(content="Hello! I need help with Salesforce.")
    current_state = {**initial_state, "messages": [user_message]}
    
    result1 = await agent.ainvoke(current_state)
    
    print("🤖 AGENT:")
    for msg in result1["messages"]:
        if hasattr(msg, 'content'):
            print(f"   {msg.content}")
    
    print("\n" + "="*50)
    
    # Step 2: Provide credentials via JSON (exactly as user would)
    print("👤 USER: Here are my credentials:")
    print(f"   {CREDENTIAL_MESSAGE[:100]}...")
    
    credential_message = HumanMessage(content=CREDENTIAL_MESSAGE)
    current_state = {**result1, "messages": result1["messages"] + [credential_message]}
    
    result2 = await agent.ainvoke(current_state)
    
    print("\n🤖 AGENT:")
    for msg in result2["messages"][len(result1["messages"]):]:
        if hasattr(msg, 'content'):
            print(f"   {msg.content}")
    
    # Check if authentication worked
    auth_status = result2.get("salesforce_authenticated", False)
    instance_url = result2.get("salesforce_instance_url")
    
    print(f"\n✅ Authentication Status: {auth_status}")
    if instance_url:
        print(f"🌐 Connected to: {instance_url}")
    
    print("\n" + "="*50)
    
    # Step 3: Ask to create a Lead (if authenticated)
    if auth_status:
        print("👤 USER: Please create a new Lead record with random data.")
        
        lead_request = HumanMessage(content="Please create a new Lead record with random data. Use FirstName: TestChat, LastName: ChatLead followed by random numbers, Company: Chat Test Company, Email: testchat@example.com, Status: Open - Not Contacted")
        current_state = {**result2, "messages": result2["messages"] + [lead_request]}
        
        result3 = await agent.ainvoke(current_state)
        
        print("\n🤖 AGENT:")
        for msg in result3["messages"][len(result2["messages"]):]:
            if hasattr(msg, 'content'):
                print(f"   {msg.content}")
    else:
        print("❌ Authentication failed - cannot test Lead creation")
    
    print("\n" + "="*60)
    print("🎯 CHAT TEST COMPLETED")
    
    return auth_status

async def main():
    """Main test function"""
    print("🚀 TESTING REAL CREDENTIALS IN CHAT INTERFACE")
    print("=" * 60)
    print()
    print("This test simulates exactly what happens when you:")
    print("1. Start a chat with the agent")
    print("2. Provide your credentials as JSON in the chat")
    print("3. Ask the agent to perform Salesforce operations")
    print()
    
    try:
        success = await test_chat_with_credentials()
        
        if success:
            print("\n🎉 SUCCESS!")
            print("✅ Your credentials work perfectly in the chat interface!")
            print("✅ You can now use the main chat agent with your real credentials")
            print("\n💡 TO USE:")
            print("   1. Run: uv run python main.py")
            print("   2. When prompted, paste your JSON credentials")
            print("   3. Start asking for Salesforce operations!")
        else:
            print("\n⚠️  Authentication issues detected")
            print("Check the output above for details")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error(f"Chat test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
