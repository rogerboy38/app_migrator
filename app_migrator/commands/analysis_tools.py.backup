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
- Enhanced security analysis
- Performance metrics
- Data volume analysis
- Migration reporting
"""

import frappe
from frappe.utils import get_sites
import os
import subprocess
import json
from pathlib import Path
from .session_manager import ensure_frappe_connection, with_session_management
import time
from datetime import datetime
import pandas as pd


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
def analyze_app_comprehensive(source_app, detailed=False):
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


def multi_bench_analysis(bench_path=None):
    """Analyze multi-bench ecosystem"""
    print("🔍 MULTI-BENCH ECOSYSTEM ANALYSIS")
    print("=" * 70)
    
    benches = detect_available_benches()
    print(f"\n📋 Found {len(benches)} benches:\n")
    
    for bench in benches:
        current_bench_path = os.path.join(os.path.expanduser('~'), bench)
        apps = get_bench_apps(current_bench_path)
        size = get_directory_size(current_bench_path)
        
        print(f"📦 {bench}")
        print(f"  Size: {size}")
        print(f"  Apps ({len(apps)}): {', '.join(apps[:5])}")
        if len(apps) > 5:
            print(f"    ... and {len(apps) - 5} more")
        print()
    
    print("=" * 70)
    return benches


# ========== ENHANCED ANALYSIS FUNCTIONS ==========


@with_session_management
def analyze_app_security(app_name, output_format='text'):
    """
    Enhanced security analysis for app migration - FIXED VERSION
    """
    print(f"🔒 SECURITY ANALYSIS: {app_name}")
    print("=" * 70)
    
    security_issues = []
    warnings = []
    recommendations = []
    
    try:
        # Analyze DocType permissions using proper column names
        doctypes = frappe.get_all('DocType', 
            filters={'app': app_name},
            fields=['name', 'is_submittable', 'track_changes']
        )
        
        print(f"📋 SECURITY ANALYSIS FOR {len(doctypes)} DOCTYPES")
        print("-" * 40)
        
        # Analyze permissions using DocPerm instead of permissions field
        if doctypes:
            doctype_names = [d['name'] for d in doctypes]
            permissions = frappe.get_all('DocPerm',
                filters={'parent': ['in', doctype_names]},
                fields=['parent', 'role', 'permlevel', 'read', 'write', 'create', 'delete', 'submit', 'cancel', 'report']
            )
            
            print(f"✅ Permission rules analyzed: {len(permissions)}")
            
            # Check for doctypes with no permissions
            doctypes_with_perms = set([p['parent'] for p in permissions])
            for doctype in doctypes:
                if doctype['name'] not in doctypes_with_perms:
                    security_issues.append(f"Doctype '{doctype['name']}' has no permission rules")
        
        # Analyze custom scripts
        print(f"\n🔧 CUSTOM SCRIPTS ANALYSIS")
        print("-" * 40)
        custom_scripts = frappe.get_all('Client Script',
            filters={'app': app_name},
            fields=['name', 'dt', 'script_type']
        )
        
        print(f"Found {len(custom_scripts)} custom scripts")
        for script in custom_scripts[:5]:
            print(f"  • {script['name']} ({script['script_type']} for {script['dt']})")
        
        # Analyze server scripts
        server_scripts = frappe.get_all('Server Script',
            filters={'app': app_name},
            fields=['name', 'doctype_event', 'script_type']
        )
        
        print(f"\nFound {len(server_scripts)} server scripts")
        for script in server_scripts[:5]:
            print(f"  • {script['name']} ({script['script_type']} - {script['doctype_event']})")
        
        # Security recommendations
        print(f"\n💡 SECURITY RECOMMENDATIONS")
        print("-" * 40)
        
        if security_issues:
            print("⚠️  CRITICAL ISSUES:")
            for issue in security_issues[:5]:
                print(f"  • {issue}")
        
        if warnings:
            print("\n⚠️  WARNINGS:")
            for warning in warnings[:5]:
                print(f"  • {warning}")
        
        if not security_issues and not warnings:
            print("✅ No major security issues found")
        
        recommendations.extend([
            "Review all DocPerm permissions before migration",
            "Test custom scripts in staging environment",
            "Validate server script permissions",
            "Check for hardcoded credentials in scripts",
            "Verify API endpoint security"
        ])
        
        print(f"\n📝 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"  • {rec}")
        
        # Generate report if JSON output requested
        if output_format == 'json':
            report = {
                'app': app_name,
                'timestamp': datetime.now().isoformat(),
                'security_issues': security_issues,
                'warnings': warnings,
                'recommendations': recommendations,
                'doctypes_analyzed': len(doctypes),
                'custom_scripts': len(custom_scripts),
                'server_scripts': len(server_scripts),
                'permissions_analyzed': len(permissions) if doctypes else 0
            }
            return report
        
        print("=" * 70)
        return {
            'security_issues': len(security_issues),
            'warnings': len(warnings),
            'doctypes_analyzed': len(doctypes),
            'permissions_analyzed': len(permissions) if doctypes else 0
        }
        
    except Exception as e:
        print(f"❌ Security analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

@with_session_management
def analyze_performance_metrics(app_name, output_format='text'):
    """
    Enhanced performance metrics analysis for app migration
    """
    print(f"⚡ PERFORMANCE ANALYSIS: {app_name}")
    print("=" * 70)
    
    try:
        performance_data = {}
        
        # Analyze doctype sizes and record counts
        print(f"\n📊 DOCTYPE SIZE ANALYSIS")
        print("-" * 40)
        
        # Get all doctypes for the app
        doctypes = frappe.get_all('DocType', 
            filters={'app': app_name},
            fields=['name', 'issingle', 'is_submittable', 'track_changes', 'search_fields']
        )
        
        large_doctypes = []
        medium_doctypes = []
        total_records = 0
        doctype_details = []
        
        print(f"Analyzing {len(doctypes)} doctypes...")
        
        for doctype in doctypes:
            if not doctype.get('issingle'):
                try:
                    # Get record count
                    count = frappe.db.count(doctype['name'])
                    total_records += count
                    
                    # Get approximate table size
                    table_size = 0
                    try:
                        # Try to get table size from information_schema
                        if frappe.db.db_type == "mariadb":
                            size_result = frappe.db.sql(f"""
                                SELECT ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
                                FROM information_schema.TABLES 
                                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tab{doctype['name']}'
                            """)
                            if size_result:
                                table_size = size_result[0][0] or 0
                    except:
                        pass
                    
                    doctype_info = {
                        'doctype': doctype['name'],
                        'record_count': count,
                        'table_size_mb': table_size,
                        'is_submittable': doctype.get('is_submittable', False),
                        'track_changes': doctype.get('track_changes', False),
                        'has_search_fields': bool(doctype.get('search_fields')),
                        'size_category': 'SMALL'
                    }
                    
                    # Categorize by size
                    if count > 50000:
                        doctype_info['size_category'] = 'LARGE'
                        large_doctypes.append(doctype_info)
                    elif count > 10000:
                        doctype_info['size_category'] = 'MEDIUM'
                        medium_doctypes.append(doctype_info)
                    
                    doctype_details.append(doctype_info)
                    
                except Exception as e:
                    # Skip doctypes that can't be counted (might be virtual tables)
                    doctype_details.append({
                        'doctype': doctype['name'],
                        'record_count': 0,
                        'table_size_mb': 0,
                        'error': str(e)
                    })
        
        # Sort by record count
        doctype_details.sort(key=lambda x: x.get('record_count', 0), reverse=True)
        large_doctypes.sort(key=lambda x: x.get('record_count', 0), reverse=True)
        medium_doctypes.sort(key=lambda x: x.get('record_count', 0), reverse=True)
        
        # Display summary
        print(f"Total records across all doctypes: {total_records:,}")
        print(f"Large doctypes (>50K records): {len(large_doctypes)}")
        print(f"Medium doctypes (>10K records): {len(medium_doctypes)}")
        print(f"Small doctypes: {len(doctype_details) - len(large_doctypes) - len(medium_doctypes)}")
        
        # Show top 10 largest doctypes
        if large_doctypes or medium_doctypes:
            print(f"\n📈 LARGEST DOCTYPES:")
            for i, data in enumerate(doctype_details[:10]):
                if data.get('error'):
                    print(f"  {i+1}. {data['doctype']}: ERROR - {data['error']}")
                else:
                    flags = []
                    if data.get('is_submittable'):
                        flags.append("📋")
                    if data.get('track_changes'):
                        flags.append("📝")
                    if data.get('has_search_fields'):
                        flags.append("🔍")
                    
                    flag_str = " " + " ".join(flags) if flags else ""
                    size_info = f" ({data['table_size_mb']} MB)" if data['table_size_mb'] > 0 else ""
                    print(f"  {i+1}. {data['doctype']}: {data['record_count']:,} records{size_info} [{data['size_category']}]{flag_str}")
        
        # Analyze custom fields impact
        print(f"\n🔧 CUSTOM FIELDS & PROPERTY SETTERS ANALYSIS")
        print("-" * 40)
        
        # Get custom fields (without app filter since column might not exist)
        custom_fields = frappe.get_all('Custom Field',
            fields=['dt', 'fieldname', 'fieldtype']
        )
        
        # Filter custom fields for this app's doctypes
        app_doctype_names = [d['name'] for d in doctypes]
        app_custom_fields = [cf for cf in custom_fields if cf['dt'] in app_doctype_names]
        
        print(f"Custom fields in app: {len(app_custom_fields)}")
        
        # Group by doctype
        doctype_field_count = {}
        for cf in app_custom_fields:
            doctype = cf['dt']
            doctype_field_count[doctype] = doctype_field_count.get(doctype, 0) + 1
        
        # Analyze property setters
        property_setters = frappe.get_all('Property Setter',
            fields=['doc_type', 'property', 'property_type']
        )
        app_property_setters = [ps for ps in property_setters if ps['doc_type'] in app_doctype_names]
        
        print(f"Property setters in app: {len(app_property_setters)}")
        
        # Identify doctypes with many customizations
        high_field_doctypes = {dt: count for dt, count in doctype_field_count.items() if count > 15}
        high_setter_doctypes = {}
        
        for ps in app_property_setters:
            doctype = ps['doc_type']
            high_setter_doctypes[doctype] = high_setter_doctypes.get(doctype, 0) + 1
        
        high_setter_doctypes = {dt: count for dt, count in high_setter_doctypes.items() if count > 10}
        
        if high_field_doctypes:
            print(f"\n⚠️  DOCTYPES WITH MANY CUSTOM FIELDS (>15):")
            for dt, count in sorted(high_field_doctypes.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {dt}: {count} custom fields")
        
        if high_setter_doctypes:
            print(f"\n⚠️  DOCTYPES WITH MANY PROPERTY SETTERS (>10):")
            for dt, count in sorted(high_setter_doctypes.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {dt}: {count} property setters")
        
        # Analyze indexes and search optimization
        print(f"\n🔍 SEARCH & INDEXING ANALYSIS")
        print("-" * 40)
        
        doctypes_with_indexes = 0
        doctypes_with_search_fields = 0
        
        for doctype in doctypes:
            if doctype.get('search_fields'):
                doctypes_with_search_fields += 1
            # Check if doctype has custom indexes
            try:
                indexes = frappe.db.sql(f"SHOW INDEX FROM `tab{doctype['name']}`")
                if len(indexes) > 1:  # More than just primary key
                    doctypes_with_indexes += 1
            except:
                pass
        
        print(f"Doctypes with search fields: {doctypes_with_search_fields}/{len(doctypes)}")
        print(f"Doctypes with additional indexes: {doctypes_with_indexes}/{len(doctypes)}")
        
        # Performance impact assessment
        print(f"\n📈 PERFORMANCE IMPACT ASSESSMENT")
        print("-" * 40)
        
        total_table_size = sum(d.get('table_size_mb', 0) for d in doctype_details)
        
        print(f"Estimated total data size: {total_table_size:.2f} MB")
        print(f"Large tables requiring optimization: {len(large_doctypes)}")
        print(f"Highly customized doctypes: {len(high_field_doctypes) + len(high_setter_doctypes)}")
        
        # Performance recommendations
        print(f"\n💡 PERFORMANCE RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = []
        
        if large_doctypes:
            recommendations.append("Implement archiving strategy for large doctypes")
            recommendations.append("Add database indexes for frequently queried large tables")
            recommendations.append("Consider read replicas for high-traffic large tables")
        
        if medium_doctypes:
            recommendations.append("Monitor growth of medium-sized doctypes")
            recommendations.append("Implement pagination for list views of medium tables")
        
        if high_field_doctypes:
            recommendations.append("Optimize doctypes with excessive custom fields")
            recommendations.append("Consider splitting highly customized doctypes")
        
        if total_table_size > 1000:  # More than 1GB
            recommendations.append("Plan for extended migration window due to large data volume")
            recommendations.append("Test migration performance with production data snapshot")
        
        if not recommendations:
            recommendations.append("App has good performance characteristics for migration")
            recommendations.append("Standard migration procedures should be sufficient")
        
        # Add general recommendations
        recommendations.extend([
            "Test with production data volume in staging",
            "Monitor database performance during migration",
            "Consider maintenance window for large migrations"
        ])
        
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        # Risk assessment
        print(f"\n⚠️  PERFORMANCE RISK ASSESSMENT")
        print("-" * 40)
        
        risk_score = 0
        if large_doctypes:
            risk_score += 2
        if total_table_size > 1000:
            risk_score += 2
        if high_field_doctypes:
            risk_score += 1
        
        risk_levels = {
            0: "LOW - Standard migration safe",
            1: "LOW - Minor optimizations recommended", 
            2: "MEDIUM - Plan optimizations needed",
            3: "HIGH - Significant optimization required",
            4: "CRITICAL - Major performance risks"
        }
        
        risk_level = risk_levels.get(risk_score, "UNKNOWN")
        print(f"Performance Risk Level: {risk_level} (Score: {risk_score}/4)")
        
        # Generate comprehensive report if JSON output requested
        if output_format == 'json':
            report = {
                'app': app_name,
                'timestamp': datetime.now().isoformat(),
                'total_records': total_records,
                'total_table_size_mb': round(total_table_size, 2),
                'doctype_count': len(doctypes),
                'large_doctypes': len(large_doctypes),
                'medium_doctypes': len(medium_doctypes),
                'custom_fields_count': len(app_custom_fields),
                'property_setters_count': len(app_property_setters),
                'doctypes_with_search_fields': doctypes_with_search_fields,
                'doctypes_with_indexes': doctypes_with_indexes,
                'high_field_doctypes': high_field_doctypes,
                'high_setter_doctypes': high_setter_doctypes,
                'doctype_details': doctype_details[:20],  # Limit details in JSON
                'recommendations': recommendations,
                'risk_score': risk_score,
                'risk_level': risk_level
            }
            return report
        
        print("=" * 70)
        return {
            'total_records': total_records,
            'total_table_size_mb': round(total_table_size, 2),
            'large_doctypes': len(large_doctypes),
            'medium_doctypes': len(medium_doctypes),
            'custom_fields': len(app_custom_fields),
            'property_setters': len(app_property_setters),
            'risk_score': risk_score
        }
        
    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


@with_session_management
def analyze_data_volume(app_name, output_format='text'):
    """
    Analyze data volume and growth patterns
    """
    print(f"📈 DATA VOLUME ANALYSIS: {app_name}")
    print("=" * 70)
    
    try:
        # Get all doctypes for the app
        doctypes = frappe.get_all('DocType', 
            filters={'app': app_name},
            fields=['name', 'issingle', 'is_submittable', 'creation']
        )
        
        volume_data = []
        total_size_estimate = 0
        
        print(f"\n📊 DATA VOLUME BY DOCTYPE")
        print("-" * 40)
        
        for doctype in doctypes:
            if not doctype.get('issingle'):
                try:
                    count = frappe.db.count(doctype['name'])
                    # Rough size estimate (assuming 2KB per record)
                    size_estimate = count * 2  # in KB
                    total_size_estimate += size_estimate
                    
                    volume_data.append({
                        'doctype': doctype['name'],
                        'record_count': count,
                        'size_estimate_kb': size_estimate,
                        'size_estimate_mb': round(size_estimate / 1024, 2),
                        'is_submittable': doctype.get('is_submittable', False)
                    })
                except Exception as e:
                    volume_data.append({
                        'doctype': doctype['name'],
                        'record_count': 0,
                        'size_estimate_kb': 0,
                        'error': str(e)
                    })
        
        # Sort by size
        volume_data.sort(key=lambda x: x['record_count'], reverse=True)
        
        # Display top 10 largest doctypes
        for i, data in enumerate(volume_data[:10]):
            if data.get('error'):
                print(f"  {i+1}. {data['doctype']}: ERROR - {data['error']}")
            else:
                submittable_flag = " 📋" if data['is_submittable'] else ""
                print(f"  {i+1}. {data['doctype']}: {data['record_count']:,} records ({data['size_estimate_mb']} MB){submittable_flag}")
        
        total_mb = total_size_estimate / 1024
        total_gb = total_mb / 1024
        
        print(f"\n📈 TOTAL DATA VOLUME ESTIMATE")
        print("-" * 40)
        print(f"Total Records: {sum(d['record_count'] for d in volume_data):,}")
        print(f"Estimated Size: {total_mb:.2f} MB ({total_gb:.2f} GB)")
        print(f"Doctypes Analyzed: {len(volume_data)}")
        
        # Growth analysis (recent records)
        print(f"\n📅 RECENT ACTIVITY ANALYSIS")
        print("-" * 40)
        
        recent_doctypes = []
        for doctype in volume_data[:5]:  # Top 5 by size
            if doctype['record_count'] > 0:
                try:
                    # Check records created in last 30 days
                    recent_count = frappe.db.sql(f"""
                        SELECT COUNT(*) 
                        FROM `tab{doctype['doctype']}` 
                        WHERE creation >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    """)[0][0]
                    
                    if recent_count > 0:
                        growth_rate = (recent_count / doctype['record_count']) * 100
                        recent_doctypes.append({
                            'doctype': doctype['doctype'],
                            'recent_records': recent_count,
                            'growth_rate': round(growth_rate, 2)
                        })
                except:
                    pass
        
        if recent_doctypes:
            print("Doctypes with recent activity (last 30 days):")
            for dt in recent_doctypes:
                print(f"  • {dt['doctype']}: {dt['recent_records']} records ({dt['growth_rate']}% of total)")
        else:
            print("No recent activity detected in top doctypes")
        
        # Migration impact assessment
        print(f"\n⚠️  MIGRATION IMPACT ASSESSMENT")
        print("-" * 40)
        
        recommendations = []
        
        if total_gb > 1:
            recommendations.append("Large data volume - plan for extended migration window")
            recommendations.append("Consider partial migration or data archiving")
            recommendations.append("Test migration with production data snapshot")
        
        large_doctypes = [d for d in volume_data if d['record_count'] > 50000]
        if large_doctypes:
            recommendations.append(f"Large doctypes detected: {len(large_doctypes)} - optimize migration order")
        
        if not recommendations:
            recommendations.append("Data volume is manageable for standard migration")
        
        for rec in recommendations:
            print(f"  • {rec}")
        
        # Generate report if JSON output requested
        if output_format == 'json':
            report = {
                'app': app_name,
                'timestamp': datetime.now().isoformat(),
                'total_records': sum(d['record_count'] for d in volume_data),
                'total_size_mb': round(total_mb, 2),
                'total_size_gb': round(total_gb, 2),
                'volume_data': volume_data,
                'recent_activity': recent_doctypes,
                'recommendations': recommendations
            }
            return report
        
        print("=" * 70)
        return {
            'total_records': sum(d['record_count'] for d in volume_data),
            'total_size_gb': round(total_gb, 2),
            'large_doctypes': len(large_doctypes)
        }
        
    except Exception as e:
        print(f"❌ Data volume analysis failed: {e}")
        return None


@with_session_management
def generate_migration_report(app_name, output_format='text'):
    """
    Generate comprehensive migration readiness report
    """
    print(f"📋 MIGRATION READINESS REPORT: {app_name}")
    print("=" * 70)
    
    try:
        report_data = {
            'app': app_name,
            'timestamp': datetime.now().isoformat(),
            'comprehensive_analysis': analyze_app_comprehensive(app_name),
            'security_analysis': analyze_app_security(app_name, 'json'),
            'performance_analysis': analyze_performance_metrics(app_name, 'json'),
            'data_volume_analysis': analyze_data_volume(app_name, 'json')
        }
        
        # Overall readiness score
        readiness_score = 0
        total_checks = 0
        
        # Calculate readiness based on various factors
        if report_data['comprehensive_analysis']:
            comp = report_data['comprehensive_analysis']
            if comp['orphans'] == 0:
                readiness_score += 25
            if comp['app_none'] == 0:
                readiness_score += 25
            if comp['missing_files'] == 0:
                readiness_score += 25
            if comp['missing_db'] == 0:
                readiness_score += 25
            total_checks += 4
        
        if report_data['security_analysis']:
            sec = report_data['security_analysis']
            if sec['security_issues'] == 0:
                readiness_score += 25
            total_checks += 1
        
        readiness_percentage = (readiness_score / (total_checks * 25)) * 100 if total_checks > 0 else 0
        
        report_data['readiness_score'] = round(readiness_percentage, 2)
        
        # Generate summary
        print(f"\n🎯 MIGRATION READINESS SCORE: {readiness_percentage:.1f}%")
        print("-" * 40)
        
        if readiness_percentage >= 80:
            print("✅ EXCELLENT - App is ready for migration")
        elif readiness_percentage >= 60:
            print("⚠️  GOOD - Some minor issues to address")
        elif readiness_percentage >= 40:
            print("⚠️  FAIR - Several issues need attention")
        else:
            print("❌ POOR - Significant work required before migration")
        
        # Next steps
        print(f"\n📝 RECOMMENDED NEXT STEPS")
        print("-" * 40)
        
        next_steps = []
        comp = report_data.get('comprehensive_analysis', {})
        
        if comp.get('orphans', 0) > 0:
            next_steps.append(f"Fix {comp['orphans']} orphan doctypes")
        if comp.get('app_none', 0) > 0:
            next_steps.append(f"Fix {comp['app_none']} doctypes with app=None")
        if comp.get('missing_files', 0) > 0:
            next_steps.append(f"Restore {comp['missing_files']} missing files")
        
        sec = report_data.get('security_analysis', {})
        if sec.get('security_issues', 0) > 0:
            next_steps.append(f"Address {sec['security_issues']} security issues")
        
        if not next_steps:
            next_steps.append("Proceed with migration - all checks passed")
        
        for step in next_steps:
            print(f"  • {step}")
        
        # Export if requested
        if output_format == 'json':
            import json
            filename = f"migration_report_{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n💾 Report saved as: {filename}")
        
        elif output_format == 'csv':
            # Create simplified CSV report
            csv_data = []
            csv_data.append(['Category', 'Metric', 'Value', 'Status'])
            
            if report_data['comprehensive_analysis']:
                comp = report_data['comprehensive_analysis']
                csv_data.append(['Comprehensive', 'Modules', comp.get('modules', 0), 'Info'])
                csv_data.append(['Comprehensive', 'Doctypes', comp.get('doctypes', 0), 'Info'])
                csv_data.append(['Comprehensive', 'Orphans', comp.get('orphans', 0), 'Warning' if comp.get('orphans', 0) > 0 else 'OK'])
                csv_data.append(['Comprehensive', 'App=None', comp.get('app_none', 0), 'Warning' if comp.get('app_none', 0) > 0 else 'OK'])
            
            csv_data.append(['Overall', 'Readiness Score', report_data['readiness_score'], 'Score'])
            
            filename = f"migration_report_{app_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(csv_data).to_csv(filename, index=False, header=False)
            print(f"\n💾 CSV report saved as: {filename}")
        
        print("=" * 70)
        return report_data
        
    except Exception as e:
        print(f"❌ Migration report generation failed: {e}")
        return None


@with_session_management
def compare_app_versions(source_app, target_app=None):
    """
    Compare app versions and compatibility
    """
    print(f"🔄 VERSION COMPARISON: {source_app}" + (f" vs {target_app}" if target_app else ""))
    print("=" * 70)
    
    try:
        # Get app info
        source_info = frappe.get_doc('App', source_app) if frappe.db.exists('App', source_app) else None
        target_info = frappe.get_doc('App', target_app) if target_app and frappe.db.exists('App', target_app) else None
        
        print(f"\n📦 APP VERSIONS")
        print("-" * 40)
        
        if source_info:
            print(f"Source: {source_app} - {source_info.get('app_version', 'Unknown')}")
        else:
            print(f"Source: {source_app} - Not installed in current site")
        
        if target_info:
            print(f"Target: {target_app} - {target_info.get('app_version', 'Unknown')}")
        elif target_app:
            print(f"Target: {target_app} - Not installed in current site")
        
        # Compare dependencies
        print(f"\n🔗 DEPENDENCY COMPARISON")
        print("-" * 40)
        
        if source_info and target_info:
            source_deps = source_info.get('dependencies', [])
            target_deps = target_info.get('dependencies', [])
            
            common_deps = set(source_deps) & set(target_deps)
            source_only = set(source_deps) - set(target_deps)
            target_only = set(target_deps) - set(source_deps)
            
            print(f"Common dependencies: {len(common_deps)}")
            print(f"Dependencies only in source: {len(source_only)}")
            print(f"Dependencies only in target: {len(target_only)}")
            
            if source_only:
                print("\n⚠️  Dependencies missing in target:")
                for dep in list(source_only)[:5]:
                    print(f"  • {dep}")
        
        # Compatibility assessment
        print(f"\n💡 COMPATIBILITY ASSESSMENT")
        print("-" * 40)
        
        if not target_app:
            print("No target app specified - showing source app analysis only")
            recommendations = ["Consider version requirements for target environment"]
        elif not source_info or not target_info:
            print("Cannot compare - one or both apps not installed")
            recommendations = ["Install both apps for proper version comparison"]
        else:
            recommendations = [
                "Check Frappe version compatibility",
                "Verify Python dependency versions",
                "Test in staging environment before production migration"
            ]
        
        for rec in recommendations:
            print(f"  • {rec}")
        
        print("=" * 70)
        return {
            'source_version': source_info.get('app_version') if source_info else None,
            'target_version': target_info.get('app_version') if target_info else None,
            'comparable': source_info and target_info
        }
        
    except Exception as e:
        print(f"❌ Version comparison failed: {e}")
        return None


if __name__ == "__main__":
    # Test analysis tools
    import sys
    if len(sys.argv) > 1:
        app_name = sys.argv[1]
        if len(sys.argv) > 2 and sys.argv[1] == 'security':
            analyze_app_security(sys.argv[2])
        elif len(sys.argv) > 2 and sys.argv[1] == 'performance':
            analyze_performance_metrics(sys.argv[2])
        elif len(sys.argv) > 2 and sys.argv[1] == 'volume':
            analyze_data_volume(sys.argv[2])
        else:
            analyze_app_comprehensive(app_name)
    else:
        multi_bench_analysis()
