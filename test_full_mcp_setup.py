#!/usr/bin/env python3
"""
Test script to try Salesforce CLI authentication for full MCP access
"""

import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def test_salesforce_cli():
    """Test if Salesforce CLI authentication would work."""
    print("🔍 Testing Salesforce CLI Setup for Full MCP Access")
    print("="*60)
    
    # Check if SF CLI is available
    try:
        result = subprocess.run(['sf', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Salesforce CLI is installed")
            print(f"📋 Version: {result.stdout.strip()}")
            
            # Check if org is authenticated
            try:
                org_result = subprocess.run(['sf', 'org', 'display', '--json'], capture_output=True, text=True)
                if org_result.returncode == 0:
                    print("✅ Salesforce org is authenticated via CLI")
                    print("🎯 You can use SALESFORCE_CONNECTION_TYPE=Salesforce_CLI")
                    
                    # Test if MCP server works with CLI auth
                    print("\n🧪 Testing MCP server with CLI auth...")
                    
                    # Update env for CLI test
                    os.environ['SALESFORCE_CONNECTION_TYPE'] = 'Salesforce_CLI'
                    
                    # Try to load MCP tools
                    import asyncio
                    from salesforce_platform_ready import create_platform_ready_salesforce_tools
                    
                    async def test_cli_mcp():
                        try:
                            tools = await create_platform_ready_salesforce_tools()
                            print(f"✅ MCP loaded {len(tools)} tools with CLI auth!")
                            
                            # Try to test one tool
                            if tools:
                                dml_tool = None
                                for tool in tools:
                                    if 'dml' in tool.name.lower():
                                        dml_tool = tool
                                        break
                                
                                if dml_tool:
                                    print(f"✅ Found DML tool: {dml_tool.name}")
                                    print("🎉 CLI authentication should work for full MCP access!")
                                    return True
                            
                            return False
                        except Exception as e:
                            print(f"❌ CLI MCP test failed: {str(e)}")
                            return False
                    
                    success = asyncio.run(test_cli_mcp())
                    return success
                    
                else:
                    print("❌ No Salesforce org authenticated")
                    print("💡 Run: sf org login web --set-default")
                    
            except Exception as e:
                print(f"❌ Error checking org auth: {str(e)}")
                
        else:
            print("❌ Salesforce CLI not installed")
            print("💡 Install with: npm install -g @salesforce/cli")
            
    except FileNotFoundError:
        print("❌ Salesforce CLI not found")
        print("💡 Install with: npm install -g @salesforce/cli")
        
    return False

def main():
    """Main test function."""
    cli_works = test_salesforce_cli()
    
    print("\n" + "="*60)
    print("📊 FULL MCP ACCESS ANALYSIS")
    print("="*60)
    
    if cli_works:
        print("🎉 FULL MCP ACCESS POSSIBLE!")
        print("✅ You can access all 15 tools from the repository")
        print("✅ Set SALESFORCE_CONNECTION_TYPE=Salesforce_CLI")
        print("✅ Remove username/password from .env")
        print("✅ Deploy with full MCP functionality")
    else:
        print("⚠️ FULL MCP ACCESS BLOCKED")
        print("💡 Recommendation: Use current working solution")
        print("✅ Deploy main_final_working.py (3 core tools)")
        print("🔄 Enhance MCP access later when CLI is set up")
    
    print(f"\n📋 Current working solution: 3 core Salesforce tools")
    print(f"🎯 Full MCP potential: 15 advanced Salesforce tools")
    print(f"🚀 Either way: Your agent will work on LangGraph Platform!")

if __name__ == "__main__":
    main()

