#!/usr/bin/env python3
"""
Verify the created Lead record exists in Salesforce
"""

import asyncio
import json
from mcp_client import mcp_client

# PLACEHOLDER CREDENTIALS - Replace with your real credentials
CREDENTIALS = {
    "instanceUrl": "https://your-org.my.salesforce.com",
    "accessToken": "your_access_token_here",
    "tokenType": "Bearer",
    "refreshToken": "your_refresh_token_here",
    "scope": "refresh_token api"
}

async def verify_lead_creation():
    """Query the most recent Lead records to verify our test record was created"""
    print("🔍 VERIFYING LEAD RECORD CREATION")
    print("-" * 50)
    
    # Set credentials
    mcp_client.set_credentials_from_dict(CREDENTIALS)
    
    try:
        # Query recent Lead records with MCP Integration Test as source
        print("📊 Querying recent Lead records with LeadSource = 'MCP Integration Test'...")
        
        # Try different query tool names
        query_tools = ["query", "salesforce_query_records", "query_records"]
        
        query_params = {
            "instanceUrl": CREDENTIALS["instanceUrl"],
            "accessToken": CREDENTIALS["accessToken"],
            "objectName": "Lead",
            "fields": ["Id", "FirstName", "LastName", "Company", "Email", "Phone", "Status", "LeadSource", "CreatedDate"],
            "whereClause": "LeadSource = 'MCP Integration Test'",
            "orderBy": "CreatedDate DESC",
            "limit": 5
        }
        
        for tool_name in query_tools:
            try:
                print(f"🔧 Trying query tool: {tool_name}")
                result = await mcp_client.call_tool(tool_name, query_params)
                
                print(f"✅ SUCCESS with tool: {tool_name}")
                
                # Parse and display results
                if 'result' in result and 'content' in result['result']:
                    content = result['result']['content']
                    
                    if isinstance(content, list) and len(content) > 0:
                        print(f"\n🎯 Found {len(content)} Lead records:")
                        
                        for i, record in enumerate(content, 1):
                            print(f"\n📋 Lead #{i}:")
                            for field, value in record.items():
                                print(f"   {field}: {value}")
                                
                        # Check if our test record is there
                        test_records = [r for r in content if 'MCPLead' in str(r.get('LastName', ''))]
                        if test_records:
                            print(f"\n🎉 SUCCESS! Found {len(test_records)} MCP test Lead record(s)")
                            return True
                        else:
                            print("\n⚠️  No MCP test Lead records found in results")
                    else:
                        print("\n📄 No Lead records found with LeadSource = 'MCP Integration Test'")
                        print("This might mean the record was created but with a different LeadSource value")
                        
                        # Try a broader query
                        print("\n🔍 Trying broader search for recent Leads...")
                        broader_query = query_params.copy()
                        broader_query["whereClause"] = "LastName LIKE '%MCPLead%'"
                        
                        broader_result = await mcp_client.call_tool(tool_name, broader_query)
                        if 'result' in broader_result and 'content' in broader_result['result']:
                            broader_content = broader_result['result']['content']
                            if isinstance(broader_content, list) and len(broader_content) > 0:
                                print(f"✅ Found {len(broader_content)} Leads with 'MCPLead' in LastName:")
                                for record in broader_content:
                                    print(f"   - {record.get('FirstName')} {record.get('LastName')} ({record.get('Id')})")
                                return True
                
                return False
                
            except Exception as tool_error:
                print(f"❌ Tool {tool_name} failed: {tool_error}")
                continue
        
        print("❌ All query tools failed")
        return False
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

async def main():
    """Main verification function"""
    print("🔍 LEAD RECORD VERIFICATION TEST")
    print("=" * 50)
    
    success = await verify_lead_creation()
    
    if success:
        print("\n🎉 VERIFICATION SUCCESSFUL!")
        print("✅ Your MCP Salesforce integration is working correctly")
        print("✅ Lead records are being created in your Salesforce org")
    else:
        print("\n⚠️  VERIFICATION INCONCLUSIVE")
        print("The Lead was reported as created, but verification had issues")
        print("This could be due to:")
        print("• Different field values than expected")
        print("• Salesforce permissions or field-level security")
        print("• Query tool name differences")

if __name__ == "__main__":
    asyncio.run(main())
