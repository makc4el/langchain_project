#!/usr/bin/env python3
"""
Simple Lead Creation Test with Real Credentials
"""

import asyncio
import json
import logging
from mcp_client import mcp_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PLACEHOLDER CREDENTIALS - Replace with your real credentials
CREDENTIALS = {
    "instanceUrl": "https://your-org.my.salesforce.com",
    "accessToken": "your_access_token_here",
    "tokenType": "Bearer",
    "refreshToken": "your_refresh_token_here",
    "scope": "refresh_token api",
    "authCode": "your_auth_code_here"
}

async def test_mcp_connection():
    """Test basic MCP server connection and list available tools"""
    print("🔗 TESTING MCP SERVER CONNECTION")
    print("-" * 50)
    
    try:
        # Test server health
        health = await mcp_client.health_check()
        print(f"✅ MCP Server Health: {health.get('status')}")
        
        # List all available tools
        tools = await mcp_client.list_tools()
        print(f"✅ Available Tools: {len(tools)}")
        
        print("\n📋 EXACT TOOL NAMES:")
        for i, tool in enumerate(tools, 1):
            name = tool.get('name', 'Unknown')
            description = tool.get('description', 'No description')[:60] + "..."
            print(f"  {i:2d}. {name}")
            print(f"      {description}")
        
        return tools
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return []

async def create_test_lead():
    """Create a test Lead record using the MCP server"""
    print("\n👤 CREATING TEST LEAD RECORD")
    print("-" * 50)
    
    # Set credentials
    print("🔐 Setting Salesforce credentials...")
    mcp_client.set_credentials_from_dict(CREDENTIALS)
    print("✅ Credentials configured!")
    
    # Generate random test data
    import random
    import string
    
    random_suffix = ''.join(random.choices(string.digits, k=4))
    lead_data = {
        "FirstName": "TestUser",
        "LastName": f"MCPLead{random_suffix}",
        "Company": f"MCP Test Company {random_suffix}",
        "Email": f"testuser.mcplead{random_suffix}@example.com",
        "Status": "Open - Not Contacted",
        "Phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        "LeadSource": "MCP Integration Test"
    }
    
    print("📝 Lead data to create:")
    for key, value in lead_data.items():
        print(f"   {key}: {value}")
    
    try:
        # Try different possible tool names for DML operations
        possible_tool_names = [
            "salesforce_dml_records",
            "salesforce_dml", 
            "dml_records",
            "dml",
            "create_record",
            "salesforce_create_record"
        ]
        
        for tool_name in possible_tool_names:
            try:
                print(f"\n🔧 Trying tool: {tool_name}")
                result = await mcp_client.call_tool(tool_name, {
                    "instanceUrl": CREDENTIALS["instanceUrl"],
                    "accessToken": CREDENTIALS["accessToken"],
                    "operation": "insert",
                    "objectName": "Lead",
                    "records": [lead_data]
                })
                
                print(f"✅ SUCCESS with tool: {tool_name}")
                print("📄 Result:")
                print(json.dumps(result, indent=2))
                
                # Extract record ID if available
                if 'result' in result and 'content' in result['result']:
                    content = result['result']['content']
                    if isinstance(content, list) and len(content) > 0:
                        record_id = content[0].get('Id')
                        if record_id:
                            print(f"🎉 CREATED LEAD RECORD: {record_id}")
                            return record_id
                
                return "Record created successfully"
                
            except Exception as tool_error:
                print(f"❌ Tool {tool_name} failed: {tool_error}")
                continue
        
        print("❌ All tool attempts failed")
        return None
        
    except Exception as e:
        print(f"❌ Lead creation failed: {e}")
        return None

async def main():
    """Main test function"""
    print("🚀 SIMPLE MCP SALESFORCE LEAD CREATION TEST")
    print("=" * 60)
    print(f"🌐 Org: {CREDENTIALS['instanceUrl']}")
    print(f"🔑 Auth: Access Token")
    print()
    
    # Test connection first
    tools = await test_mcp_connection()
    
    if not tools:
        print("❌ Cannot proceed - MCP server connection failed")
        return
    
    # Create test Lead
    result = await create_test_lead()
    
    if result:
        print(f"\n🎉 SUCCESS! Lead creation completed: {result}")
    else:
        print("\n❌ FAILED! Could not create Lead record")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
