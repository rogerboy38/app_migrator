import os
import re

file_path = "app_migrator/commands/app_setup.py"

with open(file_path, 'r') as f:
    content = f.read()

# Check what imports are needed
print("Current imports in app_setup.py:")
imports = re.findall(r'^(from .* import .*|import .*)', content, re.MULTILINE)
for imp in imports:
    print(f"  {imp}")

# Fix the cloud_api import
if "from cloud_api import SiteAPI" in content:
    # Try relative import
    new_content = content.replace(
        "from cloud_api import SiteAPI",
        "from ..utils.cloud_api import SiteAPI"
    )
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("\n✅ Changed to relative import: from ..utils.cloud_api import SiteAPI")
elif "from app_migrator.utils.cloud_api import SiteAPI" in content:
    print("\n✅ Import already correct")
else:
    print("\n⚠️  Could not find the expected import pattern")
