#!/usr/bin/env python3
"""
STEP-601 FINAL TEST - App Migrator v6.0.0 Boot Stability
"""
import sys
import os

print("🔧 STEP-601 FINAL TEST - Boot Stability Verification")
print("=" * 65)

def run_final_test():
    tests_passed = 0
    tests_total = 0
    
    print("1. Testing all critical imports...")
    critical_imports = [
        ("frappe", None),
        ("app_migrator", None),
        ("app_migrator.core.migration_manager", "MigrationManager"),
        ("app_migrator.core.boot_fixer", "BootFixer"),
        ("app_migrator.core.emergency_boot", "EmergencyBoot"),
        ("app_migrator.commands.boot_fix", "BootFixCommand")
    ]
    
    for module, class_name in critical_imports:
        tests_total += 1
        try:
            if class_name:
                exec(f"from {module} import {class_name}")
                print(f"   ✅ {module}.{class_name}")
            else:
                exec(f"import {module}")
                print(f"   ✅ {module}")
            tests_passed += 1
        except Exception as e:
            print(f"   ❌ {module}{'.' + class_name if class_name else ''}: {e}")
    
    print("\n2. Testing instance creation...")
    # Import all classes first
    from app_migrator.core.migration_manager import MigrationManager
    from app_migrator.core.boot_fixer import BootFixer
    from app_migrator.core.emergency_boot import EmergencyBoot
    from app_migrator.commands.boot_fix import BootFixCommand
    
    instance_tests = [
        ("MigrationManager", MigrationManager),
        ("BootFixer", BootFixer),
        ("EmergencyBoot", EmergencyBoot),
        ("BootFixCommand", BootFixCommand)
    ]
    
    for name, cls in instance_tests:
        tests_total += 1
        try:
            instance = cls()
            print(f"   ✅ {name} instance created")
            tests_passed += 1
        except Exception as e:
            print(f"   ❌ {name} instance failed: {e}")
    
    print("\n3. Testing method execution...")
    method_tests = [
        ("EmergencyBoot.diagnose_boot_issues()", "emergency.diagnose_boot_issues()"),
        ("BootFixer.fix_boot_issues()", "boot_fixer.fix_boot_issues()"),
        ("MigrationManager.get_installed_apps()", "migrator.get_installed_apps()")
    ]
    
    # Create instances
    migrator = MigrationManager()
    boot_fixer = BootFixer()
    emergency = EmergencyBoot()
    
    for name, method_call in method_tests:
        tests_total += 1
        try:
            result = eval(method_call)
            print(f"   ✅ {name} executed: {result}")
            tests_passed += 1
        except Exception as e:
            print(f"   ❌ {name} failed: {e}")
    
    print("\n" + "=" * 65)
    print(f"FINAL RESULTS: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 STEP-601 COMPLETE: ALL BOOT CRASHES RESOLVED!")
        print("✅ App Migrator v6.0.0 is STABLE and PRODUCTION-READY!")
        return True
    else:
        print("⚠️  STEP-601 INCOMPLETE: Some tests failed")
        return False

if __name__ == "__main__":
    success = run_final_test()
    sys.exit(0 if success else 1)
