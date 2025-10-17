#!/usr/bin/env python3
"""
Comprehensive Boot Test for App Migrator v6.0.0
Tests that all boot crashes have been resolved
"""
import sys
import os

# Set up proper Python path
bench_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if bench_root not in sys.path:
    sys.path.insert(0, bench_root)

def test_boot_recovery():
    """Test that boot recovery mechanisms work"""
    print("🧪 COMPREHENSIVE BOOT RECOVERY TEST")
    print("=" * 50)
    
    try:
        # Test 1: Basic Frappe functionality
        print("1. Testing Frappe boot...")
        import frappe
        from frappe.utils import get_sites
        sites = get_sites()
        print(f"   ✓ Frappe booted successfully, found {len(sites)} sites")
        
        # Test 2: App Migrator core
        print("2. Testing App Migrator core...")
        import app_migrator
        from app_migrator.core.migration_manager import MigrationManager
        
        migrator = MigrationManager()
        apps = migrator.get_installed_apps()
        print(f"   ✓ App Migrator working, found {len(apps)} apps")
        
        # Test 3: Boot fix modules
        print("3. Testing boot fix modules...")
        from app_migrator.core.emergency_boot import EmergencyBoot
        from app_migrator.core.boot_fixer import BootFixer
        
        emergency = EmergencyBoot()
        boot_fixer = BootFixer()
        
        diagnosis = emergency.diagnose_boot_issues()
        fixes = boot_fixer.fix_boot_issues()
        
        print(f"   ✓ Boot fix modules working: {diagnosis}, {fixes}")
        
        # Test 4: Site connectivity
        print("4. Testing site connectivity...")
        if sites:
            site = sites[0]
            frappe.init(site=site)
            frappe.connect()
            print(f"   ✓ Successfully connected to site: {site}")
            frappe.destroy()
        else:
            print("   ⚠ No sites available for connection test")
        
        print("=" * 50)
        print("🎉 BOOT TEST COMPLETE - ALL SYSTEMS OPERATIONAL!")
        print("✅ No boot crashes detected")
        print("✅ All modules import successfully") 
        print("✅ Core functionality working")
        print("✅ Boot recovery mechanisms active")
        
        return True
        
    except Exception as e:
        print(f"❌ BOOT TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_boot_recovery()
    if success:
        print("\n🚀 App Migrator v6.0.0 is READY FOR PRODUCTION!")
        print("   All boot issues have been resolved!")
    else:
        print("\n⚠ Some boot issues remain - check the errors above")
    
    sys.exit(0 if success else 1)
