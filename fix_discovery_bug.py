import re

# Read the current file
with open('app_migrator/commands/__init__.py', 'r') as f:
    content = f.read()

# Find the discover_doctypes_in_module function
old_discovery_function = '''def discover_doctypes_in_module(app_name, module_name):
    """Discover actual doctype names in a module"""
    try:
        base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
        
        if not os.path.exists(base_path):
            return []
            
        doctypes = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            
            # Only include directories that have actual doctype content
            if (os.path.isdir(item_path) and not item.startswith('.') and
                not item == '__pycache__'):
                
                # Check if this looks like a real doctype (has JSON files or other content)
                doctype_files = [f for f in os.listdir(item_path) if not f.startswith('.') and not f == '__pycache__']
                if doctype_files:
                    doctypes.append(item)
                    
        return sorted(doctypes)
        
    except Exception as e:
        return []'''

new_discovery_function = '''def discover_doctypes_in_module(app_name, module_name):
    """Discover actual doctype names in a module - FIXED VERSION"""
    try:
        base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
        
        if not os.path.exists(base_path):
            return []
            
        doctypes = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            
            # Only include directories that have actual doctype content
            if (os.path.isdir(item_path) and not item.startswith('.') and
                not item == '__pycache__'):
                
                # Check if this looks like a real doctype (has JSON files or other content)
                doctype_files = [f for f in os.listdir(item_path) if not f.startswith('.') and not f == '__pycache__']
                if doctype_files:
                    # ✅ FIX: Return the DIRECTORY name, not the JSON name
                    # The migration uses this as the directory name to copy from
                    doctypes.append(item)
                    
        return sorted(doctypes)
        
    except Exception as e:
        return []'''

# Replace the function
content = content.replace(old_discovery_function, new_discovery_function)

# Write back
with open('app_migrator/commands/__init__.py', 'w') as f:
    f.write(content)

print("✅ Fixed discover_doctypes_in_module function")
print("🎯 Now it will return directory names (snake_case) instead of JSON names")
