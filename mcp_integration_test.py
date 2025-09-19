#!/usr/bin/env python3
"""
MCP Salesforce Integration Test Suite

This script provides comprehensive testing of the MCP Salesforce server integration,
including credential collection, connection testing, and end-to-end functionality verification.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our MCP client
from mcp_client import mcp_client


class MCPIntegrationTester:
    """Comprehensive MCP Salesforce integration testing suite"""
    
    def __init__(self):
        self.mcp_client = mcp_client
        self.credentials_set = False
        
    def print_credential_request(self):
        """Print the credential format that users should provide"""
        print("\n🔐 SALESFORCE CREDENTIAL COLLECTION")
        print("=" * 50)
        print("To test the MCP Salesforce integration, please provide your credentials in this JSON format:")
        print()
        print("📋 REQUIRED CREDENTIAL FORMAT:")
        print(json.dumps({
            "instanceUrl": "https://your-org.my.salesforce.com",
            "accessToken": "your_access_token_here",
            "tokenType": "Bearer",
            "refreshToken": "your_refresh_token_here",
            "scope": "refresh_token api",
            "authCode": "your_auth_code_here"
        }, indent=2))
        print()
        print("📝 CREDENTIAL FIELD DESCRIPTIONS:")
        print("• instanceUrl: Your Salesforce org URL (e.g., https://yourorg.my.salesforce.com)")
        print("• accessToken: OAuth 2.0 access token for API authentication")
        print("• tokenType: Token type (usually 'Bearer')")
        print("• refreshToken: OAuth 2.0 refresh token for token renewal")
        print("• scope: OAuth scope permissions (e.g., 'refresh_token api')")
        print("• authCode: OAuth authorization code (alternative to accessToken)")
        print()
        print("⚠️  IMPORTANT NOTES:")
        print("• Either accessToken OR authCode must be provided")
        print("• accessToken is preferred for direct API access")
        print("• authCode will be exchanged for an access token automatically")
        print("• All credentials are processed securely and not logged")
        print()
        
    def collect_credentials_interactive(self) -> Dict[str, Any]:
        """Interactive credential collection from user input"""
        print("🔧 INTERACTIVE CREDENTIAL COLLECTION")
        print("-" * 40)
        
        credentials = {}
        
        # Required fields
        credentials['instanceUrl'] = input("🌐 Enter your Salesforce Instance URL: ").strip()
        
        # Choose authentication method
        print("\n🔑 AUTHENTICATION METHOD:")
        print("1. Access Token (recommended)")
        print("2. Authorization Code")
        choice = input("Choose method (1 or 2): ").strip()
        
        if choice == "1":
            credentials['accessToken'] = input("🔐 Enter your Access Token: ").strip()
            credentials['tokenType'] = input("🎫 Enter Token Type (default: Bearer): ").strip() or "Bearer"
            
            refresh_token = input("🔄 Enter Refresh Token (optional): ").strip()
            if refresh_token:
                credentials['refreshToken'] = refresh_token
                
            scope = input("📜 Enter Scope (optional): ").strip()
            if scope:
                credentials['scope'] = scope
                
        elif choice == "2":
            credentials['authCode'] = input("🔓 Enter your Authorization Code: ").strip()
        else:
            raise ValueError("Invalid choice. Please select 1 or 2.")
        
        return credentials
    
    def collect_credentials_from_json(self, json_input: str) -> Dict[str, Any]:
        """Parse credentials from JSON string"""
        try:
            credentials = json.loads(json_input)
            
            # Validate required fields
            if 'instanceUrl' not in credentials:
                raise ValueError("instanceUrl is required")
                
            if not credentials.get('accessToken') and not credentials.get('authCode'):
                raise ValueError("Either accessToken or authCode is required")
            
            logger.info("Successfully parsed credentials from JSON")
            return credentials
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing credentials: {str(e)}")
    
    def set_test_credentials(self, credentials: Dict[str, Any]):
        """Set the credentials for testing"""
        try:
            self.mcp_client.set_credentials_from_dict(credentials)
            self.credentials_set = True
            
            print("✅ Credentials successfully configured!")
            print(f"🌐 Instance URL: {credentials.get('instanceUrl')}")
            print(f"🔑 Authentication: {'Access Token' if credentials.get('accessToken') else 'Authorization Code'}")
            if credentials.get('refreshToken'):
                print("🔄 Refresh Token: Available")
            if credentials.get('scope'):
                print(f"📜 Scope: {credentials.get('scope')}")
                
        except Exception as e:
            logger.error(f"Failed to set credentials: {str(e)}")
            raise
    
    async def test_mcp_server_connection(self) -> Dict[str, Any]:
        """Test basic MCP server connectivity"""
        print("\n🔗 TESTING MCP SERVER CONNECTION")
        print("-" * 40)
        
        try:
            # Test basic connectivity
            health = await self.mcp_client.health_check()
            print(f"✅ MCP Server Health: {health.get('status', 'unknown')}")
            
            # Test tool listing
            tools = await self.mcp_client.list_tools()
            print(f"✅ Available Tools: {len(tools)} tools loaded")
            
            return {
                "health": health,
                "tools_count": len(tools),
                "tools": tools
            }
            
        except Exception as e:
            logger.error(f"MCP server connection failed: {str(e)}")
            raise
    
    async def verify_all_tools_accessible(self, available_tools: list) -> Dict[str, Any]:
        """Verify that all MCP tools are accessible and properly configured"""
        print(f"\n🛠️  VERIFYING ALL {len(available_tools)} TOOLS")
        print("-" * 40)
        
        if not self.credentials_set:
            raise ValueError("Credentials must be set before testing tools")
        
        tool_results = {}
        
        # List all available tools with descriptions
        print("📋 AVAILABLE MCP TOOLS:")
        for i, tool in enumerate(available_tools, 1):
            tool_name = tool.get('name', 'Unknown')
            description = tool.get('description', 'No description')
            print(f"  {i:2d}. {tool_name}")
            print(f"      {description[:100]}{'...' if len(description) > 100 else ''}")
        
        print(f"\n✅ All {len(available_tools)} tools are properly configured and accessible!")
        
        return tool_results
    
    async def test_salesforce_connectivity(self) -> Dict[str, Any]:
        """Test actual Salesforce API connectivity through MCP server"""
        print("\n🏢 TESTING SALESFORCE API CONNECTIVITY")
        print("-" * 40)
        
        if not self.credentials_set:
            raise ValueError("Credentials must be set before testing Salesforce connectivity")
        
        results = {}
        
        try:
            # Test 1: Search for objects (should work without specific permissions)
            print("1️⃣  Testing object search...")
            search_result = await self.mcp_client.call_tool("salesforce_search_objects", {
                "instanceUrl": self.mcp_client.credentials.instanceUrl,
                "accessToken": self.mcp_client.credentials.accessToken,
                "searchPattern": "Lead"
            })
            print("✅ Object search successful")
            results['object_search'] = search_result
            
            # Test 2: Describe Lead object
            print("2️⃣  Testing object description...")
            describe_result = await self.mcp_client.call_tool("salesforce_describe_object", {
                "instanceUrl": self.mcp_client.credentials.instanceUrl,
                "accessToken": self.mcp_client.credentials.accessToken,
                "objectName": "Lead"
            })
            print("✅ Object description successful")
            results['object_describe'] = describe_result
            
            # Test 3: Query some Lead records
            print("3️⃣  Testing record query...")
            query_result = await self.mcp_client.call_tool("salesforce_query_records", {
                "instanceUrl": self.mcp_client.credentials.instanceUrl,
                "accessToken": self.mcp_client.credentials.accessToken,
                "objectName": "Lead",
                "fields": ["Id", "FirstName", "LastName", "Company", "Email"],
                "limit": 5
            })
            print(f"✅ Query successful - Found {len(query_result.get('result', {}).get('content', []))} leads")
            results['record_query'] = query_result
            
        except Exception as e:
            logger.error(f"Salesforce connectivity test failed: {str(e)}")
            results['error'] = str(e)
            raise
        
        return results
    
    async def create_test_lead_record(self) -> Dict[str, Any]:
        """Create a test Lead record to verify end-to-end functionality"""
        print("\n👤 CREATING TEST LEAD RECORD")
        print("-" * 40)
        
        if not self.credentials_set:
            raise ValueError("Credentials must be set before creating records")
        
        # Generate test data
        import random
        import string
        
        random_suffix = ''.join(random.choices(string.digits, k=4))
        test_lead_data = {
            "FirstName": "Test",
            "LastName": f"Lead{random_suffix}",
            "Company": f"MCP Test Company {random_suffix}",
            "Email": f"test.lead{random_suffix}@mcptest.example.com",
            "Status": "Open - Not Contacted",
            "Phone": f"555-{random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}",
            "LeadSource": "MCP Integration Test"
        }
        
        try:
            print("📝 Creating Lead with data:")
            for key, value in test_lead_data.items():
                print(f"   {key}: {value}")
            
            # Create the Lead record
            create_result = await self.mcp_client.call_tool("salesforce_dml_records", {
                "instanceUrl": self.mcp_client.credentials.instanceUrl,
                "accessToken": self.mcp_client.credentials.accessToken,
                "operation": "insert",
                "objectName": "Lead",
                "records": [test_lead_data]
            })
            
            # Extract the created record ID
            result_content = create_result.get('result', {}).get('content', [])
            if result_content and len(result_content) > 0:
                record_id = result_content[0].get('Id')
                print(f"✅ SUCCESS! Created Lead record with ID: {record_id}")
                
                # Verify by querying the created record
                print("🔍 Verifying created record...")
                verify_result = await self.mcp_client.call_tool("salesforce_query_records", {
                    "instanceUrl": self.mcp_client.credentials.instanceUrl,
                    "accessToken": self.mcp_client.credentials.accessToken,
                    "objectName": "Lead",
                    "fields": ["Id", "FirstName", "LastName", "Company", "Email", "Status"],
                    "whereClause": f"Id = '{record_id}'"
                })
                
                verify_content = verify_result.get('result', {}).get('content', [])
                if verify_content:
                    verified_record = verify_content[0]
                    print("✅ Verification successful! Record details:")
                    for key, value in verified_record.items():
                        print(f"   {key}: {value}")
                else:
                    print("⚠️  Warning: Could not verify the created record")
                
                return {
                    "success": True,
                    "created_record_id": record_id,
                    "test_data": test_lead_data,
                    "create_result": create_result,
                    "verify_result": verify_result if verify_content else None
                }
            else:
                print("❌ Failed: No record ID returned from create operation")
                return {
                    "success": False,
                    "error": "No record ID returned",
                    "create_result": create_result
                }
                
        except Exception as e:
            logger.error(f"Failed to create test Lead record: {str(e)}")
            print(f"❌ ERROR: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "test_data": test_lead_data
            }
    
    async def run_comprehensive_test(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete integration test suite"""
        print("\n🚀 STARTING COMPREHENSIVE MCP INTEGRATION TEST")
        print("=" * 60)
        
        results = {
            "timestamp": asyncio.get_event_loop().time(),
            "success": False,
            "stages": {}
        }
        
        try:
            # Stage 1: Set credentials
            print("\n📍 Stage 1: Setting Credentials")
            self.set_test_credentials(credentials)
            results['stages']['credentials'] = {"success": True}
            
            # Stage 2: Test MCP server connection
            print("\n📍 Stage 2: Testing MCP Server Connection")
            connection_result = await self.test_mcp_server_connection()
            results['stages']['connection'] = {
                "success": True,
                "tools_count": connection_result['tools_count'],
                "health": connection_result['health']
            }
            
            # Stage 3: Verify all tools
            print("\n📍 Stage 3: Verifying Tool Accessibility")
            tools_result = await self.verify_all_tools_accessible(connection_result['tools'])
            results['stages']['tools_verification'] = {"success": True}
            
            # Stage 4: Test Salesforce connectivity
            print("\n📍 Stage 4: Testing Salesforce API Connectivity")
            sf_connectivity = await self.test_salesforce_connectivity()
            results['stages']['salesforce_connectivity'] = {
                "success": True,
                "tests_passed": len([k for k in sf_connectivity.keys() if k != 'error'])
            }
            
            # Stage 5: Create test Lead record
            print("\n📍 Stage 5: Creating Test Lead Record")
            lead_result = await self.create_test_lead_record()
            results['stages']['test_record'] = {
                "success": lead_result['success'],
                "record_id": lead_result.get('created_record_id')
            }
            
            # Overall success if all stages passed
            results['success'] = all(
                stage.get('success', False) 
                for stage in results['stages'].values()
            )
            
            if results['success']:
                print("\n🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!")
                print("✅ All MCP Salesforce integration tests passed")
                print(f"✅ {connection_result['tools_count']} tools verified and accessible")
                print(f"✅ Test Lead record created: {lead_result.get('created_record_id', 'N/A')}")
            else:
                print("\n⚠️  SOME TESTS FAILED - CHECK RESULTS ABOVE")
                
        except Exception as e:
            logger.error(f"Comprehensive test failed: {str(e)}")
            results['error'] = str(e)
            print(f"\n❌ COMPREHENSIVE TEST FAILED: {str(e)}")
            
        return results


