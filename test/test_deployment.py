"""
Test script to interact with your deployed LangGraph application
Deployment URL: https://your-deployment-id.us.langgraph.app
"""

import os
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client, get_client
import asyncio

# Load environment variables from .env file
load_dotenv()

# Your deployment URL
DEPLOYMENT_URL = "https://your-deployment-id.us.langgraph.app"

def test_with_api_key():
    """Test your deployed agents with LangSmith API key authentication"""
    
    # You need to set your LangSmith API key
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ Error: LANGSMITH_API_KEY environment variable not set!")
        print("Get your API key from https://smith.langchain.com/settings")
        return
    
    try:
        # Initialize client with your deployment URL
        client = get_sync_client(url=DEPLOYMENT_URL, api_key=api_key)
        
        print(f"🚀 Testing deployment: {DEPLOYMENT_URL}")
        print(f"🔑 Using API key: {api_key[:8]}...")
        
        # Create a new thread
        print("\n📝 Creating new thread...")
        thread = client.threads.create()
        print(f"✅ Created thread: {thread['thread_id']}")
        
        # Test your simple agent
        print("\n🤖 Testing 'agent' (simple chat agent)...")
        input_data = {
            "messages": [
                {"role": "human", "content": "Hello! Can you introduce yourself?"}
            ]
        }
        
        print("💬 Sending message: 'Hello! Can you introduce yourself?'")
        
        for chunk in client.runs.stream(
            thread_id=thread["thread_id"],
            assistant_id="agent",  # This matches your langgraph.json
            input=input_data,
            stream_mode="values"
        ):
            if chunk.data and "messages" in chunk.data:
                messages = chunk.data["messages"]
                if messages:
                    latest_message = messages[-1]
                    if latest_message.get("role") == "ai":
                        print(f"🤖 Agent: {latest_message['content']}")
        
        # Test your advanced agent
        print("\n🧠 Testing 'advanced_agent' (with session management)...")
        advanced_input = {
            "messages": [
                {"role": "human", "content": "What makes you different from the simple agent?"}
            ],
            "user_id": "test_user_123",
            "session_id": "test_session_456",
            "conversation_count": 0
        }
        
        # Create new thread for advanced agent
        advanced_thread = client.threads.create()
        print(f"✅ Created advanced thread: {advanced_thread['thread_id']}")
        
        print("💬 Sending message to advanced agent...")
        
        for chunk in client.runs.stream(
            thread_id=advanced_thread["thread_id"],
            assistant_id="advanced_agent",  # This matches your langgraph.json
            input=advanced_input,
            stream_mode="values"
        ):
            if chunk.data and "messages" in chunk.data:
                messages = chunk.data["messages"]
                if messages:
                    latest_message = messages[-1]
                    if latest_message.get("role") == "ai":
                        print(f"🧠 Advanced Agent: {latest_message['content']}")
                        
                # Show conversation count if available
                conv_count = chunk.data.get("conversation_count")
                if conv_count is not None:
                    print(f"📊 Conversation Count: {conv_count}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Common issues:")
        print("- Invalid or missing LANGSMITH_API_KEY")
        print("- Deployment not accessible or not ready")
        print("- Network connectivity issues")


def test_curl_commands():
    """Generate cURL commands for your deployment"""
    
    api_key = os.getenv("LANGSMITH_API_KEY", "your-langsmith-api-key-here")
    
    print("🔧 cURL Commands for Your Deployment")
    print("=" * 50)
    
    print("\n1️⃣ Create a thread:")
    print(f"""curl -X POST "{DEPLOYMENT_URL}/threads" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: {api_key}" \\
  -d '{{}}'""")
    
    print("\n2️⃣ Stream chat with simple agent:")
    print(f"""curl -X POST "{DEPLOYMENT_URL}/threads/{{thread_id}}/runs/stream" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: {api_key}" \\
  -d '{{
    "assistant_id": "agent",
    "input": {{
      "messages": [
        {{
          "role": "human",
          "content": "Hello! How are you?"
        }}
      ]
    }},
    "stream_mode": "values"
  }}'""")
    
    print("\n3️⃣ Stream chat with advanced agent:")
    print(f"""curl -X POST "{DEPLOYMENT_URL}/threads/{{thread_id}}/runs/stream" \\
  -H "Content-Type: application/json" \\
  -H "x-api-key: {api_key}" \\
  -d '{{
    "assistant_id": "advanced_agent",
    "input": {{
      "messages": [
        {{
          "role": "human",
          "content": "What can you do?"
        }}
      ],
      "user_id": "user123",
      "session_id": "session456",
      "conversation_count": 0
    }},
    "stream_mode": "values"
  }}'""")


async def test_async():
    """Test with async client"""
    
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ LANGSMITH_API_KEY not set for async test")
        return
    
    try:
        client = get_client(url=DEPLOYMENT_URL, api_key=api_key)
        
        print("\n🔄 Testing async streaming...")
        thread = await client.threads.create()
        
        input_data = {
            "messages": [
                {"role": "human", "content": "Tell me about async processing!"}
            ]
        }
        
        async for chunk in client.runs.stream(
            thread_id=thread["thread_id"],
            assistant_id="agent",
            input=input_data,
            stream_mode="values"
        ):
            if chunk.data and "messages" in chunk.data:
                messages = chunk.data["messages"]
                if messages:
                    latest_message = messages[-1]
                    if latest_message.get("role") == "ai":
                        print(f"🔄 Async Agent: {latest_message['content']}")
        
    except Exception as e:
        print(f"❌ Async test failed: {e}")


if __name__ == "__main__":
    print("🎯 LangGraph Deployment Tester")
    print("=" * 40)
    
    # Show cURL examples
    test_curl_commands()
    
    print("\n" + "=" * 40)
    
    # Test with Python client
    test_with_api_key()
    
    # Test async
    asyncio.run(test_async())

