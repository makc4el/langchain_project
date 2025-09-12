# 📁 Project Structure

## Core Application Files
```
main_recursion_fixed.py          # Main LangGraph agent (production)
salesforce_mcp_wrapper.py        # Salesforce MCP integration wrapper
salesforce_platform_ready.py     # Platform-ready Salesforce tools
langgraph.json                   # LangGraph platform configuration
pyproject.toml                   # Python project dependencies
```

## Documentation
```
README.md                        # Project overview and setup
DEPLOYMENT_GUIDE.md             # Complete deployment guide and troubleshooting
PROJECT_STRUCTURE.md            # This file - project organization
```

## Test Suite
```
test/
├── README.md                   # Test documentation
├── run_tests.py               # Main test runner
├── test_salesforce_integration.py    # Salesforce integration tests
├── test_recursion_fix.py       # Recursion fix validation tests
├── demo_salesforce_agent.py    # Interactive demo script
├── test_client.py             # Platform client tests
├── test_deployment.py         # Deployment tests
└── *.sh                       # Shell script tests
```

## Key Features
- ✅ **GraphRecursionError Fixed**: Intelligent tool call limits and stop conditions
- ✅ **Salesforce Integration**: Full MCP support with platform fallbacks  
- ✅ **Platform Ready**: Works on LangGraph Platform with automatic degradation
- ✅ **Comprehensive Testing**: Full test suite with recursion validation
- ✅ **Clean Codebase**: Unused imports removed, redundant files cleaned up

## Active Configuration
- **Main Entry Point**: `main_recursion_fixed.py`
- **Graph Types**: `graph` (simple) and `advanced_graph` (with session management)
- **Tool Call Limit**: 5 per conversation
- **Recursion Limit**: 15 (configurable)
- **Salesforce Tools**: 3-15 tools depending on platform capabilities
