"""
Analysis Tools Module - V5.0.0
Enhanced V4 analysis tools with V2's comprehensive analysis capabilities

Features:
- Bench health analysis
- App dependency analysis
- Comprehensive diagnostics
- Cross-app reference detection
- Orphan detection
- File system validation
"""

import frappe
from frappe.utils import get_sites
import os
import subprocess
import json
from pathlib import Path
from .session_manager import ensure_frappe_connection, with_session_management


# ========== V4 BENCH ANALYSIS TOOLS ==========

def analyze_bench_health(bench_path):
    """Analyze bench health and performance"""
    print(f"🔍 ANALYZING BENCH HEALTH: {bench_path}")
    print("=" * 70)
    
    checks = {
        "Directory exists": os.path.exists(bench_path),
        "Bench structure": os.path.exists(f"{bench_path}/apps"),
        "Sites directory": os.path.exists(f"{bench_path}/sites"),
        "Config exists": os.path.exists(f"{bench_path}/sites/common_site_config.json")
    }
    
    print("\n✔️  Health Checks:")
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    # Additional checks
    if os.path.exists(bench_path):
        size = get_directory_size(bench_path)
        print(f"\n📊 Bench Size: {size}")
        
        # Count apps
        if os.path.exists(f"{bench_path}/apps"):
            apps = [d for d in os.listdir(f"{bench_path}/apps") 
                   if os.path.isdir(f"{bench_path}/apps/{d}")]
            print(f"📦 Apps Installed: {len(apps)}")
    
    print("=" * 70)
    return all(checks.values())


def get_directory_size(path):
    """Get human-readable directory size"""
    try:
        result = subprocess.run(
            f"du -sh {path}",
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip().split()[0]
    except:
        return "unknown"


def analyze_app_dependencies(app_name, bench_path=None):
    """
    Analyze app dependencies and requirements
    V4-style file-based dependency analysis
    """
    print(f"🔍 ANALYZING DEPENDENCIES: {app_name}")
    print("=" * 70)
    
    if not bench_path:
        bench_path = "/home/frappe/frappe-bench"
    
    app_path = f"{bench_path}/apps/{app_name}"
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_name}")
        return None
    
    # Check for requirements.txt
    requirements_file = f"{app_path}/requirements.txt"
    if os.path.exists(requirements_file):
        print("\n📦 Python Dependencies:")
        try:
            with open(requirements_file, 'r') as f:
                dependencies = [line.strip() for line in f 
                               if line.strip() and not line.startswith('#')]
                for dep in dependencies[:10]:
                    print(f"  • {dep}")
                if len(dependencies) > 10:
                    print(f"  ... and {len(dependencies) - 10} more")
        except:
            print("  💡 Could not read requirements")
    else:
        print("\n  No requirements.txt found")
    
    # Check for package.json
    package_file = f"{app_path}/package.json"
    if os.path.exists(package_file):
        print("\n📦 Node.js dependencies found (package.json)")
        try:
            with open(package_file, 'r') as f:
                package_data = json.load(f)
                if 'dependencies' in package_data:
                    deps = package_data['dependencies']
                    print(f"  Found {len(deps)} dependencies")
        except:
            pass
    
    print("=" * 70)
    return True


# ========== V2 COMPREHENSIVE ANALYSIS ==========

