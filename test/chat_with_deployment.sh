#!/bin/bash

# Simple chat script for your LangGraph deployment
# This script creates a thread automatically and then lets you chat

DEPLOYMENT_URL="https://ht-this-community-12-7ec68f9c68e552e092e656eee5e954ed.us.langgraph.app"

# Check if API key is set
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo "❌ Error: LANGSMITH_API_KEY environment variable not set!"
    echo "Get your API key from https://smith.langchain.com/settings"
    echo "Then run: export LANGSMITH_API_KEY=your_key_here"
    exit 1
fi

# Function to create a new thread
create_thread() {
    echo "📝 Creating new thread..."
    THREAD_RESPONSE=$(curl -s -X POST "$DEPLOYMENT_URL/threads" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $LANGSMITH_API_KEY" \
        -d '{}')
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create thread"
        exit 1
    fi
    
    # Extract thread ID
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
        echo "❌ Failed to extract thread ID"
        echo "Response: $THREAD_RESPONSE"
        exit 1
    fi
    
    echo "✅ Created thread: $THREAD_ID"
}

# Function to send a message
send_message() {
    local message="$1"
    local assistant="$2"
    
    echo "💬 You: $message"
    echo "🤖 $assistant is typing..."
    echo ""
    
    curl -X POST "$DEPLOYMENT_URL/threads/$THREAD_ID/runs/stream" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $LANGSMITH_API_KEY" \
        -d "{
            \"assistant_id\": \"$assistant\",
            \"input\": {
                \"messages\": [
                    {
                        \"role\": \"human\",
                        \"content\": \"$message\"
                    }
                ]
            },
            \"stream_mode\": \"values\"
        }"
    
    echo ""
    echo ""
}

# Function for advanced agent with session info
send_message_advanced() {
    local message="$1"
    local user_id="${3:-user123}"
    local session_id="${4:-session456}"
    
    echo "💬 You: $message"
    echo "🧠 Advanced agent is typing..."
    echo ""
    
    curl -X POST "$DEPLOYMENT_URL/threads/$THREAD_ID/runs/stream" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $LANGSMITH_API_KEY" \
        -d "{
            \"assistant_id\": \"advanced_agent\",
            \"input\": {
                \"messages\": [
                    {
                        \"role\": \"human\",
                        \"content\": \"$message\"
                    }
                ],
                \"user_id\": \"$user_id\",
                \"session_id\": \"$session_id\",
                \"conversation_count\": 0
            },
            \"stream_mode\": \"values\"
        }"
    
    echo ""
    echo ""
}

# Main script
echo "🚀 LangGraph Chat Interface"
echo "Deployment: $DEPLOYMENT_URL"
echo "API Key: ${LANGSMITH_API_KEY:0:8}..."
echo ""

# Create thread first
create_thread

echo ""
echo "🎯 Choose your assistant:"
echo "1) agent - Simple chat agent"
echo "2) advanced_agent - Advanced chat with session management"
echo "3) Demo both agents"
echo ""

read -p "Enter choice (1/2/3): " choice

case $choice in
    1)
        echo "🤖 Starting chat with simple agent..."
        echo "Thread ID: $THREAD_ID"
        echo ""
        
        while true; do
            read -p "💬 Your message (or 'quit' to exit): " user_message
            if [ "$user_message" = "quit" ]; then
                echo "👋 Goodbye!"
                break
            fi
            send_message "$user_message" "agent"
        done
        ;;
    2)
        echo "🧠 Starting chat with advanced agent..."
        echo "Thread ID: $THREAD_ID"
        echo ""
        
        read -p "Enter user ID (default: user123): " user_id
        user_id=${user_id:-user123}
        
        read -p "Enter session ID (default: session456): " session_id
        session_id=${session_id:-session456}
        
        while true; do
            read -p "💬 Your message (or 'quit' to exit): " user_message
            if [ "$user_message" = "quit" ]; then
                echo "👋 Goodbye!"
                break
            fi
            send_message_advanced "$user_message" "$user_id" "$session_id"
        done
        ;;
    3)
        echo "🎬 Demo Mode: Testing both agents"
        echo ""
        
        # Demo simple agent
        echo "=== Simple Agent Demo ==="
        send_message "Hello! Can you introduce yourself?" "agent"
        
        # Create new thread for advanced agent
        create_thread
        echo ""
        
        # Demo advanced agent
        echo "=== Advanced Agent Demo ==="
        send_message_advanced "Hello! What makes you different from the simple agent?"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Session complete!"
echo "📋 Your thread ID was: $THREAD_ID"
echo "💡 You can continue this conversation later using this thread ID"

