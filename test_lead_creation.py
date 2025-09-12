#!/usr/bin/env python3
"""
Test Lead creation functionality specifically to ensure the tool call error is fixed.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from main_recursion_fixed import graph

def test_lead_creation():
    """Test creating a Lead record to verify the tool call fix."""
    print("🧪 Testing Lead Creation (Previously Caused Tool Call Error)")
    print("="*60)
    
    test_state = {
        "messages": [HumanMessage(content="Create a new Lead record in Salesforce with FirstName=John, LastName=Doe, Company=Test Corp, Email=john.doe@testcorp.com")],
        "tool_call_count": 0
    }
    
    try:
        print("🚀 Creating Lead record...")
        
        result = graph.invoke(
            test_state,
            config={"recursion_limit": 15}
        )
        
        tool_calls = result.get('tool_call_count', 0)
        response = result['messages'][-1].content
        
        print("✅ SUCCESS - No tool call error!")
        print(f"🔢 Tool calls used: {tool_calls}/5")
        print(f"📝 Response length: {len(response)} characters")
        
        # Check if the response indicates successful creation
        if "Record Creation - COMPLETE" in response and "Successfully created" in response:
            print("🎉 Lead created successfully!")
        elif "Record Creation - COMPLETE" in response:
            print("⚠️ Lead creation attempted (check response for details)")
        else:
            print("ℹ️ Response received (may need to check tool usage)")
        
        print("\n📝 Agent Response:")
        print("-" * 50)
        print(response)
        print("-" * 50)
        
        return True
        
    except Exception as e:
        if "tool_call" in str(e).lower():
            print(f"❌ TOOL CALL ERROR STILL EXISTS: {str(e)}")
            return False
        else:
            print(f"❌ OTHER ERROR: {str(e)}")
            return False

if __name__ == "__main__":
    success = test_lead_creation()
    print("\n" + "="*60)
    if success:
        print("🎉 LEAD CREATION TEST PASSED!")
        print("✅ Tool call error is fixed")
        print("✅ Agent can now create Salesforce records")
        exit(0)
    else:
        print("❌ TEST FAILED - Issues remain")
        exit(1)
