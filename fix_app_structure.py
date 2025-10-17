#!/usr/bin/env python3
"""
Fix App Migrator Structure
"""
import os
import sys

def create_init_files():
    """Create missing __init__.py files"""
    directories = [
        "app_migrator/core",
        "app_migrator/commands", 
        "app_migrator"
    ]
    
    for directory in directories:
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# Package initialization\n')
            print(f"✓ Created {init_file}")
        else:
            print(f"✓ {init_file} already exists")

def verify_structure():
    """Verify the app structure is correct"""
    required_files = [
        "__init__.py",
        "app_migrator/__init__.py", 
        "app_migrator/core/__init__.py",
        "app_migrator/commands/__init__.py"
    ]
    
    print("\nVerifying app structure...")
    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} MISSING")
            all_good = False
    
    return all_good

def test_imports():
    """Test that imports work after fixes"""
    print("\nTesting imports...")
    try:
        import frappe
        print("✓ Frappe imports")
        
        import app_migrator
        print("✓ App Migrator imports")
        
        from app_migrator.core.migration_manager import MigrationManager
        print("✓ MigrationManager imports")
        
        print("🎉 All imports working!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    print("🔧 Fixing App Migrator Structure")
    print("=" * 40)
    
    create_init_files()
    
    if verify_structure():
        print("\n✅ App structure is now correct!")
    else:
        print("\n⚠ Some structure issues remain")
    
    if test_imports():
        print("\n🎉 SUCCESS: App Migrator is fully functional!")
    else:
        print("\n❌ There are still import issues")

if __name__ == "__main__":
    main()
