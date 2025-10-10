"""
Enhanced Interactive Wizard - V5.0.0
Comprehensive migration wizard with site listing, app listing, module classification, and status filtering

Features:
- Site selection with validation
- App browsing and selection
- Module classification (Standard/Customized/Custom/Orphan)
- Status-based filtering
- Risk assessment
- Step-by-step guided workflow
"""

import click
import frappe
from frappe.utils import get_sites
import os
import json
from pathlib import Path
from .doctype_classifier import (
    get_doctype_classification,
    get_all_doctypes_by_app,
    DoctypeStatus,
    display_classification_summary,
    display_detailed_classifications,
    generate_migration_risk_assessment
)


def select_site():
    """
    Interactive site selection with validation
    Returns: selected site name or None if cancelled
    """
    print("\n" + "=" * 70)
    print("📋 STEP 1: SITE SELECTION")
    print("=" * 70)
    
    sites = get_sites()
    if not sites:
        print("❌ No sites available")
        return None
    
    print("\n📍 Available Sites:")
    print("  0. ❌ EXIT")
    for i, site in enumerate(sites, 1):
        print(f"  {i}. {site}")
    
    while True:
        try:
            choice_input = input(f"\n🔹 Select site (0-{len(sites)}): ").strip()
            site_choice = int(choice_input)
            
            if site_choice == 0:
                print("🚫 Operation cancelled by user")
                return None
            elif 1 <= site_choice <= len(sites):
                selected_site = sites[site_choice - 1]
                print(f"✅ Selected site: {selected_site}")
                return selected_site
            else:
                print(f"❌ Please enter a number between 0 and {len(sites)}")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n🚫 Operation cancelled by user")
            return None


def list_apps_in_site(site):
    """
    List all apps in the selected site with detailed information
    Returns: list of app names
    """
    print("\n" + "=" * 70)
    print("📋 STEP 2: APP DISCOVERY")
    print("=" * 70)
    
    try:
        apps = frappe.get_all('Module Def', 
            fields=['DISTINCT app_name as name'], 
            filters={'app_name': ['is', 'set']}
        )
        app_names = sorted([app['name'] for app in apps if app['name']])
        
        if not app_names:
            print("❌ No apps found in this site")
            return []
        
        print(f"\n📦 Found {len(app_names)} apps:")
        for i, app in enumerate(app_names, 1):
            # Get module count for each app
            module_count = frappe.db.count('Module Def', {'app_name': app})
            print(f"  {i}. {app:30s} ({module_count} modules)")
        
        return app_names
        
    except Exception as e:
        print(f"❌ Failed to list apps: {e}")
        return []


def select_app(app_names, prompt="Select app"):
    """
    Interactive app selection from available apps
    Returns: selected app name or None if cancelled
    """
    if not app_names:
        print("❌ No apps available")
        return None
    
    print(f"\n🔹 {prompt}:")
    print("  0. ❌ CANCEL")
    for i, app in enumerate(app_names, 1):
        print(f"  {i}. {app}")
    
    while True:
        try:
            choice_input = input(f"\n🔹 Select (0-{len(app_names)}): ").strip()
            choice = int(choice_input)
            
            if choice == 0:
                print("🚫 Selection cancelled")
                return None
            elif 1 <= choice <= len(app_names):
                selected_app = app_names[choice - 1]
                print(f"✅ Selected: {selected_app}")
                return selected_app
            else:
                print(f"❌ Please enter a number between 0 and {len(app_names)}")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n🚫 Selection cancelled")
            return None


