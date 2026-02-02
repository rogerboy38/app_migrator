#!/usr/bin/env python3
"""
Fix for analysis tools error handling consistency
"""

import re

def fix_error_handling():
    """Fix the error handling in analysis_tools.py"""
    
    # Read the current file
    with open('analysis_tools.py', 'r') as f:
        content = f.read()
    
    # Fix 1: Ensure analyze_migration_compatibility returns proper error for non-existent apps
    old_compatibility_start = "def analyze_migration_compatibility(self, app_name: str, detailed: bool = False) -> Dict[str, Any]:\n    \"\"\"\n    Analyze migration compatibility with enhanced error handling\n    \"\"\"\n    try:\n        print(f\"🔍 Analyzing migration compatibility: {app_name}\")\n        \n        # Get structure analysis first\n        structure_analysis = self.analyze_app_structure(app_name)"
    
    new_compatibility_start = "def analyze_migration_compatibility(self, app_name: str, detailed: bool = False) -> Dict[str, Any]:\n    \"\"\"\n    Analyze migration compatibility with enhanced error handling\n    \"\"\"\n    try:\n        print(f\"🔍 Analyzing migration compatibility: {app_name}\")\n        \n        # Check if app exists first\n        app_path = self._get_app_path_safe(app_name)\n        if not app_path or not app_path.exists():\n            return self._create_compatibility_error_result(app_name, f\"App {app_name} not found or inaccessible\")\n        \n        # Get structure analysis first\n        structure_analysis = self.analyze_app_structure(app_name)"
    
    if old_compatibility_start in content:
        content = content.replace(old_compatibility_start, new_compatibility_start)
        print("✅ Fixed migration compatibility error handling")
    else:
        print("⚠️  Could not find exact match for migration compatibility method")
    
    # Fix 2: Ensure analyze_dependencies returns proper error for non-existent apps
    old_dependencies_start = "def analyze_dependencies(self, app_name: str) -> Dict[str, Any]:\n    \"\"\"Analyze dependencies with enhanced error handling\"\"\"\n    try:\n        print(f\"🔍 Analyzing dependencies: {app_name}\")\n        \n        app_path = self._get_app_path_safe(app_name)\n        if not app_path or not app_path.exists():\n            return {\"error\": \"App not found\", \"dependencies\": [], \"count\": 0}"
    
    new_dependencies_start = "def analyze_dependencies(self, app_name: str) -> Dict[str, Any]:\n    \"\"\"Analyze dependencies with enhanced error handling\"\"\"\n    try:\n        print(f\"🔍 Analyzing dependencies: {app_name}\")\n        \n        app_path = self._get_app_path_safe(app_name)\n        if not app_path or not app_path.exists():\n            return {\"error\": \"App not found\", \"dependencies\": [], \"count\": 0, \"exists\": False}"
    
    if old_dependencies_start in content:
        content = content.replace(old_dependencies_start, new_dependencies_start)
        print("✅ Fixed dependencies error handling")
    else:
        print("⚠️  Could not find exact match for dependencies method")
    
    # Fix 3: Ensure analyze_code_complexity returns proper error for non-existent apps
    old_complexity_start = "def analyze_code_complexity(self, app_name: str) -> Dict[str, Any]:\n    \"\"\"Analyze code complexity with enhanced error handling\"\"\"\n    try:\n        print(f\"🔍 Analyzing code complexity: {app_name}\")\n        \n        app_path = self._get_app_path_safe(app_name)\n        if not app_path or not app_path.exists():\n            return {\"error\": \"App not found\", \"complexity_score\": 0, \"analysis\": \"failed\"}"
    
    new_complexity_start = "def analyze_code_complexity(self, app_name: str) -> Dict[str, Any]:\n    \"\"\"Analyze code complexity with enhanced error handling\"\"\"\n    try:\n        print(f\"🔍 Analyzing code complexity: {app_name}\")\n        \n        app_path = self._get_app_path_safe(app_name)\n        if not app_path or not app_path.exists():\n            return {\"error\": \"App not found\", \"complexity_score\": 0, \"analysis\": \"failed\", \"exists\": False}"
    
    if old_complexity_start in content:
        content = content.replace(old_complexity_start, new_complexity_start)
        print("✅ Fixed code complexity error handling")
    else:
        print("⚠️  Could not find exact match for code complexity method")
    
    # Write the fixed content back
    with open('analysis_tools.py', 'w') as f:
        f.write(content)
    
    print("🎉 Error handling fixes applied!")

if __name__ == "__main__":
    fix_error_handling()
