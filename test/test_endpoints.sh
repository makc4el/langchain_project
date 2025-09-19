#!/bin/bash

# Test script for LangGraph chat endpoints
# Make sure your langgraph dev server is running on localhost:2024

BASE_URL="http://localhost:2024"

echo "=== Testing LangGraph Chat Endpoints ==="
echo ""

# 1. Create a thread
echo "1. Creating a new thread..."
THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/threads" \
  -H "Content-Type: application/json" \
  -d '{}')

THREAD_ID=$(echo $THREAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])")
echo "Created thread: $THREAD_ID"
echo ""

# 2. Test simple agent
echo "2. Testing simple agent..."
curl -X POST "$BASE_URL/threads/$THREAD_ID/runs/stream" \
  -H "Content-Type: application/json" \
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
echo "3. Creating thread for advanced agent..."
ADVANCED_THREAD_RESPONSE=$(curl -s -X POST "$BASE_URL/threads" \
  -H "Content-Type: application/json" \
  -d '{}')

ADVANCED_THREAD_ID=$(echo $ADVANCED_THREAD_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['thread_id'])")
echo "Created advanced thread: $ADVANCED_THREAD_ID"
echo ""

# 4. Test advanced agent
echo "4. Testing advanced agent with session management..."
curl -X POST "$BASE_URL/threads/$ADVANCED_THREAD_ID/runs/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "advanced_agent",
    "input": {
      "messages": [
        {
          "role": "human", 
          "content": "Hello! What makes you special?"
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
echo "5. Testing non-streaming run..."
RUN_RESPONSE=$(curl -s -X POST "$BASE_URL/threads/$THREAD_ID/runs" \
  -H "Content-Type: application/json" \
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

RUN_ID=$(echo $RUN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])")
echo "Started run: $RUN_ID"

# Poll for completion
echo "Polling for completion..."
while true; do
  STATUS_RESPONSE=$(curl -s "$BASE_URL/threads/$THREAD_ID/runs/$RUN_ID")
  STATUS=$(echo $STATUS_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "error" ]; then
    # Get final state
    STATE_RESPONSE=$(curl -s "$BASE_URL/threads/$THREAD_ID/runs/$RUN_ID/state")
    echo "Final response:"
    echo $STATE_RESPONSE | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'values' in data and 'messages' in data['values']:
    messages = data['values']['messages']
    if messages:
        print('Agent:', messages[-1]['content'])
"
    break
  fi
  
  sleep 1
done

echo ""
echo "=== Testing Complete ==="

