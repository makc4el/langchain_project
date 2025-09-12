"""
Example client code to interact with your deployed LangGraph chat agents
"""

import asyncio
from langgraph_sdk import get_sync_client, get_client

def test_sync_client():
    """Test your chat agents using the synchronous client"""
    
    # Initialize client for local development
    client = get_sync_client(url="http://localhost:2024")
    
    # Create a new thread
    thread = client.threads.create()
    print(f"Created thread: {thread['thread_id']}")
    
    # Test simple agent
    print("\n=== Testing Simple Agent ===")
    input_data = {
        "messages": [
            {"role": "human", "content": "Hello! Can you explain what you do?"}
        ]
    }
    
    # Run the simple agent
    for chunk in client.runs.stream(
        thread_id=thread["thread_id"],
        assistant_id="agent",
        input=input_data,
        stream_mode="values"
    ):
        if chunk.data and "messages" in chunk.data:
            messages = chunk.data["messages"]
            if messages:
                print(f"Agent: {messages[-1]['content']}")
    
    # Test advanced agent
    print("\n=== Testing Advanced Agent ===")
    advanced_input = {
        "messages": [
            {"role": "human", "content": "What's special about the advanced version?"}
        ],
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "conversation_count": 0
    }
    
    # Create new thread for advanced agent
    advanced_thread = client.threads.create()
    
    for chunk in client.runs.stream(
        thread_id=advanced_thread["thread_id"],
        assistant_id="advanced_agent", 
        input=advanced_input,
        stream_mode="values"
    ):
        if chunk.data and "messages" in chunk.data:
            messages = chunk.data["messages"]
            if messages:
                print(f"Advanced Agent: {messages[-1]['content']}")
                print(f"Conversation Count: {chunk.data.get('conversation_count', 'N/A')}")


async def test_async_client():
    """Test your chat agents using the asynchronous client"""
    
    # Initialize async client
    client = get_client(url="http://localhost:2024")
    
    # Create a new thread
    thread = await client.threads.create()
    print(f"Created async thread: {thread['thread_id']}")
    
    # Test with streaming
    input_data = {
        "messages": [
            {"role": "human", "content": "Tell me about async processing!"}
        ]
    }
    
    print("\n=== Async Streaming Test ===")
    async for chunk in client.runs.stream(
        thread_id=thread["thread_id"],
        assistant_id="agent",
        input=input_data,
        stream_mode="values"
    ):
        if chunk.data and "messages" in chunk.data:
            messages = chunk.data["messages"]
            if messages:
                print(f"Async Agent: {messages[-1]['content']}")


def test_background_run():
    """Test running your agent in the background with polling"""
    
    client = get_sync_client(url="http://localhost:2024")
    
    # Create thread
    thread = client.threads.create()
    
    # Start background run
    run = client.runs.create(
        thread_id=thread["thread_id"],
        assistant_id="agent",
        input={
            "messages": [
                {"role": "human", "content": "Process this request in the background"}
            ]
        }
    )
    
    print(f"Started background run: {run['run_id']}")
    
    # Poll for completion
    while True:
        run_status = client.runs.get(thread_id=thread["thread_id"], run_id=run["run_id"])
        print(f"Run status: {run_status['status']}")
        
        if run_status["status"] in ["success", "error"]:
            # Get the final result
            final_state = client.runs.get_state(
                thread_id=thread["thread_id"], 
                run_id=run["run_id"]
            )
            if "messages" in final_state["values"]:
                final_message = final_state["values"]["messages"][-1]
                print(f"Final result: {final_message['content']}")
            break
        
        # Wait before polling again
        import time
        time.sleep(1)


if __name__ == "__main__":
    print("Testing LangGraph Chat Agents...")
    
    # Test synchronous client
    test_sync_client()
    
    # Test asynchronous client  
    asyncio.run(test_async_client())
    
    # Test background processing
    test_background_run()

