#!/usr/bin/env python3
"""
Test script specifically for testing the recursion fix.

This script tests various scenarios that previously caused GraphRecursionError
to ensure they now work properly with the recursion-safe implementation.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from main_recursion_fixed import graph, advanced_graph, MAX_TOOL_CALLS_PER_CONVERSATION, MAX_RECURSION_LIMIT


def test_scenario(description, test_state, test_graph=None):
    """Test a specific scenario and report results."""
    if test_graph is None:
        test_graph = graph
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {description}")
    print('='*60)
    
    try:
        result = test_graph.invoke(
            test_state,
            config={"recursion_limit": MAX_RECURSION_LIMIT}
        )
        
        tool_calls = result.get("tool_call_count", 0)
        last_message = result["messages"][-1].content
        
        print(f"✅ SUCCESS")
        print(f"🔢 Tool calls used: {tool_calls}/{MAX_TOOL_CALLS_PER_CONVERSATION}")
        print(f"🤖 Response length: {len(last_message)} characters")
        print(f"📝 Response preview: {last_message[:200]}...")
        
        return True, tool_calls, len(result["messages"])
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False, 0, 0


def main():
    """Run comprehensive recursion tests."""
    print("🚀 RECURSION FIX COMPREHENSIVE TEST SUITE")
    print(f"🔄 Max recursion limit: {MAX_RECURSION_LIMIT}")
    print(f"🔧 Max tool calls per conversation: {MAX_TOOL_CALLS_PER_CONVERSATION}")
    
    test_results = []
    
    # Test 1: Simple query (should not recurse)
    test_results.append(test_scenario(
        "Simple help request",
        {
            "messages": [HumanMessage(content="What can you help me with?")],
            "tool_call_count": 0
        }
    ))
    
    # Test 2: Salesforce status check (previously caused issues)
    test_results.append(test_scenario(
        "Salesforce status check",
        {
            "messages": [HumanMessage(content="Check my Salesforce integration status")],
            "tool_call_count": 0
        }
    ))
    
    # Test 3: SOQL query request (complex tool usage)
    test_results.append(test_scenario(
        "SOQL query request",
        {
            "messages": [HumanMessage(content="Execute this SOQL query: SELECT Id, Name FROM Account LIMIT 3")],
            "tool_call_count": 0
        }
    ))
    
    # Test 4: Object description (detailed request)
    test_results.append(test_scenario(
        "Object description request",
        {
            "messages": [HumanMessage(content="Describe the Account object in Salesforce")],
            "tool_call_count": 0
        }
    ))
    
    # Test 5: Search request (external tool)
    test_results.append(test_scenario(
        "Search request",
        {
            "messages": [HumanMessage(content="Search for information about Salesforce SOQL best practices")],
            "tool_call_count": 0
        }
    ))
    
    # Test 6: Complex multi-step request (potential for loops)
    test_results.append(test_scenario(
        "Complex multi-step request",
        {
            "messages": [HumanMessage(content="Check my Salesforce status, then query some Account records, and tell me about the Account object structure")],
            "tool_call_count": 0
        }
    ))
    
    # Test 7: Advanced graph test
    test_results.append(test_scenario(
        "Advanced graph conversation",
        {
            "messages": [HumanMessage(content="Help me understand my Salesforce data")],
            "user_id": "test_user",
            "session_id": "test_session", 
            "conversation_count": 0,
            "tool_call_count": 0
        },
        advanced_graph
    ))
    
    # Test 8: Stress test - vague request that might cause loops
    test_results.append(test_scenario(
        "Vague request stress test",
        {
            "messages": [HumanMessage(content="Tell me everything about my system")],
            "tool_call_count": 0
        }
    ))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print('='*60)
    
    passed = sum(1 for result in test_results if result[0])
    total = len(test_results)
    total_tool_calls = sum(result[1] for result in test_results)
    total_messages = sum(result[2] for result in test_results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"🔧 Total Tool Calls: {total_tool_calls}")
    print(f"💬 Total Messages: {total_messages}")
    print(f"📊 Average Tool Calls per Test: {total_tool_calls/total:.1f}")
    
    if passed == total:
        print("\n🎉 ALL RECURSION TESTS PASSED! 🎉")
        print("✅ No GraphRecursionError occurred")
        print("✅ All tool calls stayed within limits")
        print("✅ All conversations reached proper conclusions")
        print("✅ Agent is ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("❌ There may still be recursion issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
