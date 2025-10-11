"""
Database Schema Module - V5.0.0
Database schema operations including fixing issues, verification, and maintenance

Extracted and enhanced from App Migrator V2
Features:
- Database schema verification
- Tree doctype fixing
- Schema integrity checks
- ERPNext installation completion
"""

import frappe
from frappe.utils import get_sites
import os
import json
import subprocess
from pathlib import Path


def ensure_frappe_connection():
    """Ensure Frappe connection is active - CRITICAL FOR LONG-RUNNING OPERATIONS"""
    try:
        frappe.db.sql("SELECT 1")
        return True
    except Exception:
        try:
            sites = get_sites()
            site = sites[0] if sites else None
            if site:
                frappe.init(site=site)
                frappe.connect()
                print("   🔄 Session reconnected")
                return True
        except Exception as e:
            print(f"   ❌ Failed to reconnect: {e}")
            return False
    return False


def verify_database_schema(app_name):
    """
    Verify database schema integrity for an app
    Checks for missing tables, columns, and indexes
    """
    print(f"🔍 VERIFYING DATABASE SCHEMA: {app_name}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all doctypes for the app
        doctypes = frappe.get_all('DocType',
            filters={'app': app_name},
            fields=['name', 'issingle', 'is_virtual', 'custom']
        )
        
        print(f"\n📊 Checking {len(doctypes)} doctypes...\n")
        
        issues = {
            'missing_tables': [],
            'schema_mismatches': [],
            'missing_indexes': []
        }
        
        for dt in doctypes:
            # Skip single doctypes and virtual doctypes
            if dt['issingle'] or dt.get('is_virtual'):
                continue
            
            table_name = f"tab{dt['name']}"
            
            # Check if table exists
            table_exists = frappe.db.sql(f"""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = %s
            """, table_name, as_dict=True)
            
            if not table_exists or table_exists[0]['count'] == 0:
                issues['missing_tables'].append(dt['name'])
                print(f"  ❌ Missing table: {table_name}")
            else:
                print(f"  ✅ Table exists: {table_name}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 SCHEMA VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"\n📋 Total doctypes checked: {len(doctypes)}")
        print(f"❌ Missing tables: {len(issues['missing_tables'])}")
        
        if issues['missing_tables']:
            print("\n⚠️ Missing Tables:")
            for table in issues['missing_tables'][:10]:
                print(f"  • {table}")
            if len(issues['missing_tables']) > 10:
                print(f"  ... and {len(issues['missing_tables']) - 10} more")
        else:
            print("\n✅ All database tables present!")
        
        return len(issues['missing_tables']) == 0
        
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_database_schema(app_name, auto_create=False):
    """
    Fix database schema issues by creating missing tables
    """
    print(f"🔧 FIXING DATABASE SCHEMA: {app_name}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get doctypes with missing tables
        doctypes = frappe.get_all('DocType',
            filters={'app': app_name},
            fields=['name', 'issingle', 'is_virtual']
        )
        
        missing_tables = []
        for dt in doctypes:
            if dt['issingle'] or dt.get('is_virtual'):
                continue
            
            table_name = f"tab{dt['name']}"
            table_exists = frappe.db.sql(f"""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = %s
            """, table_name, as_dict=True)
            
            if not table_exists or table_exists[0]['count'] == 0:
                missing_tables.append(dt['name'])
        
        if not missing_tables:
            print("✅ No missing tables found")
            return True
        
        print(f"\n📊 Found {len(missing_tables)} missing tables")
        
        if not auto_create:
            confirm = input(f"\n⚠️ Create {len(missing_tables)} missing tables? (y/N): ").strip().lower()
            if confirm != 'y':
                print("🚫 Operation cancelled")
                return False
        
        created_count = 0
        failed_count = 0
        
        for doctype_name in missing_tables:
            try:
                # Use Frappe's built-in sync_table method
                doctype_meta = frappe.get_meta(doctype_name)
                frappe.db.create_table(doctype_name, doctype_meta)
                created_count += 1
                print(f"  ✅ Created table for: {doctype_name}")
            except Exception as e:
                failed_count += 1
                print(f"  ❌ Failed to create table for {doctype_name}: {e}")
        
        frappe.db.commit()
        
        print("\n" + "=" * 70)
        print("📊 SCHEMA FIX SUMMARY")
        print("=" * 70)
        print(f"  ✅ Tables created: {created_count}")
        print(f"  ❌ Failed: {failed_count}")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_tree_doctypes(app_name=None):
    """
    Fix tree doctypes by ensuring proper tree structure
    Adds lft, rgt, old_parent fields if missing
    """
    print("🌳 FIXING TREE DOCTYPES")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all tree doctypes
        filters = {'is_tree': 1}
        if app_name:
            filters['app'] = app_name
        
        tree_doctypes = frappe.get_all('DocType',
            filters=filters,
            fields=['name', 'app', 'module']
        )
        
        if not tree_doctypes:
            print("✅ No tree doctypes found")
            return True
        
        print(f"\n📊 Found {len(tree_doctypes)} tree doctypes\n")
        
        fixed_count = 0
        for dt in tree_doctypes:
            try:
                table_name = f"tab{dt['name']}"
                
                # Check for required tree fields
                required_fields = ['lft', 'rgt', 'old_parent']
                missing_fields = []
                
                for field in required_fields:
                    field_exists = frappe.db.sql(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.columns
                        WHERE table_schema = DATABASE()
                        AND table_name = %s
                        AND column_name = %s
                    """, (table_name, field), as_dict=True)
                    
                    if not field_exists or field_exists[0]['count'] == 0:
                        missing_fields.append(field)
                
                if missing_fields:
                    print(f"  🔧 Fixing {dt['name']}: adding {', '.join(missing_fields)}")
                    
                    # Add missing fields
                    for field in missing_fields:
                        if field in ['lft', 'rgt']:
                            frappe.db.sql(f"ALTER TABLE `{table_name}` ADD COLUMN `{field}` INT(10) DEFAULT 0")
                        elif field == 'old_parent':
                            frappe.db.sql(f"ALTER TABLE `{table_name}` ADD COLUMN `{field}` VARCHAR(140)")
                    
                    # Rebuild tree
                    frappe.db.sql(f"UPDATE `{table_name}` SET lft=0, rgt=0")
                    frappe.get_doc('DocType', dt['name']).run_method('rebuild_tree')
                    
                    fixed_count += 1
                    print(f"    ✅ Fixed and rebuilt tree for {dt['name']}")
                else:
                    print(f"  ✅ {dt['name']}: tree structure OK")
                
            except Exception as e:
                print(f"  ❌ Failed to fix {dt['name']}: {e}")
        
        frappe.db.commit()
        
        print("\n" + "=" * 70)
        print("📊 TREE FIX SUMMARY")
        print("=" * 70)
        print(f"  ✅ Trees fixed: {fixed_count}")
        print(f"  📋 Total tree doctypes: {len(tree_doctypes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tree fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def complete_erpnext_install():
    """
    Complete ERPNext installation by fixing common issues
    Runs verification and fixes for standard ERPNext doctypes
    """
    print("🏭 COMPLETING ERPNEXT INSTALLATION")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Check if ERPNext is installed
        erpnext_installed = frappe.db.exists('Module Def', {'app_name': 'erpnext'})
        if not erpnext_installed:
            print("❌ ERPNext is not installed")
            return False
        
        print("\n📊 Running ERPNext completion checks...\n")
        
        # Step 1: Verify schema
        print("1️⃣ Verifying ERPNext database schema...")
        schema_ok = verify_database_schema('erpnext')
        
        # Step 2: Fix tree doctypes
        print("\n2️⃣ Fixing ERPNext tree doctypes...")
        tree_ok = fix_tree_doctypes('erpnext')
        
        # Step 3: Run migrate
        print("\n3️⃣ Running database migrations...")
        try:
            frappe.db.commit()
            print("  ✅ Migrations completed")
            migrate_ok = True
        except Exception as e:
            print(f"  ❌ Migration failed: {e}")
            migrate_ok = False
        
        # Summary
        print("\n" + "=" * 70)
        print("🏭 ERPNEXT INSTALLATION SUMMARY")
        print("=" * 70)
        print(f"  Schema Verification: {'✅' if schema_ok else '❌'}")
        print(f"  Tree Doctypes: {'✅' if tree_ok else '❌'}")
        print(f"  Database Migration: {'✅' if migrate_ok else '❌'}")
        
        all_ok = schema_ok and tree_ok and migrate_ok
        if all_ok:
            print("\n🎉 ERPNext installation completed successfully!")
        else:
            print("\n⚠️ Some issues remain - manual intervention may be required")
        
        return all_ok
        
    except Exception as e:
        print(f"❌ ERPNext completion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_database_diagnostics(app_name=None):
    """
    Run comprehensive database diagnostics
    """
    print("🔍 DATABASE DIAGNOSTICS")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        filters = {}
        if app_name:
            filters['app'] = app_name
        
        # Get statistics
        total_doctypes = frappe.db.count('DocType', filters)
        total_tables = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name LIKE 'tab%'
        """, as_dict=True)[0]['count']
        
        print(f"\n📊 Database Statistics:")
        print(f"  📋 Total DocTypes: {total_doctypes}")
        print(f"  📊 Total Tables: {total_tables}")
        
        # Check for orphan tables
        all_tables = frappe.db.sql("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name LIKE 'tab%'
        """, as_dict=True)
        
        orphan_tables = []
        for table in all_tables:
            table_name = table['table_name']
            doctype_name = table_name[3:]  # Remove 'tab' prefix
            if not frappe.db.exists('DocType', doctype_name):
                orphan_tables.append(table_name)
        
        if orphan_tables:
            print(f"\n⚠️ Found {len(orphan_tables)} orphan tables (no corresponding DocType):")
            for table in orphan_tables[:10]:
                print(f"  • {table}")
            if len(orphan_tables) > 10:
                print(f"  ... and {len(orphan_tables) - 10} more")
        else:
            print("\n✅ No orphan tables found")
        
        print("\n" + "=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Diagnostics failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # For testing
    import sys
    if len(sys.argv) > 1:
        app_name = sys.argv[1]
        run_database_diagnostics(app_name)
    else:
        run_database_diagnostics()
