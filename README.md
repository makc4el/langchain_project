# LangGraph Platform AI Agent

A production-ready conversational AI agent built with LangGraph and OpenAI GPT-4o-mini, designed for seamless deployment on LangGraph Platform.

## 🚀 Features

- **Platform-Ready**: Fully compatible with LangGraph Platform deployment
- **API Integration**: RESTful API interface for prompt/response interactions
- **OpenAI GPT-4o-mini**: Latest efficient OpenAI model for optimal performance
- **Session Management**: Advanced graph with user context and session tracking
- **Production-Grade**: Clean architecture with proper error handling

## 📋 Requirements

- Python 3.11+
- OpenAI API key
- LangGraph Platform account (for cloud deployment)

## 🛠 Project Structure

```
├── main.py                 # Core agent logic and graphs
├── langgraph.json         # Platform deployment configuration
├── pyproject.toml         # Python dependencies
├── .gitignore            # Git ignore rules (includes .env)
└── README.md             # This file
```

## 🔧 Local Development

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 3. Test Locally

```bash
python main.py
```

## 🌐 Platform Deployment

This project is configured for one-click deployment to LangGraph Platform:

### Available Graphs

1. **agent** (`main.py:graph`)
   - Simple conversational AI agent
   - Direct prompt → response API
   - Optimal for basic use cases

2. **advanced_agent** (`main.py:advanced_graph`) 
   - Enhanced with session management
   - User ID and session ID tracking
   - Perfect for multi-user applications

### Deploy to Platform

1. **Upload Project**: Upload the entire project folder to LangGraph Platform
2. **Set Environment**: Configure `OPENAI_API_KEY` in platform environment
3. **Deploy**: Platform will automatically use `langgraph.json` configuration
4. **Access API**: Get your API endpoint for integration

## 📡 API Usage

Once deployed, the agent provides a REST API:

### Basic Request
```bash
curl -X POST "https://your-deployment-url/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [
        {
          "type": "human",
          "content": "Explain quantum computing in simple terms"
        }
      ]
    }
  }'
```

### Response Format
```json
{
  "output": {
    "messages": [
      {
        "type": "human", 
        "content": "Explain quantum computing in simple terms"
      },
      {
        "type": "ai",
        "content": "Quantum computing is a revolutionary technology that..."
      }
    ]
  }
}
```

## 🔐 Security

- ✅ `.env` files are git-ignored
- ✅ No hardcoded API keys
- ✅ Platform-managed environment variables
- ✅ Clean git history (secrets removed)

## 🎯 Platform Compatibility Checklist

- ✅ **No import-time execution**: Code doesn't run when imported
- ✅ **Proper graph exports**: `graph` and `advanced_graph` variables
- ✅ **RunnableConfig support**: Compatible with platform configuration
- ✅ **Environment variables**: Uses platform-provided `OPENAI_API_KEY`
- ✅ **Valid langgraph.json**: Proper platform configuration
- ✅ **Python 3.11**: Platform-supported Python version
- ✅ **API interface**: RESTful prompt/response workflow

## 🚀 Quick Start

1. **Clone & Setup**:
   ```bash
   git clone <your-repo>
   cd langchain_project
   pip install -e .
   ```

2. **Local Test** (optional):
   ```bash
   echo "OPENAI_API_KEY=your_key" > .env
   python main.py
   ```

3. **Deploy to Platform**:
   - Upload project folder
   - Set `OPENAI_API_KEY` environment variable
   - Deploy and get API endpoint

## 🤖 Model Information

- **Model**: OpenAI GPT-4o-mini
- **Temperature**: 0.7 (balanced creativity/consistency)
- **Context**: Conversation history maintained
- **Performance**: Optimized for production use

## 📞 Support

For issues with:
- **LangGraph Platform**: Check platform documentation
- **OpenAI API**: Verify API key and quotas
- **Local Development**: Ensure Python 3.11+ and dependencies installed

---

**Ready for LangGraph Platform deployment! 🚀**
