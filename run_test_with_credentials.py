#!/usr/bin/env python3
"""
Run MCP Integration Test with Provided Credentials
"""

import asyncio
import json
from mcp_integration_test import MCPIntegrationTester

# PLACEHOLDER CREDENTIALS - Replace with your real credentials
CREDENTIALS = {
    "instanceUrl": "https://your-org.my.salesforce.com",
    "accessToken": "your_access_token_here",
    "tokenType": "Bearer",
    "refreshToken": "your_refresh_token_here",
    "scope": "refresh_token api", 
    "authCode": "your_auth_code_here"
}

async def main():
    """Run the comprehensive test with your credentials"""
    print("🚀 RUNNING MCP SALESFORCE INTEGRATION TEST")
    print("=" * 60)
    print(f"🌐 Instance URL: {CREDENTIALS['instanceUrl']}")
    print(f"🔑 Using Access Token: {'✅ YES' if CREDENTIALS.get('accessToken') else '❌ NO'}")
    print(f"🔄 Refresh Token Available: {'✅ YES' if CREDENTIALS.get('refreshToken') else '❌ NO'}")
    print(f"📜 Scope: {CREDENTIALS.get('scope', 'Not specified')}")
    print()
    
    # Initialize the tester
    tester = MCPIntegrationTester()
    
    try:
        # Run the comprehensive test
        results = await tester.run_comprehensive_test(CREDENTIALS)
        
        print("\n" + "="*60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)
        
        if results['success']:
            print("🎉 SUCCESS! All integration tests passed!")
            print()
            
            # Detailed results
            for stage_name, stage_result in results['stages'].items():
                status_emoji = "✅" if stage_result.get('success') else "❌"
                print(f"{status_emoji} {stage_name.replace('_', ' ').title()}")
                
                # Special handling for specific stages
                if stage_name == 'connection' and 'tools_count' in stage_result:
                    print(f"   └── Found {stage_result['tools_count']} MCP tools available")
                
                if stage_name == 'test_record' and stage_result.get('record_id'):
                    print(f"   └── Created Lead record: {stage_result['record_id']}")
                    
        else:
            print("❌ SOME TESTS FAILED")
            print("Check the detailed output above for specific failures")
            
            # Show which stages failed
            for stage_name, stage_result in results['stages'].items():
                if not stage_result.get('success'):
                    print(f"❌ Failed: {stage_name.replace('_', ' ').title()}")
        
        print("\n🎯 Integration test completed!")
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
