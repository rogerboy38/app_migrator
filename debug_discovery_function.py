import os
import json

def test_discovery_function():
    """Test what discover_doctypes_in_module actually returns"""
    
    app_name = "amb_w_spc"
    module_name = "sfc_manufacturing"
    
    print("🔍 TESTING discover_doctypes_in_module FUNCTION")
    print("=" * 50)
    
    # This is the exact code from our function
    base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
    
    if not os.path.exists(base_path):
        print(f"❌ Path not found: {base_path}")
        return []
        
    doctypes = []
    print(f"Scanning: {base_path}")
    print()
    
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        
        # Only include directories that have actual doctype content
        if (os.path.isdir(item_path) and not item.startswith('.') and
            not item == '__pycache__'):
            
            # Check if this looks like a real doctype (has JSON files or other content)
            doctype_files = [f for f in os.listdir(item_path) if not f.startswith('.') and not f == '__pycache__']
            if doctype_files:
                doctypes.append(item)
                print(f"✅ Found directory: {item}")
                
                # Check what's in the JSON file
                json_file = os.path.join(item_path, f"{item}.json")
                if os.path.exists(json_file):
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    json_name = data.get('name', 'NOT FOUND')
                    print(f"   JSON 'name' field: '{json_name}'")
                else:
                    print(f"   ❌ JSON file missing: {json_file}")
    
    print()
    print(f"📋 discover_doctypes_in_module RETURNS: {doctypes}")
    return doctypes

# Test it
result = test_discovery_function()
print()
print("🎯 This is what gets passed to interactive selection")
