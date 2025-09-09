import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define the state structure
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize the GPT model (using GPT-4 Turbo as the latest available)
def create_llm():
    return ChatOpenAI(
        model="gpt-4-turbo-preview",  # Use the latest GPT model available
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

# Define the agent node
def agent_node(state: State):
    llm = create_llm()
    
    # Get the last message from the state
    messages = state["messages"]
    
    # Generate response using the LLM
    response = llm.invoke(messages)
    
    # Return the updated state with the new message
    return {"messages": [response]}

# Create the graph
def create_agent_graph():
    # Initialize the state graph
    workflow = StateGraph(State)
    
    # Add the agent node
    workflow.add_node("agent", agent_node)
    
    # Define the flow
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    
    # Compile the graph
    return workflow.compile()

# Main function to run the agent
def run_agent(prompt: str):
    # Create the agent graph
    agent = create_agent_graph()
    
    # Create initial state with the user prompt
    initial_state = {
        "messages": [HumanMessage(content=prompt)]
    }
    
    # Run the agent
    result = agent.invoke(initial_state)
    
    # Extract and return the response
    last_message = result["messages"][-1]
    return last_message.content

# Example usage
if __name__ == "__main__":
    # Set your OpenAI API key
    # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    # Test the agent
    user_prompt = "Explain quantum computing in simple terms"
    response = run_agent(user_prompt)
    print(f"User: {user_prompt}")
    print(f"Agent: {response}")

# For LangGraph Platform deployment, you'll need this configuration
def create_deployable_agent():
    """
    This function returns the compiled graph for deployment on LangGraph Platform
    """
    return create_agent_graph()

# Optional: Add more sophisticated features
class AdvancedState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str

def advanced_agent_node(state: AdvancedState):
    llm = create_llm()
    
    # You can add custom logic here based on user_id, session_id, etc.
    messages = state["messages"]
    
    # Add system message for context if needed
    system_context = "You are a helpful AI assistant. Provide clear and concise responses."
    
    # Prepare messages with system context
    full_messages = [
        {"role": "system", "content": system_context}
    ] + [msg.dict() if hasattr(msg, 'dict') else msg for msg in messages]
    
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def create_advanced_agent_graph():
    workflow = StateGraph(AdvancedState)
    workflow.add_node("agent", advanced_agent_node)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    return workflow.compile()


# Simple usage
response = run_agent("What is Salesforce?")
print(response)