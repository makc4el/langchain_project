"""
Salesforce Tools for LangChain Integration

This module provides LangChain tools that interact with Salesforce via the MCP server
"""

import asyncio
from typing import Dict, Any, Optional
from langchain_core.tools import Tool
from mcp_client import mcp_client


def create_salesforce_query_tool() -> Tool:
    """Create a tool for executing SOQL queries"""
    
    async def query_salesforce(query: str) -> str:
        """Execute a SOQL query in Salesforce"""
        try:
            if not mcp_client.credentials:
                return "❌ Salesforce credentials not set. Please provide your instanceUrl and accessToken first."
            
            result = await mcp_client.query_soql(query)
            
            if "error" in result:
                return f"❌ Query failed: {result['error']}"
            
            # Format the results nicely
            records = result.get("result", {}).get("content", [])
            if not records:
                return "✅ Query executed successfully but returned no records."
            
            response = f"✅ Query returned {len(records)} records:\n\n"
            for i, record in enumerate(records[:5]):  # Show first 5 records
                response += f"Record {i+1}:\n"
                for key, value in record.items():
                    if key != "attributes":
                        response += f"  {key}: {value}\n"
                response += "\n"
            
            if len(records) > 5:
                response += f"... and {len(records) - 5} more records"
            
            return response
            
        except Exception as e:
            return f"❌ Error executing query: {str(e)}"
    
    def sync_query_salesforce(query: str) -> str:
        """Synchronous wrapper for the async query function"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(query_salesforce(query))
        except RuntimeError:
            # If no event loop is running, create a new one
            return asyncio.run(query_salesforce(query))
    
    return Tool(
        name="salesforce_query",
        description="Execute SOQL queries in Salesforce. Use this to retrieve data from Salesforce objects like Accounts, Contacts, Opportunities, etc. Example: SELECT Id, Name FROM Account LIMIT 10",
        func=sync_query_salesforce
    )


def create_salesforce_search_tool() -> Tool:
    """Create a tool for searching Salesforce objects"""
    
    async def search_salesforce(search_term: str) -> str:
        """Search across Salesforce objects"""
        try:
            if not mcp_client.credentials:
                return "❌ Salesforce credentials not set. Please provide your instanceUrl and accessToken first."
            
            result = await mcp_client.search_objects(search_term)
            
            if "error" in result:
                return f"❌ Search failed: {result['error']}"
            
            records = result.get("result", {}).get("content", [])
            if not records:
                return f"✅ Search completed but no records found for '{search_term}'."
            
            response = f"✅ Found {len(records)} records matching '{search_term}':\n\n"
            for record in records[:10]:  # Show first 10 results
                obj_type = record.get("attributes", {}).get("type", "Unknown")
                record_id = record.get("Id", "No ID")
                name = record.get("Name") or record.get("Subject") or record.get("Title") or "No Name"
                response += f"• {obj_type}: {name} (ID: {record_id})\n"
            
            if len(records) > 10:
                response += f"... and {len(records) - 10} more results"
            
            return response
            
        except Exception as e:
            return f"❌ Error searching: {str(e)}"
    
    def sync_search_salesforce(search_term: str) -> str:
        """Synchronous wrapper for the async search function"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(search_salesforce(search_term))
        except RuntimeError:
            return asyncio.run(search_salesforce(search_term))
    
    return Tool(
        name="salesforce_search",
        description="Search for records across multiple Salesforce objects. Use this to find records by name, keyword, or text content.",
        func=sync_search_salesforce
    )


