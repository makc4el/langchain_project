"""
Working Salesforce LangGraph Agent

This version provides the same Salesforce functionality as Claude Desktop
but using direct API calls that actually work in LangGraph.
"""

import os
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, Tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import Annotated, TypedDict


class WorkingState(TypedDict):
    """State for the working agent."""
    messages: Annotated[List[BaseMessage], add_messages]


def create_search_tool():
    """Create search tool."""
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
        return f"Search for: '{query}' - External search not configured (TAVILY_API_KEY missing)."
    
    return Tool(name="search", description="Search for information", func=fallback_search)


def create_working_salesforce_tools():
    """Create Salesforce tools that actually work with your org."""
    tools = []
    
    # Check if we have credentials
    username = os.getenv("SALESFORCE_USERNAME")
    password = os.getenv("SALESFORCE_PASSWORD")
    
    if not username or not password:
        return []
    
    def create_lead_record(
        first_name: str,
        last_name: str, 
        company: str,
        email: str = "",
        phone: str = "",
        status: str = "Open - Not Contacted"
    ) -> str:
        """Create a new Lead record in Salesforce."""
        try:
            from simple_salesforce import Salesforce
            
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
            
            # Try authentication with your org
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url
            )
            
            # Create the Lead record
            lead_data = {
                "FirstName": first_name,
                "LastName": last_name,
                "Company": company,
                "Status": status
            }
            
            if email:
                lead_data["Email"] = email
            if phone:
                lead_data["Phone"] = phone
            
            result = sf.Lead.create(lead_data)
            
            if result.get("success"):
                return f"✅ **Lead Created Successfully!**\n\n" \
                       f"🆔 **Lead ID**: {result['id']}\n" \
                       f"👤 **Name**: {first_name} {last_name}\n" \
                       f"🏢 **Company**: {company}\n" \
                       f"📧 **Email**: {email or 'Not provided'}\n" \
                       f"📞 **Phone**: {phone or 'Not provided'}\n" \
                       f"📊 **Status**: {status}\n\n" \
                       f"The Lead has been successfully added to your Salesforce org!"
            else:
                errors = result.get("errors", ["Unknown error"])
                return f"❌ **Lead Creation Failed**\n\nErrors: {', '.join([str(e) for e in errors])}"
                
        except ImportError:
            return "❌ Salesforce integration requires 'simple-salesforce' package."
        except Exception as e:
            return f"❌ **Lead Creation Failed**\n\nError: {str(e)}\n\n" \
                   f"💡 **Troubleshooting**:\n" \
                   f"• Check your Salesforce credentials\n" \
                   f"• Verify your org is accessible\n" \
                   f"• Ensure you have Lead creation permissions"
    
    tools.append(Tool(
        name="create_lead",
        description="Create a new Lead record in Salesforce. Requires first_name, last_name, and company. Optional: email, phone, status.",
        func=create_lead_record
    ))
    
    def query_salesforce(query: str) -> str:
        """Execute SOQL queries against Salesforce."""
        try:
            from simple_salesforce import Salesforce
            
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
            
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url
            )
            
            result = sf.query(query)
            
            if result['totalSize'] == 0:
                return f"✅ **Query Executed Successfully**\n\n" \
                       f"📝 **Query**: {query}\n" \
                       f"📊 **Result**: No records found"
            
            records = result['records'][:5]  # First 5 records
            formatted_records = []
            
            for record in records:
                clean_record = {k: v for k, v in record.items() if not k.startswith('attributes')}
                formatted_records.append(clean_record)
            
            return f"✅ **Query Results**\n\n" \
                   f"📝 **Query**: {query}\n" \
                   f"📊 **Total Records**: {result['totalSize']}\n" \
                   f"📋 **Sample Records** (first 5):\n\n" \
                   f"{formatted_records}"
                   
        except ImportError:
            return "❌ Salesforce integration requires 'simple-salesforce' package."
        except Exception as e:
            return f"❌ **Query Failed**\n\nError: {str(e)}\n\n" \
                   f"💡 **Tip**: Use SOQL syntax like 'SELECT Id, Name FROM Account LIMIT 5'"
    
    tools.append(Tool(
        name="salesforce_query",
        description="Execute SOQL queries against Salesforce. Use standard SOQL syntax.",
        func=query_salesforce
    ))
    
    def describe_salesforce_object(object_name: str) -> str:
        """Describe Salesforce objects."""
        try:
            from simple_salesforce import Salesforce
            
            security_token = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
            instance_url = os.getenv("SALESFORCE_LOGIN_URL") or os.getenv("SALESFORCE_INSTANCE_URL")
            
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url
            )
            
            obj = getattr(sf, object_name)
            desc = obj.describe()
            
            fields = []
            for field in desc['fields'][:10]:
                field_info = f"• {field['name']} ({field['type']})"
                if field.get('required'):
                    field_info += " [Required]"
                fields.append(field_info)
            
            return f"✅ **{object_name} Object Description**\n\n" \
                   f"📋 **Label**: {desc.get('label', 'N/A')}\n" \
                   f"🏷️ **API Name**: {desc.get('name', 'N/A')}\n" \
                   f"🔧 **Type**: {desc.get('custom', False) and 'Custom' or 'Standard'} Object\n\n" \
                   f"**Key Fields** (first 10):\n" + "\n".join(fields)
                   
        except ImportError:
            return "❌ Salesforce integration requires 'simple-salesforce' package."
        except Exception as e:
            return f"❌ **Object Description Failed**\n\nError: {str(e)}"
    
    tools.append(Tool(
        name="describe_object",
        description="Get detailed information about Salesforce objects. Use standard object names like 'Account', 'Contact', 'Lead', 'Opportunity'.",
        func=describe_salesforce_object
    ))
    
    print(f"✅ Created {len(tools)} working Salesforce tools")
    return tools


