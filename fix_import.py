import os

file_path = "app_migrator/commands/app_setup.py"

with open(file_path, 'r') as f:
    content = f.read()

# Fix the import - cloud_api should be app_migrator.utils.cloud_api
if "from cloud_api import SiteAPI" in content:
    print("Fixing import...")
    content = content.replace(
        "from cloud_api import SiteAPI",
        "from app_migrator.utils.cloud_api import SiteAPI"
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Import fixed!")
else:
    print("Import already fixed or different format")
    
    # Check for other patterns
    if "import cloud_api" in content:
        print("Found other cloud_api import, checking...")
