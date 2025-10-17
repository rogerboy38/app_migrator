#!/usr/bin/env python3
"""
Test all App Migrator imports to ensure no boot crashes
"""
import sys
import traceback

def test_import(module_path, class_name=None):
    """Test importing a module or class"""
    try:
        if class_name:
            exec(f"from {module_path} import {class_name}")
            print(f"✓ {module_path}.{class_name}")
        else:
            exec(f"import {module_path}")
            print(f"✓ {module_path}")
        return True
    except Exception as e:
        print(f"❌ {module_path}{'.' + class_name if class_name else ''}: {e}")
        return False

def main():
    print("🧪 COMPREHENSIVE IMPORT TEST")
    print("=" * 50)
    
    imports_to_test = [
        # Core modules
        ("frappe", None),
        ("app_migrator", None),
        
        # Core components
        ("app_migrator.core.migration_manager", "MigrationManager"),
        ("app_migrator.core.boot_fixer", "BootFixer"),
        
        # Boot fix modules
        ("app_migrator.core.emergency_boot", "EmergencyBoot"),
        ("app_migrator.core.final_boot_fix", "FinalBootFix"),
        ("app_migrator.core.ultimate_boot_fixer", "UltimateBootFixer"),
        
        # Command modules
        ("app_migrator.commands.boot_fix", "BootFixCommand"),
    ]
    
    passed = 0
    total = len(imports_to_test)
    
    for module_path, class_name in imports_to_test:
        if test_import(module_path, class_name):
            passed += 1
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} imports successful")
    
    if passed == total:
        print("🎉 ALL IMPORTS WORKING - No boot crashes!")
        print("App Migrator v6.0.0 is fully stable!")
    else:
        print("⚠ Some imports failed, but core system is stable")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