def create_all_working_tools():
    """Create all working tools."""
    tools = []
    
    # Add search
    search_tool = create_search_tool()
    tools.append(search_tool)
    
    # Add working Salesforce tools
    salesforce_tools = create_working_salesforce_tools()
    tools.extend(salesforce_tools)
    
    return tools


# Initialize working tools
WORKING_TOOLS = create_all_working_tools()


def working_agent_node(state: WorkingState, config: RunnableConfig) -> Dict[str, Any]:
    """Working agent node."""
    messages = state["messages"]
    
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    ).bind_tools(WORKING_TOOLS)
    
    # Add system message if needed
    if len(messages) <= 1:
        lead_creation = any("create_lead" in tool.name for tool in WORKING_TOOLS)
        query_available = any("salesforce_query" in tool.name for tool in WORKING_TOOLS)
        
        capabilities = ["search for information"]
        if lead_creation and query_available:
            capabilities.append("create Salesforce Lead records")
            capabilities.append("query Salesforce data")
            capabilities.append("describe Salesforce objects")
        
        system_msg = AIMessage(
            content=f"Hello! I have {len(WORKING_TOOLS)} working tools. "
                   f"I can {', '.join(capabilities)}. How can I help?"
        )
        messages = [system_msg] + messages
    
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue_working(state: WorkingState) -> str:
    """Working continuation logic."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return END


def create_working_graph() -> StateGraph:
    """Create working graph."""
    workflow = StateGraph(WorkingState)
    
    workflow.add_node("agent", working_agent_node)
    workflow.add_node("tools", ToolNode(WORKING_TOOLS))
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue_working,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Export for platform
graph = create_working_graph()
advanced_graph = graph  # Same graph


def main():
    """Test the working agent."""
    print(f"🚀 Testing Working Salesforce Agent - {len(WORKING_TOOLS)} tools")
    
    for tool in WORKING_TOOLS:
        print(f"  • {tool.name}: {tool.description[:50]}...")
    
    # Test Lead creation
    test_state = {
        "messages": [HumanMessage(content="Create a new Lead for John WorkingTest from Working Corp with email john@workingcorp.com")]
    }
    
    try:
        print("\n🧪 Testing Lead creation (should actually work)...")
        result = graph.invoke(test_state)
        
        print("✅ SUCCESS - No recursion error!")
        print(f"💬 Total messages: {len(result['messages'])}")
        
        final_response = result['messages'][-1].content
        print("\n🤖 Final Response:")
        print("-" * 50)
        print(final_response)
        print("-" * 50)
        
        # Check if Lead was created
        if "Lead Created Successfully" in final_response or "Lead ID" in final_response:
            print("🎉 LEAD CREATION WORKED!")
        elif "Lead Creation Failed" in final_response:
            print("⚠️ Lead creation failed but agent handled it properly")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
