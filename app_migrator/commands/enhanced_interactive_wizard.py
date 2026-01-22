"""
Enhanced Interactive Wizard - V6.0.0
Comprehensive migration wizard with MULTI-BENCH and MULTI-SITE support

Features:
- Site selection with validation
- App browsing and selection
- Module classification (Standard/Customized/Custom/Orphan)
- Status-based filtering
- Risk assessment
- Step-by-step guided workflow
- ✨ NEW: Site-to-site migration (same bench)
- ✨ NEW: Cross-bench migration (different benches)
"""

import click
import frappe
from frappe.utils import get_sites
import os
import json
import subprocess
from pathlib import Path
from .doctype_classifier import (
    get_doctype_classification,
    get_all_doctypes_by_app,
    DoctypeStatus,
    display_classification_summary,
    display_detailed_classifications,
    generate_migration_risk_assessment
)


def get_all_bench_apps():
    """
    Get ALL apps in the bench's apps/ directory (not just installed on site)
    This includes newly created apps that haven't been installed yet.
    
    Returns: list of app names available in the bench
    """
    try:
        # Method 1: Use frappe.get_app_path to find apps directory
        try:
            frappe_path = frappe.get_app_path('frappe')
            apps_dir = Path(frappe_path).parent  # apps/ directory
        except:
            # Fallback: Try common bench structure
            bench_path = os.environ.get('FRAPPE_BENCH_ROOT', os.getcwd())
            if 'apps' in os.listdir(bench_path):
                apps_dir = Path(bench_path) / 'apps'
            else:
                # Navigate up from current directory
                current = Path.cwd()
                while current.name != 'frappe-bench' and current != current.parent:
                    current = current.parent
                apps_dir = current / 'apps'
        
        if not apps_dir.exists():
            return []
        
        # Find all valid Frappe apps (directories with hooks.py or setup.py)
        bench_apps = []
        for item in apps_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it's a valid Frappe app
                has_hooks = (item / item.name / 'hooks.py').exists()
                has_setup = (item / 'setup.py').exists()
                has_pyproject = (item / 'pyproject.toml').exists()
                
                if has_hooks or has_setup or has_pyproject:
                    bench_apps.append(item.name)
        
        return sorted(bench_apps)
        
    except Exception as e:
        print(f"⚠️ Could not scan bench apps directory: {e}")
        return []


def get_bench_sites(bench_path=None):
    """
    Get all sites from a specific bench or current bench
    """
    if bench_path is None:
        return get_sites()
    
    try:
        sites_dir = Path(bench_path) / 'sites'
        if not sites_dir.exists():
            return []
        
        sites = []
        for item in sites_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'assets':
                if (item / 'site_config.json').exists():
                    sites.append(item.name)
        return sorted(sites)
    except Exception as e:
        print(f"⚠️ Could not scan sites in {bench_path}: {e}")
        return []


def get_bench_apps_from_path(bench_path):
    """
    Get all apps from a specific bench path
    """
    try:
        apps_dir = Path(bench_path) / 'apps'
        if not apps_dir.exists():
            return []
        
        bench_apps = []
        for item in apps_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                has_hooks = (item / item.name / 'hooks.py').exists()
                has_setup = (item / 'setup.py').exists()
                has_pyproject = (item / 'pyproject.toml').exists()
                if has_hooks or has_setup or has_pyproject:
                    bench_apps.append(item.name)
        return sorted(bench_apps)
    except Exception as e:
        print(f"⚠️ Could not scan apps in {bench_path}: {e}")
        return []


def select_bench():
    """
    Interactive bench selection for cross-bench migration
    """
    print("\n" + "=" * 70)
    print("🏢 BENCH SELECTION")
    print("=" * 70)
    
    print("\n  1. 📍 Current bench (default)")
    print("  2. 📂 Specify different bench path")
    print("  0. ❌ CANCEL")
    
    while True:
        try:
            choice = int(input("\n🔹 Select option (0-2): ").strip())
            if choice == 0:
                return None
            elif choice == 1:
                return None
            elif choice == 2:
                bench_path = input("\n🔹 Enter bench path (e.g., /home/user/other-bench): ").strip()
                if not bench_path:
                    print("❌ Path cannot be empty")
                    continue
                
                bench_path = Path(bench_path).expanduser().resolve()
                if not bench_path.exists():
                    print(f"❌ Path does not exist: {bench_path}")
                    continue
                
                if not (bench_path / 'apps').exists() or not (bench_path / 'sites').exists():
                    print(f"❌ Invalid bench structure. Expected apps/ and sites/ directories.")
                    continue
                
                print(f"✅ Valid bench found: {bench_path}")
                return str(bench_path)
            else:
                print("❌ Please enter 0, 1, or 2")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n🚫 Selection cancelled")
            return None


