#!/usr/bin/env python3
"""
Test Runner for LangChain Salesforce Project

This script runs all tests in the test directory with proper setup.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_command(command, description):
    """Run a command and display results."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print('='*60)
    
    try:
        result = subprocess.run(
            command,
            cwd=Path(__file__).parent,
            shell=True,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ {description} - ERROR: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("🧪 LangChain Salesforce Project Test Suite")
    print("=" * 60)
    
    # Change to test directory
    os.chdir(Path(__file__).parent)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Salesforce Integration Test
    tests_total += 1
    if run_command("uv run python test_salesforce_integration.py", "Salesforce Integration Test"):
        tests_passed += 1
    
    # Test 2: Platform Deployment Test (if exists)
    if Path("test_deployment.py").exists():
        tests_total += 1
        if run_command("uv run python test_deployment.py", "Platform Deployment Test"):
            tests_passed += 1
    
    # Test 3: Recursion Fix Test
    tests_total += 1
    if run_command("uv run python test_recursion_fix.py", "Recursion Fix Comprehensive Test"):
        tests_passed += 1
    
    # Test 4: Demo Script (non-interactive check)
    tests_total += 1 
    if run_command("uv run python -c 'import demo_salesforce_agent; print(\"✅ Demo script imports successfully\")'", "Demo Script Import Test"):
        tests_passed += 1
    
    # Test 5: Shell scripts (if they exist and are executable)
    shell_scripts = ["test_deployment.sh", "test_endpoints.sh", "chat_with_deployment.sh"]
    for script in shell_scripts:
        script_path = Path(script)
        if script_path.exists() and os.access(script_path, os.X_OK):
            tests_total += 1
            if run_command(f"./{script}", f"Shell Script Test: {script}"):
                tests_passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST RESULTS SUMMARY")
    print('='*60)
    print(f"✅ Tests Passed: {tests_passed}")
    print(f"❌ Tests Failed: {tests_total - tests_passed}")
    print(f"📊 Total Tests: {tests_total}")
    
    if tests_passed == tests_total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("✅ Your Salesforce integration is working correctly!")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
