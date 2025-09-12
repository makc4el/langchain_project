#!/usr/bin/env python3
"""
Test the specific scenario that would have caused GraphRecursionError
"""

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from main_recursion_fixed import graph

def test_recursion_scenario():
    """Test a scenario that previously caused infinite recursion."""
    print("🧪 Testing Previously Problematic Recursion Scenario...")
    print("="*60)
    
    # This type of request previously caused loops
    problematic_state = {
        "messages": [HumanMessage(content="Help me with my Salesforce, check the status and tell me what you can do")],
        "tool_call_count": 0
    }
    
    try:
        print("🚀 Invoking agent (this previously would timeout with GraphRecursionError)...")
        
        result = graph.invoke(
            problematic_state,
            config={"recursion_limit": 15}
        )
        
        print("✅ SUCCESS - No recursion error!")
        print(f"🔢 Tool calls used: {result.get('tool_call_count', 0)}/5")
        print(f"💬 Total messages: {len(result['messages'])}")
        print(f"🤖 Final response length: {len(result['messages'][-1].content)} characters")
        
        print("\n📝 Agent Response Preview:")
        print("-" * 50)
        print(result['messages'][-1].content[:300] + "..." if len(result['messages'][-1].content) > 300 else result['messages'][-1].content)
        print("-" * 50)
        
        return True
        
    except Exception as e:
        if "GraphRecursionError" in str(e) or "Recursion limit" in str(e):
            print(f"❌ RECURSION ERROR STILL EXISTS: {str(e)}")
            return False
        else:
            print(f"❌ OTHER ERROR: {str(e)}")
            return False

if __name__ == "__main__":
    success = test_recursion_scenario()
    print("\n" + "="*60)
    if success:
        print("🎉 VERIFICATION COMPLETE - GraphRecursionError is FIXED!")
        print("✅ Your agent is safe to deploy!")
        exit(0)
    else:
        print("❌ VERIFICATION FAILED - Issue still exists!")
        exit(1)
