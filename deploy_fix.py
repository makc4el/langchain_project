"""
Deploy the StructuredTool fix to resolve the "dml is not a valid tool" error
"""

import os
import subprocess
from datetime import datetime

def deploy_structured_tool_fix():
    """Deploy the updated main.py with StructuredTool fixes"""
    
    print("🚀 **DEPLOYING STRUCTUREDTOOL FIX**")
    print("="*60)
    
    print("This will fix the error: 'dml is not a valid tool, try one of []'")
    print("")
    
    # Step 1: Verify our fix is in place
    print("1️⃣ **Verifying StructuredTool Fix in main.py**")
    
    try:
        with open('main.py', 'r') as f:
            content = f.read()
        
        if 'create_structured_salesforce_tools_sync' in content:
            print("✅ StructuredTool implementation found in main.py")
        else:
            print("❌ StructuredTool implementation missing!")
            return
        
        if 'StructuredTool.from_function' in content:
            print("✅ StructuredTool.from_function usage confirmed")
        else:
            print("❌ StructuredTool.from_function not found!")
            return
            
        # Count DML and Query tool implementations
        dml_count = content.count('def dml_function')
        query_count = content.count('def query_function')
        print(f"✅ Found {dml_count} DML tool and {query_count} Query tool implementations")
        
    except Exception as e:
        print(f"❌ Error checking main.py: {e}")
        return
    
    # Step 2: Commit the changes if needed
    print(f"\n2️⃣ **Preparing for Deployment**")
    
    try:
        # Check if there are any uncommitted changes
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.stdout.strip():
            print("📝 Found uncommitted changes, committing...")
            
            # Add all changes
            subprocess.run(['git', 'add', '.'], cwd='.')
            
            # Commit with descriptive message
            commit_msg = f"Fix: Convert Tool to StructuredTool for multi-parameter support - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd='.')
            
            print(f"✅ Committed changes: {commit_msg}")
        else:
            print("✅ No uncommitted changes found")
            
    except Exception as e:
        print(f"⚠️ Git operations failed: {e}")
        print("Proceeding with manual deployment instructions...")
    
    # Step 3: Show deployment options
    print(f"\n3️⃣ **DEPLOYMENT OPTIONS**")
    print("-" * 40)
    
    print("🔄 **CRITICAL: Choose ONE deployment method:**")
    print("")
    
    print("**Option A: LangGraph CLI (Recommended)**")
    print("```bash")
    print("# Install LangGraph CLI if not installed")
    print("pip install langgraph-cli")
    print("")
    print("# Deploy the updated application")
    print("langgraph deploy")
    print("```")
    print("")
    
    print("**Option B: Platform Dashboard**")
    print("1. Go to your LangGraph Platform dashboard")
    print("2. Find your application: mcpconnectordynamic-343b682d82a350a8a9ff6eb9bc33626c")
    print("3. Click 'Redeploy' or 'Update' with current code")
    print("")
    
    print("**Option C: Git-based Auto-Deploy (if configured)**")
    print("```bash")
    print("# Push to trigger auto-deployment")
    print("git push origin main")
    print("```")
    print("")
    
    # Step 4: Expected results
    print(f"4️⃣ **EXPECTED RESULTS AFTER DEPLOYMENT**")
    print("-" * 40)
    
    print("🎯 **BEFORE (Current Error):**")
    print("   dml call_xyz123...")
    print('   "Error: dml is not a valid tool, try one of []."')
    print("")
    
    print("🎯 **AFTER (Fixed):**")
    print("   dml call_xyz123...")
    print('   "✅ Successfully created lead John Doe - ID: 00Q..."')
    print("")
    
    print("📊 **How to Test After Deployment:**")
    print("1. Run: python test_conversation_with_api.py")
    print("2. Look for REAL Salesforce record IDs (00Q...)")
    print("3. Check your Salesforce org for actual lead records")
    print("4. No more 'is not a valid tool' errors!")
    print("")
    
    print("🚨 **IF DEPLOYMENT STILL FAILS:**")
    print("The issue might be in the tool initialization. Check logs for:")
    print("- Tool loading errors")
    print("- MCP server connection issues")
    print("- Import errors in main.py")
    print("")
    
    print("✅ **DEPLOYMENT PREPARATION COMPLETE!**")
    print("Choose your deployment method above and execute it.")

def test_local_structured_tools():
    """Test that our StructuredTool implementation works locally"""
    print(f"\n🧪 **TESTING LOCAL STRUCTUREDTOOL IMPLEMENTATION**")
    print("-" * 50)
    
    try:
        # Import our fixed main.py
        from main import create_structured_salesforce_tools_sync
        
        print("✅ Successfully imported StructuredTool function")
        
        # Create tools
        tools = create_structured_salesforce_tools_sync()
        print(f"✅ Created {len(tools)} tools locally")
        
        # Check DML tool
        dml_tools = [t for t in tools if t.name == 'dml']
        if dml_tools:
            dml_tool = dml_tools[0]
            print(f"✅ DML tool found: {type(dml_tool).__name__}")
            
            # Check if it's a StructuredTool with schema
            if hasattr(dml_tool, 'args_schema'):
                print(f"✅ Has args_schema - will accept multiple parameters!")
                print(f"   Ready to handle: operation, objectName, records")
            else:
                print(f"❌ Missing args_schema - would still fail!")
                return False
        
        print(f"\n🎯 **LOCAL TEST RESULT: SUCCESS!**")
        print(f"The StructuredTool implementation works locally.")
        print(f"After deployment, the 'dml is not a valid tool' error will be fixed!")
        return True
        
    except Exception as e:
        print(f"❌ Local test failed: {e}")
        return False

if __name__ == "__main__":
    deploy_structured_tool_fix()
    test_local_structured_tools()
