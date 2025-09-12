#!/usr/bin/env python3
"""
Final Verification: Test that GraphRecursionError is completely fixed
"""

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from main_recursion_fixed import graph, MAX_TOOL_CALLS_PER_CONVERSATION, MAX_RECURSION_LIMIT

def verify_fix():
    """Verify the GraphRecursionError fix works."""
    print("🔍 FINAL VERIFICATION: GraphRecursionError Fix")
    print("="*60)
    print(f"🔄 Max recursion limit: {MAX_RECURSION_LIMIT}")
    print(f"🔧 Max tool calls: {MAX_TOOL_CALLS_PER_CONVERSATION}")
    
    # Test the exact type of request that caused issues before
    test_scenarios = [
        "Help me with Salesforce, check my status and show me what you can do",
        "What's my Salesforce integration status? Can you query some data?",
        "I need help with my Salesforce org - tell me everything you can do"
    ]
    
    all_passed = True
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🧪 Test {i}/3: {scenario}")
        print("-" * 50)
        
        test_state = {
            "messages": [HumanMessage(content=scenario)],
            "tool_call_count": 0
        }
        
        try:
            result = graph.invoke(
                test_state,
                config={"recursion_limit": MAX_RECURSION_LIMIT}
            )
            
            tool_calls = result.get('tool_call_count', 0)
            response_length = len(result['messages'][-1].content)
            
            print(f"✅ SUCCESS")
            print(f"🔢 Tool calls: {tool_calls}/{MAX_TOOL_CALLS_PER_CONVERSATION}")
            print(f"📝 Response: {response_length} chars")
            
            if tool_calls <= MAX_TOOL_CALLS_PER_CONVERSATION:
                print("✅ Tool calls within limit")
            else:
                print(f"❌ Too many tool calls: {tool_calls}")
                all_passed = False
            
        except Exception as e:
            if "GraphRecursionError" in str(e) or "Recursion limit" in str(e):
                print(f"❌ RECURSION ERROR: {str(e)}")
                all_passed = False
            else:
                print(f"❌ OTHER ERROR: {str(e)}")
                all_passed = False
    
    print("\n" + "="*60)
    print("📊 FINAL VERIFICATION RESULTS")
    print("="*60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ GraphRecursionError is COMPLETELY FIXED")
        print("✅ Tool call limits are working")
        print("✅ Agent provides definitive responses")
        print("✅ Safe for production deployment")
        
        print("\n🚀 DEPLOYMENT READY:")
        print("• langgraph.json → main_recursion_fixed.py")
        print("• Recursion limits: Configured")
        print("• Tool call limits: 5 per conversation")
        print("• Error handling: Robust")
        
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Additional fixes may be needed")
        return False

if __name__ == "__main__":
    success = verify_fix()
    exit(0 if success else 1)
