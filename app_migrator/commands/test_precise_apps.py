import frappe
from frappe.utils import get_sites

print("🔍 PRECISE APP COUNT VERIFICATION")
print("=" * 45)

sites = get_sites()
actual_apps = {}

for site in sites:
    print(f"\n🌐 Testing: {site}")
    try:
        # Force fresh connection
        frappe.init(site)
        frappe.connect(site=site)
        
        # Get ACTUAL installed apps from database
        apps = frappe.get_installed_apps()
        actual_apps[site] = apps
        
        print(f"   🗄️  Database: {frappe.conf.db_name}")
        print(f"   📦 ACTUAL Apps: {len(apps)}")
        print(f"   📋 Apps: {apps}")
        
        frappe.db.close()
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

print(f"\n📊 SUMMARY:")
for site, apps in actual_apps.items():
    print(f"   {site}: {len(apps)} apps")

# Check if they're different
if len(actual_apps) >= 2:
    sites_list = list(actual_apps.keys())
    apps1 = set(actual_apps[sites_list[0]])
    apps2 = set(actual_apps[sites_list[1]])
    
    if apps1 != apps2:
        print(f"\n✅ SUCCESS: Sites have DIFFERENT apps!")
        print(f"   Unique to {sites_list[0]}: {apps1 - apps2}")
        print(f"   Unique to {sites_list[1]}: {apps2 - apps1}")
    else:
        print(f"\n⚠️  WARNING: Sites have IDENTICAL apps")
