"""
Enhanced Interactive Wizard - v5.0.0
Provides better user interaction with:
- Site listing and selection
- Module listing with status
- DocType classification (orphan/customized/standard/custom)
- Smart filtering and selection
"""

import click
import frappe
from frappe.utils import get_sites
import os
from .doctype_classifier import (
    get_doctype_classification,
    get_all_doctypes_by_app,
    DoctypeStatus,
    display_classification_summary,
    display_detailed_classifications
)

def list_all_sites():
    """
    List all available sites with status information
    """
    try:
        sites = get_sites()
        
        print("\n" + "=" * 80)
        print("🌐 AVAILABLE SITES")
        print("=" * 80)
        
        if not sites:
            print("❌ No sites found")
            return []
        
        for idx, site in enumerate(sites, 1):
            # Check if site exists
            site_path = frappe.get_site_path(site)
            exists = os.path.exists(site_path)
            status = "✅ Active" if exists else "❌ Inactive"
            
            print(f"{idx}. {site:30s} - {status}")
        
        print("=" * 80 + "\n")
        
        return sites
    except Exception as e:
        print(f"❌ Error listing sites: {str(e)}")
        return []

def select_site_interactive():
    """
    Interactive site selection
    """
    sites = list_all_sites()
    
    if not sites:
        print("❌ No sites available for selection")
        return None
    
    while True:
        try:
            choice = input("\n🎯 Enter site number (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Exiting...")
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(sites):
                selected = sites[idx]
                print(f"✅ Selected site: {selected}")
                return selected
            else:
                print(f"❌ Invalid selection. Please choose 1-{len(sites)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            return None

def list_apps_in_site(site_name=None):
    """
    List all installed apps in a site
    """
    try:
        if not site_name:
            site_name = frappe.local.site
        
        # Get installed apps
        apps = frappe.get_installed_apps()
        
        print("\n" + "=" * 80)
        print(f"📦 INSTALLED APPS IN SITE: {site_name}")
        print("=" * 80)
        
        if not apps:
            print("❌ No apps found")
            return []
        
        for idx, app in enumerate(apps, 1):
            # Try to get app info
            try:
                app_path = frappe.get_app_path(app)
                exists = os.path.exists(app_path)
                status = "✅" if exists else "❌"
                
                print(f"{idx}. {status} {app}")
            except:
                print(f"{idx}. ❓ {app}")
        
        print("=" * 80 + "\n")
        
        return apps
    except Exception as e:
        print(f"❌ Error listing apps: {str(e)}")
        return []

def select_app_interactive():
    """
    Interactive app selection
    """
    apps = list_apps_in_site()
    
    if not apps:
        print("❌ No apps available for selection")
        return None
    
    while True:
        try:
            choice = input("\n🎯 Enter app number (or 'q' to quit): ").strip()
            
            if choice.lower() == 'q':
                print("👋 Exiting...")
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(apps):
                selected = apps[idx]
                print(f"✅ Selected app: {selected}")
                return selected
            else:
                print(f"❌ Invalid selection. Please choose 1-{len(apps)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled by user")
            return None

def list_modules_in_app(app_name):
    """
    List all modules/doctypes in an app with classification
    """
    try:
        print(f"\n🔍 Analyzing app: {app_name}...")
        
        # Get all doctypes for this app
        classifications = get_all_doctypes_by_app(app_name)
        
        if not classifications:
            print(f"❌ No doctypes found for app: {app_name}")
            return []
        
        # Display summary
        display_classification_summary(classifications)
        
        # Ask if user wants detailed view
        show_details = input("\n📋 Show detailed classifications? (y/n): ").strip().lower()
        
        if show_details == 'y':
            display_detailed_classifications(classifications)
        
        return classifications
    except Exception as e:
        print(f"❌ Error listing modules: {str(e)}")
        return []

def select_doctypes_by_status(app_name):
    """
    Select doctypes filtered by status (orphan/customized/standard/custom)
    """
    try:
        classifications = get_all_doctypes_by_app(app_name)
        
        if not classifications:
            print(f"❌ No doctypes found for app: {app_name}")
            return []
        
        print("\n" + "=" * 80)
        print("🎯 FILTER DOCTYPES BY STATUS")
        print("=" * 80)
        print("\n1. ✅ Standard (not modified)")
        print("2. ⚙️  Customized (has Custom Fields or Property Setters)")
        print("3. 🔧 Custom (user-created)")
        print("4. ⚠️  Orphan (app=None or missing)")
        print("5. 📋 All doctypes")
        print("0. ❌ Cancel")
        
        while True:
            try:
                choice = input("\n🎯 Select filter (0-5): ").strip()
                
                if choice == '0':
                    print("👋 Cancelled")
                    return []
                
                filter_map = {
                    '1': DoctypeStatus.STANDARD,
                    '2': DoctypeStatus.CUSTOMIZED,
                    '3': DoctypeStatus.CUSTOM,
                    '4': DoctypeStatus.ORPHAN,
                    '5': None  # All
                }
                
                if choice in filter_map:
                    filter_status = filter_map[choice]
                    
                    if filter_status:
                        filtered = [c for c in classifications if c.get('status') == filter_status]
                        print(f"\n✅ Filtered to: {filter_status.upper()} doctypes")
                    else:
                        filtered = classifications
                        print("\n✅ Showing all doctypes")
                    
                    if not filtered:
                        print(f"❌ No doctypes found with selected filter")
                        continue
                    
                    # Display the filtered list
                    print("\n" + "=" * 80)
                    print(f"📋 FILTERED DOCTYPES ({len(filtered)} total)")
                    print("=" * 80)
                    
                    for idx, c in enumerate(filtered, 1):
                        status = c.get('status', 'unknown')
                        name = c.get('name', 'Unknown')
                        details = ', '.join(c.get('details', [])) if c.get('details') else 'No customizations'
                        
                        status_icons = {
                            DoctypeStatus.STANDARD: "✅",
                            DoctypeStatus.CUSTOMIZED: "⚙️",
                            DoctypeStatus.CUSTOM: "🔧",
                            DoctypeStatus.ORPHAN: "⚠️"
                        }
                        
                        icon = status_icons.get(status, "📋")
                        print(f"{idx:3d}. {icon} {name:40s} - {details}")
                    
                    print("=" * 80)
                    
                    return filtered
                else:
                    print("❌ Invalid choice. Please select 0-5")
                    
            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\n👋 Cancelled by user")
                return []
                
    except Exception as e:
        print(f"❌ Error filtering doctypes: {str(e)}")
        return []

def interactive_migration_wizard():
    """
    Complete interactive migration wizard with enhanced features
    
    Enhanced features:
    - Site listing and selection
    - App listing and selection
    - Module/DocType listing with status classification
    - Status-based filtering (orphan/customized/standard/custom)
    - Action selection per doctype
    """
    print("\n" + "=" * 80)
    print("🎨 ENHANCED INTERACTIVE MIGRATION WIZARD v5.0.0")
    print("=" * 80)
    print("\nThis wizard will guide you through:")
    print("  1. Site selection")
    print("  2. App selection (source & target)")
    print("  3. Module/DocType analysis with status classification")
    print("  4. Action selection based on doctype status")
    print("\n" + "=" * 80 + "\n")
    
    # Step 1: Select site
    print("\n📍 STEP 1: Select Site")
    print("-" * 80)
    selected_site = select_site_interactive()
    
    if not selected_site:
        print("❌ No site selected. Exiting wizard.")
        return
    
    # Initialize Frappe for the selected site
    try:
        frappe.init(site=selected_site)
        frappe.connect()
    except Exception as e:
        print(f"❌ Error connecting to site {selected_site}: {str(e)}")
        return
    
    # Step 2: Select source app
    print("\n📍 STEP 2: Select Source App")
    print("-" * 80)
    source_app = select_app_interactive()
    
    if not source_app:
        print("❌ No source app selected. Exiting wizard.")
        return
    
    # Step 3: Analyze modules in source app
    print("\n📍 STEP 3: Analyze Modules/DocTypes")
    print("-" * 80)
    classifications = list_modules_in_app(source_app)
    
    if not classifications:
        print("❌ No modules found. Exiting wizard.")
        return
    
    # Step 4: Filter by status
    print("\n📍 STEP 4: Filter DocTypes by Status")
    print("-" * 80)
    filtered_doctypes = select_doctypes_by_status(source_app)
    
    if not filtered_doctypes:
        print("❌ No doctypes selected. Exiting wizard.")
        return
    
    # Step 5: Select target app
    print("\n📍 STEP 5: Select Target App")
    print("-" * 80)
    print("\n💡 The selected doctypes will be migrated to the target app")
    target_app = select_app_interactive()
    
    if not target_app:
        print("❌ No target app selected. Exiting wizard.")
        return
    
    # Step 6: Confirm and execute
    print("\n📍 STEP 6: Confirmation")
    print("=" * 80)
    print(f"\n📦 Migration Summary:")
    print(f"   Site: {selected_site}")
    print(f"   Source App: {source_app}")
    print(f"   Target App: {target_app}")
    print(f"   DocTypes: {len(filtered_doctypes)}")
    print(f"\n📋 DocTypes to migrate:")
    
    for idx, dt in enumerate(filtered_doctypes[:10], 1):
        print(f"   {idx}. {dt.get('name')}")
    
    if len(filtered_doctypes) > 10:
        print(f"   ... and {len(filtered_doctypes) - 10} more")
    
    print("\n" + "=" * 80)
    