def create_salesforce_describe_tool() -> Tool:
    """Create a tool for describing Salesforce objects"""
    
    async def describe_salesforce_object(object_name: str) -> str:
        """Describe a Salesforce object to understand its fields and properties"""
        try:
            if not mcp_client.credentials:
                return "❌ Salesforce credentials not set. Please provide your instanceUrl and accessToken first."
            
            result = await mcp_client.describe_object(object_name)
            
            if "error" in result:
                return f"❌ Describe failed: {result['error']}"
            
            obj_info = result.get("result", {}).get("content", {})
            
            response = f"✅ Object: {obj_info.get('name', object_name)}\n"
            response += f"Label: {obj_info.get('label', 'N/A')}\n"
            response += f"Type: {obj_info.get('keyPrefix', 'N/A')}\n\n"
            
            fields = obj_info.get("fields", [])
            if fields:
                response += "Key Fields:\n"
                # Show important fields first
                important_fields = [f for f in fields if f.get("name", "").lower() in ["id", "name", "subject", "title", "email", "phone"]]
                for field in important_fields[:10]:
                    field_name = field.get("name", "")
                    field_label = field.get("label", "")
                    field_type = field.get("type", "")
                    required = " (Required)" if field.get("nillable") == False else ""
                    response += f"• {field_name} ({field_label}): {field_type}{required}\n"
            
            return response
            
        except Exception as e:
            return f"❌ Error describing object: {str(e)}"
    
    def sync_describe_salesforce_object(object_name: str) -> str:
        """Synchronous wrapper for the async describe function"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(describe_salesforce_object(object_name))
        except RuntimeError:
            return asyncio.run(describe_salesforce_object(object_name))
    
    return Tool(
        name="salesforce_describe",
        description="Get detailed information about a Salesforce object including its fields and properties. Use this to understand the structure of objects like Account, Contact, Opportunity, etc.",
        func=sync_describe_salesforce_object
    )


def create_salesforce_create_tool() -> Tool:
    """Create a tool for creating Salesforce records"""
    
    async def create_salesforce_record(input_data: str) -> str:
        """Create a new record in Salesforce
        
        Input format: objectName|field1:value1|field2:value2|...
        Example: Account|Name:Test Company|Type:Customer
        """
        try:
            if not mcp_client.credentials:
                return "❌ Salesforce credentials not set. Please provide your instanceUrl and accessToken first."
            
            # Parse input
            parts = input_data.split("|")
            if len(parts) < 2:
                return "❌ Invalid input format. Use: objectName|field1:value1|field2:value2"
            
            object_name = parts[0].strip()
            fields = {}
            
            for part in parts[1:]:
                if ":" not in part:
                    continue
                field_name, field_value = part.split(":", 1)
                fields[field_name.strip()] = field_value.strip()
            
            if not fields:
                return "❌ No fields provided for record creation"
            
            result = await mcp_client.create_record(object_name, fields)
            
            if "error" in result:
                return f"❌ Create failed: {result['error']}"
            
            record_id = result.get("result", {}).get("content", [{}])[0].get("id", "Unknown")
            return f"✅ Successfully created {object_name} record with ID: {record_id}"
            
        except Exception as e:
            return f"❌ Error creating record: {str(e)}"
    
    def sync_create_salesforce_record(input_data: str) -> str:
        """Synchronous wrapper for the async create function"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(create_salesforce_record(input_data))
        except RuntimeError:
            return asyncio.run(create_salesforce_record(input_data))
    
    return Tool(
        name="salesforce_create",
        description="Create a new record in Salesforce. Format: objectName|field1:value1|field2:value2. Example: Account|Name:Test Company|Type:Customer",
        func=sync_create_salesforce_record
    )


def create_salesforce_manage_field_tool() -> Tool:
    """Create a tool for managing custom fields in Salesforce objects"""
    
    async def manage_salesforce_field(input_data: str) -> str:
        """Create or update custom fields in Salesforce objects
        
        Input format: operation|objectName|fieldName|type|label|[additional properties]
        Example: create|Lead|testing_string|Text|Testing String|length:255|description:A test field
        """
        try:
            if not mcp_client.credentials:
                return "❌ Salesforce credentials not set. Please provide your instanceUrl and accessToken first."
            
            # Parse input
            parts = input_data.split("|")
            if len(parts) < 4:
                return "❌ Invalid input format. Use: operation|objectName|fieldName|type|label|[additional properties]"
            
            operation = parts[0].strip()
            object_name = parts[1].strip()
            field_name = parts[2].strip()
            field_type = parts[3].strip()
            field_label = parts[4].strip() if len(parts) > 4 else field_name
            
            if operation not in ['create', 'update']:
                return "❌ Operation must be 'create' or 'update'"
            
            # Prepare field properties
            field_props = {
                "type": field_type,
                "label": field_label
            }
            
            # Parse additional properties
            for part in parts[5:] if len(parts) > 5 else []:
                if ":" in part:
                    prop_name, prop_value = part.split(":", 1)
                    prop_name = prop_name.strip()
                    prop_value = prop_value.strip()
                    
                    # Convert boolean values
                    if prop_value.lower() in ['true', 'false']:
                        prop_value = prop_value.lower() == 'true'
                    # Convert numeric values
                    elif prop_value.isdigit():
                        prop_value = int(prop_value)
                    
                    field_props[prop_name] = prop_value
            
            result = await mcp_client.manage_field(
                operation=operation,
                object_name=object_name,
                field_name=field_name,
                **field_props
            )
            
            if "error" in result:
                return f"❌ Field management failed: {result['error']}"
            
            # Extract the response message - handle both dict and list responses
            result_data = result.get("result", {})
            
            # Handle case where result might be a list
            if isinstance(result_data, list):
                content = result_data
            else:
                content = result_data.get("content", [])
            
            if content and len(content) > 0:
                first_item = content[0]
                if isinstance(first_item, dict):
                    message = first_item.get("text", "Unknown response")
                    return f"✅ {message}"
                else:
                    return f"✅ {first_item}"
            else:
                return f"✅ Successfully {operation}d field {field_name}__c on {object_name}"
            
        except Exception as e:
            return f"❌ Error managing field: {str(e)}"
    
    def sync_manage_salesforce_field(input_data: str) -> str:
        """Synchronous wrapper for the async field management function"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(manage_salesforce_field(input_data))
        except RuntimeError:
            return asyncio.run(manage_salesforce_field(input_data))
    
    return Tool(
        name="salesforce_manage_field",
        description="Create or update custom fields on Salesforce objects. Format: operation|objectName|fieldName|type|label|[properties]. Example: create|Lead|testing_string|Text|Testing String|length:255",
        func=sync_manage_salesforce_field
    )


def get_all_salesforce_tools():
    """Get all available Salesforce tools"""
    return [
        create_salesforce_query_tool(),
        create_salesforce_search_tool(),
        create_salesforce_describe_tool(),
        create_salesforce_create_tool(),
        create_salesforce_manage_field_tool()
    ]
