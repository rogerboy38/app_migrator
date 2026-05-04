#!/usr/bin/env python3
"""Quick smoke test for analysis tools"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from analysis_tools import analyze_app_structure, analyze_migration_compatibility
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def quick_test(app_name="frappe"):
    """Quick smoke test"""
    print(f"🚀 Quick test for {app_name}")
    
    try:
        # Test 1: Basic structure analysis
        print("1. Testing structure analysis...")
        structure = analyze_app_structure(app_name)
        if structure.get("error"):
            print(f"   ❌ Failed: {structure['error']}")
            return False
        print(f"   ✅ Success: {structure.get('app_name')} - {len(structure.get('modules', []))} modules")
        
        # Test 2: Migration compatibility
        print("2. Testing migration compatibility...")
        compatibility = analyze_migration_compatibility(app_name)
        if compatibility.get("error"):
            print(f"   ❌ Failed: {compatibility['error']}")
            return False
        print(f"   ✅ Success: Score {compatibility.get('compatibility_score')}/100 - Ready: {compatibility.get('migration_ready')}")
        
        print("🎉 Quick test passed!")
        return True
        
    except Exception as e:
        print(f"💥 Quick test failed: {e}")
        return False

if __name__ == "__main__":
    app_to_test = sys.argv[1] if len(sys.argv) > 1 else "frappe"
    success = quick_test(app_to_test)
    sys.exit(0 if success else 1)
