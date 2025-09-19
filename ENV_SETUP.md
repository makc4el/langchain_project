# 🔐 Environment Variables Setup

## Required Environment Variables

Before running any tests, set these environment variables with your actual Salesforce credentials:

```bash
# LangGraph API Key (get from https://smith.langchain.com/settings)
export LANGSMITH_API_KEY=lsv2_pt_your_actual_langsmith_key_here

# Salesforce Credentials (get from your OAuth flow)
export SALESFORCE_INSTANCE_URL=https://your-org.my.salesforce.com
export SALESFORCE_ACCESS_TOKEN=your_actual_salesforce_access_token
export SALESFORCE_TOKEN_TYPE=Bearer
export SALESFORCE_REFRESH_TOKEN=your_actual_refresh_token
export SALESFORCE_AUTH_CODE=your_actual_authorization_code
export SALESFORCE_SCOPE="refresh_token api"

# OpenAI API Key (for LLM operations)
export OPENAI_API_KEY=sk-your_actual_openai_api_key

# Optional: Tavily API Key (for web search)
export TAVILY_API_KEY=tvly-your_actual_tavily_key
```

## 🔗 Alternative: Use .env file

Create a `.env` file in the project root:

```bash
# Create .env file (this file should NOT be committed to git)
cp .env.example .env

# Edit .env with your actual values
nano .env
```

## 🚨 SECURITY NOTES

1. **NEVER commit actual credentials to git**
2. **Add .env to .gitignore** 
3. **Use environment variables in production**
4. **Rotate credentials regularly**
5. **Use minimal required permissions**

## 🧪 Testing

After setting environment variables, run:

```bash
# Test the secured conversation
python test_conversation_with_api.py

# Test working functionality  
python test_working_conversation.py

# Debug lead creation
python debug_lead_creation.py
```

## 🛡️ Files Secured

These files now use environment variables instead of hardcoded credentials:
- ✅ `test_conversation_with_api.py`
- ✅ `test_working_conversation.py` 
- ✅ `debug_lead_creation.py`

## 📋 Credential Sources

Get your Salesforce credentials from:
1. **Instance URL**: Your Salesforce org URL
2. **Access Token**: OAuth 2.0 flow or Connected App
3. **Auth Code**: Salesforce OAuth authorization flow
4. **Refresh Token**: OAuth 2.0 response
