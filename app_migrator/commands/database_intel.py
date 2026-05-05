"""
💾 Database Intelligence - Database Analysis and Migration Tools
"""

import frappe
from frappe.utils import get_sites


def get_database_info(site_name):
    """Get comprehensive database information for a site"""
    try:
        frappe.init(site_name)
        frappe.connect(site=site_name)

        print(f"💾 DATABASE INFO: {site_name}")
        print("=" * 40)

        # Basic info
        print(f"📊 Database: {frappe.conf.db_name}")
        print(f"🏠 Host: {frappe.conf.db_host}")

        # Table count
        tables = frappe.db.sql("SHOW TABLES", as_dict=True)
        print(f"📋 Tables: {len(tables)}")

        # DocType count
        doctypes = frappe.get_all("DocType", filters={"custom": 0})
        custom_doctypes = frappe.get_all("DocType", filters={"custom": 1})
        print(f"📄 DocTypes: {len(doctypes)} standard, {len(custom_doctypes)} custom")

        frappe.db.close()
        return True

    except Exception as e:
        print(f"❌ Database info failed: {e}")
        return False

def analyze_site_compatibility(source_site, target_site):
    """Analyze compatibility between two sites"""
    print("🔍 ANALYZING SITE COMPATIBILITY")
    print(f"   Source: {source_site} → Target: {target_site}")

    try:
        # Get source site apps
        frappe.init(source_site)
        frappe.connect(site=source_site)
        source_apps = frappe.get_installed_apps()
        frappe.db.close()

        # Get target site apps
        frappe.init(target_site)
        frappe.connect(site=target_site)
        target_apps = frappe.get_installed_apps()
        frappe.db.close()

        # Analysis
        common_apps = set(source_apps) & set(target_apps)
        missing_apps = set(source_apps) - set(target_apps)

        print("📊 COMPATIBILITY ANALYSIS:")
        print(f"   ✅ Common apps: {len(common_apps)}")
        print(f"   📦 Missing apps: {len(missing_apps)}")

        if missing_apps:
            print("   🎯 Apps to migrate:")
            for app in sorted(missing_apps):
                print(f"      • {app}")

        return len(missing_apps) == 0

    except Exception as e:
        print(f"❌ Compatibility analysis failed: {e}")
        return False
