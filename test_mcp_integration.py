#!/usr/bin/env python3
"""
Quick MCP Integration Test Runner

Run this script to test your MCP Salesforce integration with your credentials.
"""

import asyncio
import json
from mcp_integration_test import MCPIntegrationTester

# Example credentials format for quick testing
EXAMPLE_CREDENTIALS = {
    "instanceUrl": "https://your-org.my.salesforce.com",
    "accessToken": "your_access_token_here",
    "tokenType": "Bearer", 
    "refreshToken": "your_refresh_token_here",
    "scope": "refresh_token api",
    "authCode": "your_auth_code_here"
}

def get_user_credentials():
    """Get credentials from user input"""
    print("🔐 MCP Salesforce Integration Test")
    print("=" * 40)
    print()
    print("Please provide your Salesforce credentials.")
    print("You can either:")
    print("1. Enter them interactively")
    print("2. Paste them as JSON")
    print("3. Use example format (for demo)")
    print()
    
    choice = input("Choose option (1, 2, or 3): ").strip()
    
    if choice == "1":
        # Interactive input
        credentials = {}
        credentials['instanceUrl'] = input("Instance URL: ").strip()
        
        print("\nAuthentication method:")
        print("1. Access Token")
        print("2. Authorization Code")
        auth_choice = input("Choose (1 or 2): ").strip()
        
        if auth_choice == "1":
            credentials['accessToken'] = input("Access Token: ").strip()
            credentials['tokenType'] = input("Token Type (default: Bearer): ").strip() or "Bearer"
        else:
            credentials['authCode'] = input("Authorization Code: ").strip()
        
        return credentials
    
    elif choice == "2":
        # JSON input
        print("\nPaste your JSON credentials (press Enter when done):")
        json_input = input().strip()
        try:
            return json.loads(json_input)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            return None
    
    elif choice == "3":
        # Example format
        print("\n📋 Using example format:")
        print(json.dumps(EXAMPLE_CREDENTIALS, indent=2))
        print("\n⚠️  Note: These are example credentials and won't work for actual testing.")
        print("Replace with your real credentials.")
        return EXAMPLE_CREDENTIALS
    
    else:
        print("Invalid choice.")
        return None

async def main():
    """Main test runner"""
    print("🚀 MCP Salesforce Integration Test Runner")
    print("=" * 50)
    
    # Get credentials
    credentials = get_user_credentials()
    if not credentials:
        print("❌ No valid credentials provided. Exiting.")
        return
    
    # Run the test
    tester = MCPIntegrationTester()
    
    try:
        print("\n🔥 Starting comprehensive integration test...")
        results = await tester.run_comprehensive_test(credentials)
        
        # Print results
        if results['success']:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ MCP Salesforce integration is working correctly")
            print(f"✅ {len(results['stages'])} test stages completed successfully")
            
            if 'test_record' in results['stages']:
                record_id = results['stages']['test_record'].get('record_id')
                if record_id:
                    print(f"✅ Test Lead record created: {record_id}")
        else:
            print("\n❌ SOME TESTS FAILED")
            print("Check the output above for details")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
