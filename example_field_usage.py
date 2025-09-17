#!/usr/bin/env python3
"""
Example of how to use the new Salesforce field management functionality
"""

from salesforce_tools import get_all_salesforce_tools
from mcp_client import mcp_client

def example_usage():
    """Example showing how to create custom fields and use them"""
    
    # Get all Salesforce tools including the new field management tool
    tools = get_all_salesforce_tools()
    field_tool = None
    create_tool = None
    
    for tool in tools:
        if tool.name == "salesforce_manage_field":
            field_tool = tool
        elif tool.name == "salesforce_create":
            create_tool = tool
    
    if not field_tool:
        print("❌ Field management tool not found")
        return
    
    print("🚀 Salesforce Field Management Example")
    print("=" * 40)
    
    # STEP 1: Set your Salesforce credentials
    print("\n1. First, set your Salesforce credentials:")
    print("   mcp_client.set_credentials('https://your-instance.salesforce.com', 'your_access_token')")
    print("   # Or use OAuth code: mcp_client.set_credentials('https://your-instance.salesforce.com', auth_code='your_code')")
    
    # STEP 2: Create custom fields
    print("\n2. Create custom fields:")
    
    examples = [
        {
            "description": "Create a simple text field",
            "input": "create|Lead|testing_string|Text|Testing String|length:255|description:A custom field for testing"
        },
        {
            "description": "Create a required number field",
            "input": "create|Account|priority_score|Number|Priority Score|precision:5|scale:2|required:true|description:Priority score for the account"
        },
        {
            "description": "Create a picklist field",
            "input": "create|Contact|department|Picklist|Department|description:Employee department"
            # Note: Picklist values would need to be added through the Salesforce UI or additional API calls
        },
        {
            "description": "Create a date field",
            "input": "create|Opportunity|target_close_date|Date|Target Close Date|description:Expected close date"
        }
    ]
    
    for example in examples:
        print(f"\n   {example['description']}:")
        print(f"   result = field_tool.func('{example['input']}')")
        
        # Uncomment to actually run (requires credentials):
        # if mcp_client.credentials:
        #     result = field_tool.func(example['input'])
        #     print(f"   Result: {result}")
    
    # STEP 3: Create records with custom fields
    print("\n3. Create records using the new custom fields:")
    
    print("   # After creating the testing_string field, you can create leads with it:")
    print("   lead_input = 'Lead|FirstName:Jane|LastName:Doe|Company:Test Corp|testing_string__c:My Value'")
    print("   result = create_tool.func(lead_input)")
    
    # STEP 4: Update existing fields
    print("\n4. Update existing custom fields:")
    print("   # Change field label or properties:")
    print("   update_input = 'update|Lead|testing_string|label:Updated Testing String|description:Updated description'")
    print("   result = field_tool.func(update_input)")
    
    print("\n" + "=" * 40)
    print("📋 Field Creation Format:")
    print("   create|ObjectName|fieldName|Type|Label|[property:value|property:value...]")
    print("\n📋 Common Field Types:")
    print("   - Text, LongTextArea, Email, Phone, Url")
    print("   - Number, Currency, Percent")
    print("   - Date, DateTime")
    print("   - Checkbox (boolean)")
    print("   - Picklist, MultiselectPicklist")
    print("   - Lookup, MasterDetail (for relationships)")
    print("\n📋 Common Properties:")
    print("   - length:N (for text fields)")
    print("   - precision:N, scale:N (for number fields)")
    print("   - required:true/false")
    print("   - unique:true/false")
    print("   - description:Your description")
    print("   - grantAccessTo:['System Administrator','Standard User']")

if __name__ == "__main__":
    example_usage()