@with_session_management
def analyze_app_comprehensive(source_app):
    """
    COMPREHENSIVE DEPENDENCY ANALYSIS FOR MIGRATION WITH ENHANCED DIAGNOSTICS
    V2-style comprehensive analysis
    """
    print(f"🔍 COMPREHENSIVE ANALYSIS: {source_app}")
    print("=" * 70)
    
    try:
        # Get modules
        modules = frappe.get_all('Module Def',
            filters={'app_name': source_app},
            fields=['name', 'module_name', 'app_name']
        )
        
        print(f"\n📦 MODULES IN {source_app}: {len(modules)}\n")
        
        all_app_doctypes = []
        
        for module in modules:
            print(f"  • {module['module_name']}")
            doctypes = frappe.get_all('DocType',
                filters={'module': module['module_name']},
                fields=['name', 'custom', 'is_submittable', 'issingle', 'app']
            )
            
            for doctype in doctypes:
                all_app_doctypes.append(doctype)
                custom_flag = " (CUSTOM)" if doctype['custom'] else ""
                submittable_flag = " 📋" if doctype.get('is_submittable') else ""
                single_flag = " ⚙️" if doctype.get('issingle') else ""
                app_flag = " ❌ APP=NONE" if not doctype.get('app') else ""
                print(f"      └─ {doctype['name']}{custom_flag}{submittable_flag}{single_flag}{app_flag}")
        
        # Orphan Detection
        print(f"\n🔍 ORPHAN DETECTION")
        print("=" * 70)
        orphans = []
        for dt in all_app_doctypes:
            if not dt.get('module'):
                orphans.append(f"{dt['name']} - NO MODULE")
            else:
                module_check = frappe.get_all('Module Def', 
                    filters={'module_name': dt['module'], 'app_name': source_app}
                )
                if not module_check:
                    orphans.append(f"{dt['name']} - WRONG MODULE: {dt['module']}")
        
        if orphans:
            print("⚠️  ORPHAN DOCTYPES FOUND:")
            for orphan in orphans[:10]:
                print(f"  • {orphan}")
            if len(orphans) > 10:
                print(f"  ... and {len(orphans) - 10} more")
        else:
            print("✅ No orphan doctypes found")
        
        # App=None Detection
        print(f"\n🔍 APP=NONE DETECTION")
        print("=" * 70)
        app_none_doctypes = frappe.get_all('DocType', 
            filters={'app': ['is', 'not set']}, 
            fields=['name', 'module']
        )
        
        if app_none_doctypes:
            print(f"⚠️  DOCTYPES WITH APP=NONE: {len(app_none_doctypes)}")
            for dt in app_none_doctypes[:10]:
                print(f"  • {dt['name']} (module: {dt.get('module', 'N/A')})")
            if len(app_none_doctypes) > 10:
                print(f"  ... and {len(app_none_doctypes) - 10} more")
        else:
            print("✅ No doctypes with app=None")
        
        # File System Check
        print(f"\n🔍 FILE SYSTEM CHECK")
        print("=" * 70)
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / source_app / source_app
        
        missing_files = []
        missing_db = []
        
        if app_path.exists():
            # Check for doctypes in DB missing from files
            for dt in all_app_doctypes:
                if dt.get('module'):
                    expected_path = app_path / dt['module'] / f"{dt['name']}.json"
                    snake_name = frappe.scrub(dt['name'])
                    snake_path = app_path / dt['module'] / f"{snake_name}.json"
                    
                    if not expected_path.exists() and not snake_path.exists():
                        missing_files.append(f"{dt['name']} (in DB, no file)")
            
            # Check for files in filesystem missing from DB
            for module_dir in app_path.iterdir():
                if module_dir.is_dir():
                    for doctype_file in module_dir.glob('**/*.json'):
                        if doctype_file.stem != '__init__':
                            if not frappe.db.exists('DocType', doctype_file.stem):
                                missing_db.append(f"{doctype_file.stem} (file exists, not in DB)")
        else:
            print(f"⚠️  App path not found: {app_path}")
        
        if missing_files:
            print("⚠️  DOCTYPES IN DB BUT MISSING FILES:")
            for item in missing_files[:10]:
                print(f"  • {item}")
            if len(missing_files) > 10:
                print(f"  ... and {len(missing_files) - 10} more")
        else:
            print("✅ All DB doctypes have corresponding files")
            
        if missing_db:
            print("\n⚠️  DOCTYPE FILES WITH NO DB RECORDS:")
            for item in missing_db[:10]:
                print(f"  • {item}")
            if len(missing_db) > 10:
                print(f"  ... and {len(missing_db) - 10} more")
        else:
            print("✅ All doctype files have DB records")
        
        # Dependency Analysis
        print(f"\n🔍 CROSS-APP DEPENDENCIES")
        print("=" * 70)
        
        all_doctypes = frappe.get_all('DocType', fields=['name', 'app'])
        dependency_count = 0
        cross_app_dependencies = []
        source_doctypes = [dt['name'] for dt in all_app_doctypes]
        
        for target_dt in all_doctypes:
            if target_dt.get('app') != source_app:
                try:
                    doc = frappe.get_doc('DocType', target_dt['name'])
                    doc_json = doc.as_json()
                    references = [source_dt for source_dt in source_doctypes if source_dt in doc_json]
                    if references:
                        cross_app_dependencies.append({
                            'doctype': target_dt['name'],
                            'app': target_dt.get('app', 'Unknown'),
                            'references': references
                        })
                        dependency_count += 1
                except Exception:
                    pass
        
        if cross_app_dependencies:
            print(f"⚠️  CROSS-APP DEPENDENCIES: {len(cross_app_dependencies)}")
            for dep in cross_app_dependencies[:5]:
                print(f"  • {dep['doctype']} ({dep['app']}) references: {', '.join(dep['references'][:3])}")
            if len(cross_app_dependencies) > 5:
                print(f"  ... and {len(cross_app_dependencies) - 5} more")
        else:
            print("✅ No cross-app dependencies found")
        
        # Comprehensive Summary
        print(f"\n📊 COMPREHENSIVE SUMMARY")
        print("=" * 70)
        print(f"  • Modules: {len(modules)}")
        print(f"  • Doctypes: {len(all_app_doctypes)}")
        print(f"  • Orphan Doctypes: {len(orphans)}")
        print(f"  • App=None Doctypes: {len(app_none_doctypes)}")
        print(f"  • Missing Files: {len(missing_files)}")
        print(f"  • Missing DB Records: {len(missing_db)}")
        print(f"  • Cross-App Dependencies: {dependency_count}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("=" * 70)
        recommendations = []
        if orphans:
            recommendations.append("Fix orphans: bench migrate-app fix-orphans " + source_app)
        if app_none_doctypes:
            recommendations.append("Fix app=None: bench migrate-app fix-app-none " + source_app)
        if missing_files:
            recommendations.append("Restore missing: bench migrate-app restore-missing " + source_app)
        if cross_app_dependencies:
            recommendations.append("Analyze references: bench migrate-app fix-all-references " + source_app)
        
        if recommendations:
            for rec in recommendations:
                print(f"  • {rec}")
        else:
            print("  ✅ App is ready for migration!")
        
        print("=" * 70)
        
        return {
            'modules': len(modules),
            'doctypes': len(all_app_doctypes),
            'orphans': len(orphans),
            'app_none': len(app_none_doctypes),
            'missing_files': len(missing_files),
            'missing_db': len(missing_db),
            'dependencies': dependency_count
        }
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_available_benches():
    """Detect all available benches in frappe home directory"""
    benches = []
    frappe_home = os.path.expanduser('~')
    
    for item in os.listdir(frappe_home):
        item_path = os.path.join(frappe_home, item)
        if os.path.isdir(item_path):
            # Check if it's a bench (has apps directory)
            if os.path.exists(os.path.join(item_path, 'apps')) and \
               os.path.exists(os.path.join(item_path, 'sites')):
                benches.append(item)
    
    return sorted(benches)


def get_bench_apps(bench_path):
    """Get installed apps from a bench"""
    try:
        result = subprocess.run(
            f"cd {bench_path} && bench version",
            shell=True, capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n')
        apps = []
        for line in lines:
            if ' ' in line and not line.startswith('✅'):
                parts = line.split()
                if parts:
                    app = parts[0]
                    apps.append(app)
        return sorted(apps)
    except Exception as e:
        print(f"  ❌ Error getting apps: {e}")
        return []


def multi_bench_analysis():
    """Analyze multi-bench ecosystem"""
    print("🔍 MULTI-BENCH ECOSYSTEM ANALYSIS")
    print("=" * 70)
    
    benches = detect_available_benches()
    print(f"\n📋 Found {len(benches)} benches:\n")
    
    for bench in benches:
        bench_path = os.path.join(os.path.expanduser('~'), bench)
        apps = get_bench_apps(bench_path)
        size = get_directory_size(bench_path)
        
        print(f"📦 {bench}")
        print(f"  Size: {size}")
        print(f"  Apps ({len(apps)}): {', '.join(apps[:5])}")
        if len(apps) > 5:
            print(f"    ... and {len(apps) - 5} more")
        print()
    
    print("=" * 70)
    return benches


if __name__ == "__main__":
    # Test analysis tools
    import sys
    if len(sys.argv) > 1:
        app_name = sys.argv[1]
        analyze_app_comprehensive(app_name)
    else:
        multi_bench_analysis()
