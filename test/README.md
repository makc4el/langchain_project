# Test Suite for LangChain Salesforce Project

This directory contains all test and demo files for the LangChain agent with Salesforce MCP integration.

## Test Files

### Core Integration Tests
- **`test_salesforce_integration.py`** - Comprehensive Salesforce MCP integration testing
- **`demo_salesforce_agent.py`** - Interactive demo showing agent capabilities

### Platform Deployment Tests  
- **`test_deployment.py`** - Platform deployment testing
- **`test_client.py`** - Client interaction testing
- **`test_endpoints.sh`** - API endpoint testing
- **`test_deployment.sh`** - Deployment script testing
- **`chat_with_deployment.sh`** - Interactive deployment chat testing

## Running Tests

### Salesforce Integration Test
```bash
# From project root
cd test
python test_salesforce_integration.py
```

### Demo Agent
```bash  
# From project root
cd test
python demo_salesforce_agent.py
```

### Platform Deployment Tests
```bash
# From project root
cd test
python test_deployment.py
./test_deployment.sh
./test_endpoints.sh
```

## Requirements

All tests require:
- Project dependencies installed (`uv install`)
- Environment variables configured (`.env` file in project root)
- For Salesforce tests: Valid Salesforce credentials

## Test Environment Setup

The test files automatically:
1. Add the parent directory to Python path for imports
2. Load environment variables from project root `.env`
3. Import required modules from the main project

## Expected Outputs

### ✅ Successful Test Run
```
🚀 Starting Salesforce MCP Integration Tests...
✅ Configuration valid for user: your_user@domain.com
✅ Loaded 15 Salesforce tools
🎉 All tests passed! Salesforce integration is ready.
```

### ⚠️ Fallback Mode
```
🔄 Falling back to direct API integration
✅ Created 2 fallback Salesforce tools
⚠️ MCP integration works, but agent integration needs work.
```

## Troubleshooting

Common issues:
- **Import errors**: Ensure you're running from the test directory
- **Environment variables**: Check `.env` file in project root
- **Salesforce auth**: Verify credentials are correct and org is accessible
- **Dependencies**: Run `uv install` from project root