def analyze_app_modules(app_name):
    """
    Analyze app modules with enhanced classification
    Shows Standard/Customized/Custom/Orphan status for each doctype
    """
    print("\n" + "=" * 70)
    print(f"📊 MODULE ANALYSIS: {app_name}")
    print("=" * 70)
    
    try:
        # Get all modules for this app
        modules = frappe.get_all('Module Def',
            filters={'app_name': app_name},
            fields=['name', 'module_name', 'app_name'],
            order_by='module_name'
        )
        
        if not modules:
            print(f"❌ No modules found for {app_name}")
            return None
        
        print(f"\n📦 Found {len(modules)} modules in {app_name}\n")
        
        module_data = []
        for module in modules:
            # Get doctypes for this module
            doctypes = frappe.get_all('DocType',
                filters={'module': module['module_name']},
                fields=['name', 'custom', 'app']
            )
            
            # Classify each doctype
            classifications = []
            status_counts = {}
            for dt in doctypes:
                classification = get_doctype_classification(dt['name'])
                classifications.append(classification)
                status = classification.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            module_data.append({
                'module': module,
                'doctypes': doctypes,
                'classifications': classifications,
                'status_counts': status_counts
            })
        
        # Display module summary
        for idx, data in enumerate(module_data, 1):
            module_name = data['module']['module_name']
            doctype_count = len(data['doctypes'])
            status_counts = data['status_counts']
            
            # Build status summary string
            status_parts = []
            if status_counts.get(DoctypeStatus.STANDARD, 0) > 0:
                status_parts.append(f"✅{status_counts[DoctypeStatus.STANDARD]}S")
            if status_counts.get(DoctypeStatus.CUSTOMIZED, 0) > 0:
                status_parts.append(f"⚙️{status_counts[DoctypeStatus.CUSTOMIZED]}M")
            if status_counts.get(DoctypeStatus.CUSTOM, 0) > 0:
                status_parts.append(f"🔧{status_counts[DoctypeStatus.CUSTOM]}C")
            if status_counts.get(DoctypeStatus.ORPHAN, 0) > 0:
                status_parts.append(f"⚠️{status_counts[DoctypeStatus.ORPHAN]}O")
            
            status_summary = " ".join(status_parts) if status_parts else "📋"
            
            print(f"  {idx:2d}. {module_name:35s} ({doctype_count:3d} doctypes) [{status_summary}]")
        
        print("\n📊 Legend: S=Standard, M=Modified (Customized), C=Custom, O=Orphan")
        
        return module_data
        
    except Exception as e:
        print(f"❌ Module analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def filter_by_status(module_data):
    """
    Filter doctypes by status and display filtered results
    """
    print("\n" + "=" * 70)
    print("🔍 FILTER BY STATUS")
    print("=" * 70)
    
    print("\nAvailable filters:")
    print("  1. ✅ Standard doctypes only")
    print("  2. ⚙️ Customized doctypes only")
    print("  3. 🔧 Custom doctypes only")
    print("  4. ⚠️ Orphan doctypes only")
    print("  5. 📋 All doctypes (no filter)")
    print("  0. ❌ BACK")
    
    status_map = {
        1: DoctypeStatus.STANDARD,
        2: DoctypeStatus.CUSTOMIZED,
        3: DoctypeStatus.CUSTOM,
        4: DoctypeStatus.ORPHAN,
        5: None  # All
    }
    
    while True:
        try:
            choice_input = input("\n🔹 Select filter (0-5): ").strip()
            choice = int(choice_input)
            
            if choice == 0:
                return None
            elif choice in status_map:
                filter_status = status_map[choice]
                
                # Collect all doctypes matching the filter
                filtered_doctypes = []
                for data in module_data:
                    for classification in data['classifications']:
                        if filter_status is None or classification.get('status') == filter_status:
                            filtered_doctypes.append(classification)
                
                if not filtered_doctypes:
                    print(f"\n❌ No doctypes found with selected status")
                    continue
                
                # Display filtered results
                print(f"\n📋 Found {len(filtered_doctypes)} matching doctypes:")
                display_detailed_classifications(filtered_doctypes, limit=20)
                
                return filtered_doctypes
            else:
                print("❌ Please enter a number between 0 and 5")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n🚫 Filter cancelled")
            return None


def interactive_migration_wizard():
    """
    Main interactive migration wizard with enhanced features
    Supports site selection, app listing, module classification, and status filtering
    """
    print("\n" + "=" * 70)
    print("🧙 ENHANCED INTERACTIVE MIGRATION WIZARD V5.0.0")
    print("=" * 70)
    print("\n🚀 Complete migration workflow with advanced classification")
    
    try:
        # Step 1: Select site
        selected_site = select_site()
        if not selected_site:
            return
        
        # Initialize Frappe with selected site
        frappe.init(site=selected_site)
        frappe.connect()
        
        # Step 2: List and analyze apps
        app_names = list_apps_in_site(selected_site)
        if not app_names:
            frappe.destroy()
            return
        
        # Step 3: Select source app
        print("\n" + "=" * 70)
        print("📋 STEP 3: SOURCE APP SELECTION")
        print("=" * 70)
        source_app = select_app(app_names, "Select SOURCE app")
        if not source_app:
            frappe.destroy()
            return
        
        # Step 4: Analyze source app modules
        module_data = analyze_app_modules(source_app)
        if not module_data:
            frappe.destroy()
            return
        
        # Step 5: Interactive menu
        while True:
            print("\n" + "=" * 70)
            print("📋 MIGRATION OPTIONS")
            print("=" * 70)
            print("\n  1. 🔍 Filter doctypes by status")
            print("  2. 📊 Show full classification summary")
            print("  3. ⚠️ Generate risk assessment")
            print("  4. 🚀 Start migration (select target app)")
            print("  5. 🔄 Analyze different app")
            print("  0. ❌ EXIT")
            
            try:
                choice_input = input("\n🔹 Select option (0-5): ").strip()
                choice = int(choice_input)
                
                if choice == 0:
                    print("\n🎉 Wizard completed!")
                    break
                
                elif choice == 1:
                    # Filter by status
                    filter_by_status(module_data)
                
                elif choice == 2:
                    # Show full classification summary
                    all_classifications = []
                    for data in module_data:
                        all_classifications.extend(data['classifications'])
                    display_classification_summary(all_classifications)
                    display_detailed_classifications(all_classifications, limit=10)
                
                elif choice == 3:
                    # Generate risk assessment
                    print("\n🔹 Enter doctype name for risk assessment:")
                    doctype_name = input("Doctype: ").strip()
                    if doctype_name:
                        risk = generate_migration_risk_assessment(doctype_name)
                        print("\n" + "=" * 70)
                        print(f"⚠️ RISK ASSESSMENT: {risk['doctype']}")
                        print("=" * 70)
                        print(f"\nStatus: {risk['status'].upper()}")
                        print(f"Risk Level: {risk['risk_level']}")
                        print(f"\nDescription: {risk['description']}")
                        print("\n📋 Recommendations:")
                        for rec in risk['recommendations']:
                            print(f"  • {rec}")
                
                elif choice == 4:
                    # Start migration - select target app
                    print("\n" + "=" * 70)
                    print("📋 STEP 6: TARGET APP SELECTION")
                    print("=" * 70)
                    target_app = select_app(app_names, "Select TARGET app")
                    if target_app:
                        print(f"\n✅ Migration planned: {source_app} → {target_app}")
                        print("\n⚠️ Migration execution not yet implemented in this wizard")
                        print("💡 Use migration_engine.py for actual migration")
                
                elif choice == 5:
                    # Analyze different app
                    source_app = select_app(app_names, "Select app to analyze")
                    if source_app:
                        module_data = analyze_app_modules(source_app)
                        if not module_data:
                            continue
                
                else:
                    print("❌ Please enter a number between 0 and 5")
            
            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\n🚫 Wizard cancelled by user")
                break
        
        frappe.destroy()
        
    except KeyboardInterrupt:
        print("\n\n🚫 Wizard cancelled by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Wizard failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            frappe.destroy()
        except:
            pass


def guided_migration_workflow():
    """
    Display guided workflow steps for migration
    """
    print("\n" + "=" * 70)
    print("🎯 GUIDED MIGRATION WORKFLOW")
    print("=" * 70)
    
    workflow_steps = [
        ("1. 🔍 Analysis", "bench --site [site] migrate-app analyze [app_name]"),
        ("2. 📋 Classification", "bench --site [site] migrate-app classify [app_name]"),
        ("3. ⚠️ Risk Assessment", "bench --site [site] migrate-app risk-assess [app_name]"),
        ("4. 🚀 Execute Migration", "bench --site [site] migrate-app migrate [source] [target]"),
        ("5. ✅ Verification", "bench --site [site] migrate-app verify [app_name]")
    ]
    
    for step, command in workflow_steps:
        print(f"\n{step}")
        print(f"  $ {command}")
    
    print("\n" + "=" * 70)
    print("💡 Use the interactive wizard for guided step-by-step process:")
    print("  $ bench --site [site] migrate-app wizard")
    print("=" * 70)


if __name__ == "__main__":
    # For testing
    interactive_migration_wizard()