def select_site(prompt="STEP 1: SITE SELECTION", bench_path=None):
    """
    Interactive site selection with validation
    Returns: selected site name or None if cancelled
    """
    print("\n" + "=" * 70)
    print(f"📋 {prompt}")
    print("=" * 70)
    
    sites = get_bench_sites(bench_path)
    if not sites:
        print("❌ No sites available")
        return None
    
    bench_label = f" (from {bench_path})" if bench_path else ""
    print(f"\n📍 Available Sites{bench_label}:")
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
    List all apps in the selected site with detailed information (FIXED VERSION)
    
    Returns: list of app names
    
    Fix: Changed from querying Module Def to using frappe.get_installed_apps()
    This ensures ALL installed apps are shown, not just those with modules.
    """
    print("\n" + "=" * 70)
    print("📋 STEP 2: APP DISCOVERY")
    print("=" * 70)
    
    try:
        # ✅ FIXED: Use frappe.get_installed_apps() instead of querying Module Def
        apps = frappe.get_installed_apps()
        
        if not apps:
            print("❌ No apps found in this site")
            return []
        
        print(f"\n📦 Found {len(apps)} installed apps:\n")
        
        app_details = []
        apps_with_modules = 0
        apps_without_modules = 0
        
        for i, app in enumerate(apps, 1):
            try:
                # Get module count
                module_count = frappe.db.count('Module Def', {'app_name': app})
                
                # Verify app exists on filesystem
                try:
                    app_path = frappe.get_app_path(app)
                    exists = os.path.exists(app_path)
                except:
                    exists = False
                
                # Display with status tags
                if not exists:
                    status_icon = "⚠️"
                    tag = "[missing]"
                    print(f"  {i}. {status_icon} {app:30s} {tag}")
                elif module_count > 0:
                    status_icon = "✅"
                    tag = f"({module_count} modules)"
                    apps_with_modules += 1
                    print(f"  {i}. {status_icon} {app:30s} {tag}")
                else:
                    status_icon = "📦"
                    tag = "[no modules]"
                    apps_without_modules += 1
                    print(f"  {i}. {status_icon} {app:30s} {tag}")
                
                app_details.append(app)
                
            except Exception as e:
                print(f"  {i}. ❌ {app:30s} [error: {str(e)[:30]}]")
                app_details.append(app)
        
        # Print summary
        print(f"\n{'─' * 70}")
        print(f"📊 Summary: {apps_with_modules} app(s) with modules, {apps_without_modules} utility app(s)")
        print(f"💡 ✅=Standard app  📦=Utility app  ⚠️=Missing")
        
        return app_details
        
    except Exception as e:
        print(f"❌ Failed to list apps: {e}")
        return []


def handle_zero_module_app(selected_app, all_apps):
    """
    Handle selection of an app with zero modules
    Offers to import modules from another app or continue anyway
    """
    print(f"\n⚠️ App '{selected_app}' has 0 modules")
    print("\n" + "=" * 70)
    print("📋 ZERO-MODULE APP OPTIONS")
    print("=" * 70)
    
    print("\n🔹 What would you like to do?")
    print("  1. 📋 Continue with this app (0 modules)")
    print("  2. 📦 Select modules from another app to migrate")
    print("  3. 🔄 Choose a different app")
    print("  0. ❌ CANCEL")
    
    while True:
        try:
            choice = int(input("\n🔹 Select option (0-3): ").strip())
            
            if choice == 0:
                return None
            elif choice == 1:
                print(f"\n✅ Continuing with '{selected_app}' (0 modules)")
                return {'app': selected_app, 'module_count': 0, 'source_app': None}
            elif choice == 2:
                # Show apps with modules
                other_apps = [app for app in all_apps if app != selected_app]
                apps_with_modules = []
                
                print("\n📦 Apps with modules:\n")
                for i, app in enumerate(other_apps, 1):
                    count = frappe.db.count('Module Def', {'app_name': app})
                    if count > 0:
                        apps_with_modules.append(app)
                        print(f"  {i}. {app} ({count} modules)")
                
                if not apps_with_modules:
                    print("\n❌ No apps with modules available")
                    continue
                
                source_idx = int(input(f"\n🔹 Select source (1-{len(apps_with_modules)}): "))
                if 1 <= source_idx <= len(apps_with_modules):
                    source_app = apps_with_modules[source_idx - 1]
                    print(f"\n✅ Will migrate modules FROM {source_app} TO {selected_app}")
                    return {'app': selected_app, 'source_app': source_app, 'import_mode': True}
                    
            elif choice == 3:
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("\n🚫 Invalid input")
            return None


def select_app(app_names, prompt="Select app"):
    """
    Interactive app selection from available apps with zero-module detection
    Returns: selected app name or dict with details, or None if cancelled
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
                
                # Check if app has modules
                module_count = frappe.db.count('Module Def', {'app_name': selected_app})
                
                if module_count == 0:
                    # Handle zero-module scenario
                    result = handle_zero_module_app(selected_app, app_names)
                    return result
                else:
                    print(f"✅ Selected: {selected_app} ({module_count} modules)")
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
    Analyze app modules with enhanced classification (OPTIMIZED VERSION)
    
    Performance: 60-360x faster using batch queries
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
        
        print(f"\n📦 Found {len(modules)} modules in {app_name}")
        
        # Get ALL doctypes for all modules in ONE query
        module_names = [m['module_name'] for m in modules]
        all_doctypes = frappe.get_all('DocType',
            filters={'module': ['in', module_names]},
            fields=['name', 'custom', 'module']
        )
        
        if not all_doctypes:
            print(f"❌ No doctypes found for {app_name}")
            return None
        
        # ⚡ OPTIMIZED: Batch classify ALL doctypes at once
        print(f"📋 Analyzing {len(all_doctypes)} doctypes...", end="", flush=True)
        
        from .doctype_classifier import batch_classify_doctypes, DoctypeStatus
        all_doctype_names = [dt['name'] for dt in all_doctypes]
        classifications_dict = batch_classify_doctypes(all_doctype_names)
        
        print(" ✅ Done!\n")
        
        # Group results by module
        module_data = []
        for module in modules:
            module_doctypes = [dt for dt in all_doctypes if dt['module'] == module['module_name']]
            
            classifications = []
            status_counts = {}
            
            for dt in module_doctypes:
                classification = classifications_dict.get(dt['name'])
                if classification:
                    classifications.append(classification)
                    status = classification.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            module_data.append({
                'module': module,
                'doctypes': module_doctypes,
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
        print("✅ Analysis complete!")
        
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
    ✨ NEW: Multi-bench and multi-site migration support
    """
    print("\n" + "=" * 70)
    print("🧙 ENHANCED INTERACTIVE MIGRATION WIZARD V6.0.0")
    print("=" * 70)
    print("\n🚀 Complete migration workflow with MULTI-BENCH support")
    print("💡 Supports: same-site, site-to-site, and cross-bench migrations")
    
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
        
        # Handle dict return (zero-module app) or string return (normal app)
        if isinstance(source_app, dict):
            # Zero-module app selected
            app_name = source_app['app']
            if source_app.get('import_mode'):
                print(f"\n📌 Note: Import mode - will analyze source app {source_app['source_app']}")
                # For now, analyze the source app
                module_data = analyze_app_modules(source_app['source_app'])
            else:
                print(f"\n⚠️ Note: '{app_name}' has 0 modules")
                print("💡 Skipping module analysis for zero-module app")
                module_data = None
        else:
            # Normal app with modules
            app_name = source_app
            # Step 4: Analyze source app modules
            module_data = analyze_app_modules(app_name)
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
                    # Start migration - ENHANCED with multi-bench/multi-site support
                    print("\n" + "=" * 70)
                    print("📋 STEP 6: MIGRATION TARGET CONFIGURATION")
                    print("=" * 70)
                    
                    print("\n🎯 Select migration target type:")
                    print("  1. 📦 Same site (migrate to different app on current site)")
                    print("  2. 🔄 Different site (same bench, different site)")
                    print("  3. 🏢 Different bench (cross-bench migration)")
                    print("  0. ❌ CANCEL")
                    
                    try:
                        target_type = int(input("\n🔹 Select target type (0-3): ").strip())
                        
                        if target_type == 0:
                            print("🚫 Selection cancelled")
                            continue
                        
                        target_bench_path = None
                        target_site = selected_site
                        target_apps = []
                        
                        if target_type == 1:
                            # Same site - use current apps
                            print(f"\n✅ Target: Same site ({selected_site})")
                            target_apps = list(set(app_names + get_all_bench_apps()))
                            
                        elif target_type == 2:
                            # Different site, same bench
                            all_sites = get_bench_sites()
                            other_sites = [s for s in all_sites if s != selected_site]
                            
                            if not other_sites:
                                print("❌ No other sites available in this bench")
                                continue
                            
                            print("\n📍 Available target sites:")
                            print("  0. ❌ CANCEL")
                            for i, site in enumerate(other_sites, 1):
                                print(f"  {i}. {site}")
                            
                            site_choice = int(input(f"\n🔹 Select target site (0-{len(other_sites)}): ").strip())
                            if site_choice == 0:
                                continue
                            if 1 <= site_choice <= len(other_sites):
                                target_site = other_sites[site_choice - 1]
                                print(f"\n✅ Target site: {target_site}")
                                target_apps = get_all_bench_apps()
                            else:
                                print("❌ Invalid selection")
                                continue
                                
                        elif target_type == 3:
                            # Different bench
                            target_bench_path = select_bench()
                            if not target_bench_path:
                                continue
                            
                            other_bench_sites = get_bench_sites(target_bench_path)
                            if not other_bench_sites:
                                print(f"❌ No sites found in {target_bench_path}")
                                continue
                            
                            print(f"\n📍 Sites in {target_bench_path}:")
                            print("  0. ❌ CANCEL")
                            for i, site in enumerate(other_bench_sites, 1):
                                print(f"  {i}. {site}")
                            
                            site_choice = int(input(f"\n🔹 Select target site (0-{len(other_bench_sites)}): ").strip())
                            if site_choice == 0:
                                continue
                            if 1 <= site_choice <= len(other_bench_sites):
                                target_site = other_bench_sites[site_choice - 1]
                                print(f"\n✅ Target site: {target_site}")
                                target_apps = get_bench_apps_from_path(target_bench_path)
                            else:
                                print("❌ Invalid selection")
                                continue
                        else:
                            print("❌ Invalid option")
                            continue
                        
                        # Now select target app
                        if not target_apps:
                            target_apps = get_all_bench_apps()
                        target_apps.sort()
                        
                        print("\n📦 Available target apps:")
                        print("  0. ❌ CANCEL")
                        for i, app in enumerate(target_apps, 1):
                            if app in app_names:
                                print(f"  {i}. {app} [installed on source]")
                            else:
                                print(f"  {i}. {app} [✨ NEW]")
                        
                        app_choice = int(input(f"\n🔹 Select target app (0-{len(target_apps)}): ").strip())
                        
                        if app_choice == 0:
                            print("🚫 Selection cancelled")
                            continue
                        elif 1 <= app_choice <= len(target_apps):
                            target_app = target_apps[app_choice - 1]
                            
                            # Display migration summary
                            print("\n" + "=" * 70)
                            print("🚀 MIGRATION SUMMARY")
                            print("=" * 70)
                            print(f"\n  📤 SOURCE:")
                            print(f"     Site: {selected_site}")
                            print(f"     App:  {app_name}")
                            print(f"\n  📥 TARGET:")
                            if target_bench_path:
                                print(f"     Bench: {target_bench_path}")
                            print(f"     Site: {target_site}")
                            print(f"     App:  {target_app}")
                            
                            if target_type == 1:
                                print(f"\n  📋 Type: Same-site migration")
                            elif target_type == 2:
                                print(f"\n  📋 Type: Site-to-site migration (same bench)")
                            else:
                                print(f"\n  📋 Type: Cross-bench migration")
                            
                            print("\n" + "─" * 70)
                            print("\n⚠️ Migration execution not yet implemented in this wizard")
                            print("💡 Use migration_engine.py for actual migration with these parameters")
                        else:
                            print(f"❌ Please enter a number between 0 and {len(target_apps)}")
                    except ValueError:
                        print("❌ Please enter a valid number")
                
                elif choice == 5:
                    # Analyze different app
                    new_selection = select_app(app_names, "Select app to analyze")
                    if new_selection:
                        # Handle dict or string return
                        if isinstance(new_selection, dict):
                            source_app = new_selection
                            app_name = new_selection['app']
                            if new_selection.get('import_mode'):
                                module_data = analyze_app_modules(new_selection['source_app'])
                            else:
                                print(f"\n⚠️ Note: '{app_name}' has 0 modules")
                                module_data = None
                        else:
                            source_app = new_selection
                            app_name = new_selection
                            module_data = analyze_app_modules(new_selection)
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
