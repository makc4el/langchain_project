import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

# Define the state structure
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize the GPT model for LangGraph Platform
def create_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",  # Use GPT-4o-mini for better platform compatibility
        temperature=0.7,
        # OpenAI API key will be provided by platform environment
    )

# Define the agent node for platform deployment
def agent_node(state: State, config: RunnableConfig):
    """Main agent node that processes messages using OpenAI GPT-4o-mini"""
    llm = create_llm()
    
    # Get messages from state
    messages = state["messages"]
    
    # Generate response using the LLM
    response = llm.invoke(messages, config)
    
    # Return the updated state with the new message
    return {"messages": [response]}

# Create the main graph for platform deployment
def create_graph():
    """Create and return the compiled graph for LangGraph Platform"""
    # Initialize the state graph
    workflow = StateGraph(State)
    
    # Add the agent node
    workflow.add_node("agent", agent_node)
    
    # Define the flow
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    
    # Compile the graph with checkpointer for platform
    return workflow.compile()

# Platform-compatible graph creation (main export)
graph = create_graph()

# Alternative export name for compatibility
def create_deployable_agent():
    """
    This function returns the compiled graph for deployment on LangGraph Platform
    """
    return create_graph()

# Main function for local testing only
def run_agent(prompt: str):
    """Local testing function - not used in platform deployment"""
    agent = create_graph()
    
    initial_state = {
        "messages": [HumanMessage(content=prompt)]
    }
    
    result = agent.invoke(initial_state)
    last_message = result["messages"][-1]
    return last_message.content

# Optional: Advanced graph with session management
class AdvancedState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str

def advanced_agent_node(state: AdvancedState, config: RunnableConfig):
    """Advanced agent node with session management"""
    llm = create_llm()
    
    # You can add custom logic here based on user_id, session_id, etc.
    messages = state["messages"]
    
    # Add system message for context if needed
    system_message = HumanMessage(content="You are a helpful AI assistant. Provide clear and concise responses.")
    enhanced_messages = [system_message] + messages
    
    response = llm.invoke(enhanced_messages, config)
    
    return {"messages": [response]}

def create_advanced_graph():
    """Create advanced graph with session management for platform deployment"""
    workflow = StateGraph(AdvancedState)
    workflow.add_node("agent", advanced_agent_node)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    return workflow.compile()

# Export advanced graph
advanced_graph = create_advanced_graph()

# Local testing (only runs when script is executed directly)
if __name__ == "__main__":
    # Test the agent locally
    test_prompt = "What is LangGraph?"
    print(f"Testing locally with: {test_prompt}")
    try:
        result = run_agent(test_prompt)
        print(f"Response: {result}")
    except Exception as e:
        print(f"Local test failed (this is normal without API key): {e}")