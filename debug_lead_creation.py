"""
Diagnostic test to debug lead creation issues with the LangGraph API
"""

import os
import json
from dotenv import load_dotenv
from langgraph_sdk import get_sync_client

# Load environment variables
load_dotenv()

DEPLOYMENT_URL = "https://mcpconnectordynamic-343b682d82a350a8a9ff6eb9bc33626c.us.langgraph.app"

def debug_lead_creation():
    """Debug lead creation with step-by-step analysis"""
    
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ Error: LANGSMITH_API_KEY environment variable not set!")
        return
    
    try:
        client = get_sync_client(url=DEPLOYMENT_URL, api_key=api_key)
        
        print("🔬 Lead Creation Diagnostic Test")
        print("="*50)
        
        # Step 1: Create thread and authenticate
        thread = client.threads.create()
        print(f"✅ Created thread: {thread['thread_id']}")
        
        # 🚨 SECURITY: Load Salesforce credentials from environment variables
        credentials = {
            "instanceUrl": os.getenv("SALESFORCE_INSTANCE_URL", "https://your-org.my.salesforce.com"),
            "accessToken": os.getenv("SALESFORCE_ACCESS_TOKEN", "your_access_token_here"),
            "tokenType": os.getenv("SALESFORCE_TOKEN_TYPE", "Bearer"),
            "refreshToken": os.getenv("SALESFORCE_REFRESH_TOKEN", "your_refresh_token_here"),
            "authCode": os.getenv("SALESFORCE_AUTH_CODE", "your_auth_code_here")
        }
        
        # Validate credentials
        if any("your_" in str(v) for v in credentials.values()):
            print("❌ Please set Salesforce credentials in environment variables first:")
            print("  export SALESFORCE_INSTANCE_URL=https://your-org.my.salesforce.com")
            print("  export SALESFORCE_ACCESS_TOKEN=your_actual_token")  
            print("  export SALESFORCE_AUTH_CODE=your_actual_code")
            return
        
        auth_message = f"Please authenticate with these credentials: {json.dumps(credentials)}"
        
        print("\n🔐 Step 1: Authentication...")
        input_data = {
            "messages": [{"role": "human", "content": auth_message}]
        }
        
        # Test with a timeout and non-streaming first
        print("📡 Testing non-streaming authentication...")
        
        try:
            run_result = client.runs.create(
                thread_id=thread["thread_id"],
                assistant_id="advanced_agent",
                input=input_data
            )
            print(f"✅ Run created: {run_result['run_id']}")
            
            # Wait for completion with timeout
            import time
            max_wait = 30  # 30 seconds timeout
            wait_time = 0
            
            while wait_time < max_wait:
                status = client.runs.get(thread_id=thread["thread_id"], run_id=run_result["run_id"])
                print(f"📊 Run status: {status['status']}")
                
                if status["status"] in ["success", "error", "failed"]:
                    break
                    
                time.sleep(2)
                wait_time += 2
            
            if status["status"] == "success":
                # Get the thread state instead
                try:
                    thread_state = client.threads.get_state(thread_id=thread["thread_id"])
                    if "values" in thread_state and "messages" in thread_state["values"]:
                        messages = thread_state["values"]["messages"]
                        for msg in messages[-3:]:  # Show last 3 messages
                            if msg.get("type") == "ai":
                                print(f"🤖 Auth Response: {msg['content']}")
                except Exception as e:
                    print(f"⚠️ Could not get thread state: {e}")
                    print("✅ Authentication run completed successfully")
                
                print("\n📋 Step 2: Testing Simple Lead Creation...")
                
                # Very simple lead creation request
                simple_lead_request = """Create a simple lead record with these details:
- First Name: Test
- Last Name: User  
- Company: Test Company
- Email: test@example.com

Please use the Salesforce tools to create this lead."""
                
                lead_input = {
                    "messages": [{"role": "human", "content": simple_lead_request}]
                }
                
                print("📡 Creating lead creation run...")
                lead_run = client.runs.create(
                    thread_id=thread["thread_id"],
                    assistant_id="advanced_agent",
                    input=lead_input
                )
                
                print(f"✅ Lead run created: {lead_run['run_id']}")
                
                # Monitor the lead creation run
                wait_time = 0
                while wait_time < max_wait:
                    lead_status = client.runs.get(thread_id=thread["thread_id"], run_id=lead_run["run_id"])
                    print(f"📊 Lead run status: {lead_status['status']}")
                    
                    if lead_status["status"] in ["success", "error", "failed"]:
                        break
                        
                    time.sleep(2)
                    wait_time += 2
                
                if lead_status["status"] == "success":
                    # Get the thread state
                    try:
                        lead_thread_state = client.threads.get_state(thread_id=thread["thread_id"])
                        if "values" in lead_thread_state and "messages" in lead_thread_state["values"]:
                            messages = lead_thread_state["values"]["messages"]
                            for msg in messages[-3:]:  # Show last 3 messages
                                if msg.get("type") == "ai":
                                    print(f"🤖 Lead Creation Response: {msg['content']}")
                                elif msg.get("type") == "human":
                                    print(f"👤 User: {msg['content'][:100]}...")
                    except Exception as e:
                        print(f"⚠️ Could not get thread state: {e}")
                        print("✅ Lead creation run completed successfully")
                else:
                    print(f"❌ Lead creation failed with status: {lead_status['status']}")
                    print(f"Full lead status: {lead_status}")
                    
                    # Try to get thread state anyway to see error messages
                    try:
                        error_thread_state = client.threads.get_state(thread_id=thread["thread_id"])
                        if "values" in error_thread_state and "messages" in error_thread_state["values"]:
                            messages = error_thread_state["values"]["messages"]
                            for msg in messages[-3:]:  # Show last 3 messages
                                print(f"📄 Message ({msg.get('type', 'unknown')}): {msg.get('content', 'No content')[:200]}...")
                    except Exception as e:
                        print(f"⚠️ Could not get error thread state: {e}")
                        
            else:
                print(f"❌ Authentication failed with status: {status['status']}")
                if 'error' in status:
                    print(f"Error details: {status['error']}")
                    
        except Exception as e:
            print(f"❌ Non-streaming test failed: {e}")
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")

if __name__ == "__main__":
    debug_lead_creation()
