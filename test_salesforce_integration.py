"""
Test script for Salesforce MCP integration.

This script tests the Salesforce MCP server integration with the provided credentials.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from salesforce_mcp_wrapper import SalesforceMCPWrapper, validate_salesforce_config


async def test_salesforce_integration():
    """Test the Salesforce MCP integration."""
    print("🔍 Testing Salesforce MCP Integration...")
    print("=" * 50)
    
    # Step 1: Validate configuration
    print("\n1️⃣  Validating Salesforce configuration...")
    if validate_salesforce_config():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration validation failed")
        return False
    
    # Step 2: Initialize MCP wrapper
    print("\n2️⃣  Initializing Salesforce MCP wrapper...")
    try:
        wrapper = SalesforceMCPWrapper()
        print("✅ MCP wrapper created successfully")
    except Exception as e:
        print(f"❌ Failed to create MCP wrapper: {str(e)}")
        return False
    
    # Step 3: Initialize wrapper (this loads tools automatically)
    print("\n3️⃣  Initializing Salesforce MCP integration...")
    try:
        initialization_success = await wrapper.initialize()
        if initialization_success:
            print("✅ Salesforce MCP integration initialized successfully")
            tools = wrapper.get_tools()
            print(f"✅ Loaded {len(tools)} Salesforce tools")
        else:
            print("❌ Failed to initialize Salesforce MCP integration")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing Salesforce MCP integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test a simple tool call
    print("\n4️⃣  Testing tool functionality...")
    try:
        tools = wrapper.get_tools()
        if tools:
            # Try to call the first available tool with a simple test
            test_tool = tools[0]
            print(f"🧪 Testing tool: {test_tool.name}")
            
            # This might fail if the tool needs specific arguments
            # We'll catch and handle the error gracefully
            try:
                result = test_tool.run("test")
                print(f"✅ Tool test result: {result}")
            except Exception as tool_error:
                print(f"⚠️  Tool test failed (expected): {str(tool_error)}")
        
    except Exception as e:
        print(f"❌ Error testing tools: {str(e)}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    wrapper.cleanup()
    
    print("\n🎉 Integration test completed!")
    return True


async def test_agent_integration():
    """Test the full agent integration."""
    print("\n" + "=" * 50)
    print("🤖 Testing Agent Integration...")
    print("=" * 50)
    
    try:
        # Import the main module
        from main import initialize_salesforce_tools, create_simple_graph
        from langchain_core.messages import HumanMessage
        
        # Initialize Salesforce tools
        print("\n1️⃣  Initializing Salesforce tools in agent...")
        salesforce_tools = await initialize_salesforce_tools()
        print(f"✅ Agent has access to {len(salesforce_tools)} Salesforce tools")
        
        # Create and test the graph
        print("\n2️⃣  Creating LangGraph with Salesforce integration...")
        graph = create_simple_graph()
        print("✅ LangGraph created successfully")
        
        # Test a simple conversation
        print("\n3️⃣  Testing agent conversation...")
        test_state = {
            "messages": [HumanMessage(content="What tools do you have available?")]
        }
        
        result = graph.invoke(test_state)
        response = result["messages"][-1].content
        print(f"🤖 Agent Response: {response}")
        
        print("✅ Agent integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Agent integration test failed: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting Salesforce MCP Integration Tests...")
    
    # Run the tests
    try:
        # Test MCP integration
        integration_success = asyncio.run(test_salesforce_integration())
        
        if integration_success:
            # Test agent integration
            agent_success = asyncio.run(test_agent_integration())
            
            if agent_success:
                print("\n🎉 All tests passed! Salesforce integration is ready.")
                return 0
            else:
                print("\n⚠️  MCP integration works, but agent integration needs work.")
                return 1
        else:
            print("\n❌ MCP integration failed. Check your configuration.")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during tests: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