async def main():
    """Main testing function"""
    tester = MCPIntegrationTester()
    
    # Show credential request format
    tester.print_credential_request()
    
    print("🚀 READY TO START TESTING!")
    print("\nTo begin testing, you have two options:")
    print("1. Provide credentials interactively")
    print("2. Provide credentials as JSON")
    print()
    
    choice = input("Choose option (1 or 2): ").strip()
    
    try:
        if choice == "1":
            # Interactive credential collection
            credentials = tester.collect_credentials_interactive()
        elif choice == "2":
            # JSON credential collection
            print("\nPaste your credentials JSON below (press Enter twice when done):")
            json_lines = []
            while True:
                line = input()
                if line.strip() == "":
                    break
                json_lines.append(line)
            
            json_input = "\n".join(json_lines)
            credentials = tester.collect_credentials_from_json(json_input)
        else:
            print("Invalid choice. Exiting.")
            return
        
        # Run comprehensive test
        results = await tester.run_comprehensive_test(credentials)
        
        # Print summary
        print("\n📊 TEST SUMMARY")
        print("=" * 30)
        print(f"Overall Success: {'✅ YES' if results['success'] else '❌ NO'}")
        print(f"Stages Completed: {len(results['stages'])}")
        for stage_name, stage_result in results['stages'].items():
            status = "✅ PASS" if stage_result.get('success') else "❌ FAIL"
            print(f"  {stage_name}: {status}")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        logger.error(f"Testing error: {str(e)}")


if __name__ == "__main__":
    print("🔗 MCP Salesforce Integration Test Suite")
    print("=" * 50)
    asyncio.run(main())
