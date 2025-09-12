"""
Demo script showing how to use the LangChain agent with Salesforce capabilities.

This script demonstrates real conversations with the Salesforce-enabled agent.
"""

import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# Import our main agent
from main import advanced_graph


async def demo_salesforce_agent():
    """Demonstrate the Salesforce-enabled agent with real queries."""
    
    print("🚀 Starting Salesforce-Enabled Agent Demo")
    print("=" * 60)
    
    # Initialize advanced graph with Salesforce tools
    print("✨ Initializing agent with Salesforce capabilities...")
    
    # Demo conversations
    demo_queries = [
        "What Salesforce tools and capabilities do you have available?",
        "Can you search for any Account objects in Salesforce?", 
        "Show me the structure of the Account object in Salesforce",
        "Query some Account records from Salesforce - just show me the first few",
        "Can you tell me what custom objects exist in this Salesforce org?",
    ]
    
    conversation_state = {
        "messages": [],
        "user_id": "demo_user",
        "session_id": "demo_session",
        "conversation_count": 0
    }
    
    print("🤖 Agent is ready! Starting demo conversation...\n")
    
    for i, query in enumerate(demo_queries, 1):
        print(f"👤 **Query {i}:** {query}")
        print("-" * 50)
        
        # Add user message to conversation
        conversation_state["messages"].append(HumanMessage(content=query))
        
        try:
            # Get agent response
            result = advanced_graph.invoke(conversation_state)
            
            # Update conversation state
            conversation_state = result
            
            # Display agent response
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                print(f"🤖 **Agent Response:**")
                print(last_message.content)
            else:
                print("🤖 Agent processed the request")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            
        print("\n" + "="*60 + "\n")
        
        # Small delay between queries
        await asyncio.sleep(1)
    
    print("✅ Demo completed! Your agent is ready to use.")
    print("\n💡 **Usage Tips:**")
    print("- Ask about Salesforce objects, fields, and data")
    print("- Request SOQL queries to retrieve data")  
    print("- Ask to create or modify custom objects/fields")
    print("- Request searches across multiple objects")
    print("- Ask for help with Apex code")
    print("- Combine Salesforce operations with web search")


def main():
    """Run the demo."""
    try:
        asyncio.run(demo_salesforce_agent())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user.")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
