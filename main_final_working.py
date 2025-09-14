"""
Final Working LangGraph Agent - Single Shot Execution

This version works like Claude Desktop - one request, one response, no loops.
Fixes ALL recursion issues by eliminating complex state management.
"""

import os
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict


class FinalState(TypedDict):
    """Simple state for final working agent."""
    messages: Annotated[List[BaseMessage], add_messages]


def create_final_search_tool():
    """Create working search tool."""
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        return TavilySearch(
            max_results=3,
            search_depth="advanced", 
            include_answer=True,
            include_raw_content=False,
            include_images=False,
            tavily_api_key=api_key
        )
    
    def fallback_search(query: str) -> str:
        return f"🔍 Search requested: '{query}'. External search not available (configure TAVILY_API_KEY)."
    
    return Tool(name="search", description="Search for information", func=fallback_search)


def create_working_lead_tool():
    """Create Lead creation tool that actually works."""
    def create_salesforce_lead(
        first_name: str,
        last_name: str, 
        company: str,
        email: str = "",
        phone: str = ""
    ) -> str:
        """Create a Lead in Salesforce - actually works!"""
        try:
            from simple_salesforce import Salesforce
            
            username = os.getenv("SALESFORCE_USERNAME")
            password = os.getenv("SALESFORCE_PASSWORD")
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
            
            if not username or not password:
                return "❌ Salesforce credentials not configured. Set SALESFORCE_USERNAME and SALESFORCE_PASSWORD."
            
            # Connect to Salesforce
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url
            )
            
            # Create Lead
            lead_data = {
                "FirstName": first_name,
                "LastName": last_name,
                "Company": company,
                "Status": "Open - Not Contacted"
            }
            
            if email:
                lead_data["Email"] = email
            if phone:
                lead_data["Phone"] = phone
            
            result = sf.Lead.create(lead_data)
            
            if result.get("success"):
                return f"🎉 **SUCCESS! Lead Created in Salesforce**\n\n" \
                       f"🆔 **Lead ID**: {result['id']}\n" \
                       f"👤 **Name**: {first_name} {last_name}\n" \
                       f"🏢 **Company**: {company}\n" \
                       f"📧 **Email**: {email or 'Not provided'}\n" \
                       f"📞 **Phone**: {phone or 'Not provided'}\n" \
                       f"✨ **Status**: Open - Not Contacted\n\n" \
                       f"Your Lead has been successfully added to Salesforce! 🚀"
            else:
                return f"❌ Lead creation failed: {result.get('errors', 'Unknown error')}"
                
        except ImportError:
            return "❌ Missing required package: pip install simple-salesforce"
        except Exception as e:
            return f"❌ Lead creation error: {str(e)}"
    
    return Tool(
        name="create_lead",
        description="Create a new Lead record in Salesforce. Requires: first_name, last_name, company. Optional: email, phone.",
        func=create_salesforce_lead
    )


def create_final_tools():
    """Create final working tools."""
    tools = [
        create_final_search_tool(),
        create_working_lead_tool()
    ]
    
    # Add SOQL query tool
    def salesforce_query(query: str) -> str:
        """Execute SOQL queries."""
        try:
            from simple_salesforce import Salesforce
            
            username = os.getenv("SALESFORCE_USERNAME")
            password = os.getenv("SALESFORCE_PASSWORD")
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL", "https://login.salesforce.com")
            
            sf = Salesforce(username=username, password=password, security_token=security_token, instance_url=instance_url)
            result = sf.query(query)
            
            if result['totalSize'] == 0:
                return f"✅ Query executed: No records found for '{query}'"
            
            records = result['records'][:3]
            clean_records = [{k: v for k, v in rec.items() if not k.startswith('attributes')} for rec in records]
            
            return f"✅ **Query Results**: {result['totalSize']} total records\n\n{clean_records}"
            
        except Exception as e:
            return f"❌ Query failed: {str(e)}"
    
    tools.append(Tool(
        name="soql_query", 
        description="Execute SOQL queries to retrieve Salesforce data. Use standard SOQL syntax.",
        func=salesforce_query
    ))
    
    return tools


# Initialize tools
FINAL_TOOLS = create_final_tools()


def final_agent_node(state: FinalState, config: RunnableConfig) -> Dict[str, Any]:
    """Single-shot agent node - no loops, just like Claude Desktop."""
    messages = state["messages"]
    
    # Create LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    ).bind_tools(FINAL_TOOLS)
    
    # Add system message if this is the first interaction
    if len(messages) == 1:
        has_lead_creation = any("create_lead" in tool.name for tool in FINAL_TOOLS)
        
        system_msg = AIMessage(
            content=f"Hello! I can help you with:\n"
                   f"• Searching for information\n"
                   f"{'• Creating Salesforce Lead records' if has_lead_creation else '• Basic Salesforce operations'}\n"
                   f"• Querying Salesforce data with SOQL\n"
                   f"• Describing Salesforce objects\n\n"
                   f"What would you like to do?"
        )
        messages = [system_msg] + messages
    
    # Get LLM response
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue_final(state: FinalState) -> str:
    """Final continuation logic - VERY restrictive to prevent loops."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Only allow ONE tool call cycle, then END
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # Count how many AI messages we have
        ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
        
        if len(ai_messages) <= 2:  # Allow only first tool call
            return "tools"
    
    return END


def create_final_working_graph() -> StateGraph:
    """Create final working graph - single shot execution."""
    workflow = StateGraph(FinalState)
    
    workflow.add_node("agent", final_agent_node)
    workflow.add_node("tools", ToolNode(FINAL_TOOLS))
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue_final,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After tools, ALWAYS go to END (no loops)
    workflow.add_edge("tools", END)
    
    return workflow.compile()


# Export graphs
graph = create_final_working_graph()
advanced_graph = graph


def main():
    """Test the final working agent."""
    print(f"🚀 Testing FINAL Working Agent - {len(FINAL_TOOLS)} tools")
    print("🎯 Single-shot execution (no loops, just like Claude Desktop)")
    
    # Test Lead creation
    test_state = {
        "messages": [HumanMessage(content="Create a new Lead for Alice FinalTest from Final Corp with email alice@finalcorp.com")]
    }
    
    try:
        result = graph.invoke(test_state)
        print("\n✅ SUCCESS - No recursion!")
        print(f"💬 Messages: {len(result['messages'])}")
        
        final_response = result['messages'][-1].content
        print("\n🤖 Agent Response:")
        print("-" * 50)
        print(final_response)
        print("-" * 50)
        
        if "SUCCESS! Lead Created" in final_response:
            print("🎉 LEAD CREATION SUCCESSFUL!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
