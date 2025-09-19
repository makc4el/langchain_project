#!/bin/bash

# Test script for your deployed LangGraph application
# Deployment URL: https://your-deployment-id.us.langgraph.app

DEPLOYMENT_URL="https://your-deployment-id.us.langgraph.app"

# Check if LANGSMITH_API_KEY is set
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo "❌ Error: LANGSMITH_API_KEY environment variable not set!"
    echo "Get your API key from https://smith.langchain.com/settings"
    echo "Then run: export LANGSMITH_API_KEY=your_key_here"
    exit 1
fi

echo "🎯 Testing LangGraph Deployment"
echo "🚀 Deployment URL: $DEPLOYMENT_URL"
echo "🔑 API Key: ${LANGSMITH_API_KEY:0:8}..."
echo ""

# 1. Create a thread
echo "1️⃣ Creating a new thread..."
THREAD_RESPONSE=$(curl -s -X POST "$DEPLOYMENT_URL/threads" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGSMITH_API_KEY" \
  -d '{}')

# Check if thread creation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to create thread. Check your API key and deployment URL."
    exit 1
fi

echo "Thread response: $THREAD_RESPONSE"

# Extract thread ID (requires jq or python)
if command -v jq &> /dev/null; then
    THREAD_ID=$(echo $THREAD_RESPONSE | jq -r '.thread_id')
elif command -v python3 &> /dev/null; then
    THREAD_ID=$(echo $THREAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])" 2>/dev/null)
else
    echo "❌ Need jq or python3 to parse JSON response"
    echo "Install with: brew install jq"
    exit 1
fi

if [ "$THREAD_ID" = "null" ] || [ -z "$THREAD_ID" ]; then
    echo "❌ Failed to extract thread ID from response"
    echo "Response was: $THREAD_RESPONSE"
    exit 1
fi

echo "✅ Created thread: $THREAD_ID"
echo ""

# 2. Test simple agent
echo "2️⃣ Testing simple agent..."
echo "💬 Sending: 'Hello! Can you introduce yourself?'"
echo ""

curl -X POST "$DEPLOYMENT_URL/threads/$THREAD_ID/runs/stream" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGSMITH_API_KEY" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "human",
          "content": "Hello! Can you introduce yourself?"
        }
      ]
    },
    "stream_mode": "values"
  }'

echo ""
echo ""

# 3. Create another thread for advanced agent
echo "3️⃣ Creating thread for advanced agent..."
ADVANCED_THREAD_RESPONSE=$(curl -s -X POST "$DEPLOYMENT_URL/threads" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGSMITH_API_KEY" \
  -d '{}')

if command -v jq &> /dev/null; then
    ADVANCED_THREAD_ID=$(echo $ADVANCED_THREAD_RESPONSE | jq -r '.thread_id')
else
    ADVANCED_THREAD_ID=$(echo $ADVANCED_THREAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])" 2>/dev/null)
fi

echo "✅ Created advanced thread: $ADVANCED_THREAD_ID"
echo ""

# 4. Test advanced agent
echo "4️⃣ Testing advanced agent with session management..."
echo "💬 Sending: 'What makes you special?'"
echo ""

curl -X POST "$DEPLOYMENT_URL/threads/$ADVANCED_THREAD_ID/runs/stream" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGSMITH_API_KEY" \
  -d '{
    "assistant_id": "advanced_agent",
    "input": {
      "messages": [
        {
          "role": "human", 
          "content": "What makes you different from the simple agent?"
        }
      ],
      "user_id": "test_user_123",
      "session_id": "test_session_456", 
      "conversation_count": 0
    },
    "stream_mode": "values"
  }'

echo ""
echo ""

# 5. Test non-streaming run
echo "5️⃣ Testing non-streaming run..."
echo "💬 Sending: 'What is 2+2?'"

RUN_RESPONSE=$(curl -s -X POST "$DEPLOYMENT_URL/threads/$THREAD_ID/runs" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $LANGSMITH_API_KEY" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {
          "role": "human",
          "content": "What is 2+2?"
        }
      ]
    }
  }')

if command -v jq &> /dev/null; then
    RUN_ID=$(echo $RUN_RESPONSE | jq -r '.run_id')
else
    RUN_ID=$(echo $RUN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null)
fi

echo "✅ Started run: $RUN_ID"

# Poll for completion
echo "🔄 Polling for completion..."
while true; do
  STATUS_RESPONSE=$(curl -s "$DEPLOYMENT_URL/threads/$THREAD_ID/runs/$RUN_ID" \
    -H "x-api-key: $LANGSMITH_API_KEY")
    
  if command -v jq &> /dev/null; then
      STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  else
      STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
  fi
  
  echo "📊 Status: $STATUS"
  
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "error" ]; then
    # Get final state
    STATE_RESPONSE=$(curl -s "$DEPLOYMENT_URL/threads/$THREAD_ID/runs/$RUN_ID/state" \
      -H "x-api-key: $LANGSMITH_API_KEY")
    echo "📝 Final response:"
    
    if command -v jq &> /dev/null; then
        echo $STATE_RESPONSE | jq '.values.messages[-1].content' 2>/dev/null || echo $STATE_RESPONSE
    else
        echo $STATE_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'values' in data and 'messages' in data['values']:
        messages = data['values']['messages']
        if messages:
            print('🤖 Agent:', messages[-1]['content'])
    else:
        print(json.dumps(data, indent=2))
except:
    print('Could not parse response')
" 2>/dev/null || echo $STATE_RESPONSE
    fi
    break
  fi
  
  sleep 2
done

echo ""
echo "✅ Testing Complete!"
echo ""
echo "🎉 Your LangGraph deployment is working correctly!"
echo "📚 Available assistants:"
echo "   • agent (simple chat)"
echo "   • advanced_agent (with session management)"

