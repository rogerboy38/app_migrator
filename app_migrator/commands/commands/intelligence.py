"""
App Migrator Intelligence Commands
AI-powered migration analysis and prediction
"""

import click
import json
import os
from datetime import datetime

try:
    import frappe
    from frappe.commands import pass_context
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    pass_context = lambda f: f


# ==================== PREDICT SUCCESS ====================

@click.command('app-migrator-predict-success')
@click.option('--site', required=True, help='Site name')
@click.option('--source-app', required=True, help='Source app to analyze')
@click.option('--target-version', default='16', help='Target Frappe version')
@pass_context
def predict_success(context, site, source_app, target_version):
    """Predict migration success probability using heuristics"""
    print(f"🔮 MIGRATION SUCCESS PREDICTION")
    print(f"   App: {source_app}")
    print(f"   Target: Frappe v{target_version}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Collect metrics
    metrics = {
        "doctypes": 0,
        "custom_doctypes": 0,
        "custom_fields": 0,
        "workflows": 0,
        "print_formats": 0,
        "reports": 0,
        "hooks_complexity": 0,
        "deprecated_apis": 0
    }
    
    # Count doctypes
    module_title = source_app.replace("_", " ").title()
    doctypes = frappe.get_all("DocType", filters={"module": module_title}, fields=["name", "custom"])
    metrics["doctypes"] = len(doctypes)
    metrics["custom_doctypes"] = len([d for d in doctypes if d.custom])
    
    # Count custom fields
    for dt in doctypes:
        cf = frappe.get_all("Custom Field", filters={"dt": dt.name})
        metrics["custom_fields"] += len(cf)
    
    # Count workflows
    workflows = frappe.get_all("Workflow", filters={"document_type": ["in", [d.name for d in doctypes]]})
    metrics["workflows"] = len(workflows)
    
    # Check hooks.py complexity
    hooks_path = os.path.expanduser(f"~/frappe-bench/apps/{source_app}/{source_app}/hooks.py")
    if os.path.exists(hooks_path):
        with open(hooks_path, 'r') as f:
            hooks_content = f.read()
            metrics["hooks_complexity"] = len(hooks_content.split('\n'))
            
            # Check for deprecated patterns
            deprecated = ['doc_events', 'override_whitelisted_methods', 'jinja']
            for pattern in deprecated:
                if pattern in hooks_content:
                    metrics["deprecated_apis"] += 1
    
    frappe.db.close()
    
    # Calculate success score
    score = 100
    
    # Deductions
    if metrics["doctypes"] > 50:
        score -= 10
    if metrics["custom_fields"] > 100:
        score -= 10
    if metrics["workflows"] > 5:
        score -= 5
    if metrics["hooks_complexity"] > 200:
        score -= 10
    if metrics["deprecated_apis"] > 0:
        score -= metrics["deprecated_apis"] * 5
    
    # Bonuses
    if metrics["custom_doctypes"] > metrics["doctypes"] * 0.8:
        score += 5  # Custom doctypes migrate easier
    
    score = max(0, min(100, score))
    
    # Display results
    print(f"\n📊 ANALYSIS METRICS:")
    print(f"   DocTypes: {metrics['doctypes']}")
    print(f"   Custom DocTypes: {metrics['custom_doctypes']}")
    print(f"   Custom Fields: {metrics['custom_fields']}")
    print(f"   Workflows: {metrics['workflows']}")
    print(f"   Hooks Complexity: {metrics['hooks_complexity']} lines")
    print(f"   Deprecated APIs: {metrics['deprecated_apis']}")
    
    print(f"\n🎯 SUCCESS PREDICTION: {score}%")
    
    if score >= 80:
        print("   ✅ HIGH probability of success")
        print("   Recommendation: Proceed with standard migration")
    elif score >= 60:
        print("   ⚠️ MEDIUM probability - review warnings")
        print("   Recommendation: Use staging environment first")
    else:
        print("   ❌ LOW probability - significant issues detected")
        print("   Recommendation: Manual review required")
    
    # Risk factors
    print(f"\n⚠️ RISK FACTORS:")
    if metrics["deprecated_apis"] > 0:
        print(f"   • {metrics['deprecated_apis']} deprecated API patterns found")
    if metrics["hooks_complexity"] > 200:
        print(f"   • Complex hooks.py ({metrics['hooks_complexity']} lines)")
    if metrics["workflows"] > 5:
        print(f"   • Multiple workflows may need updating")


# ==================== GENERATE INTELLIGENT PLAN ====================

@click.command('app-migrator-generate-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--source-apps', required=True, help='Comma-separated source apps')
@click.option('--target-app', required=True, help='Target consolidated app')
@click.option('--output', '-o', default='migration_plan.json', help='Output file')
@pass_context
def generate_intelligent_plan(context, site, source_apps, target_app, output):
    """Generate an intelligent migration plan with dependency analysis"""
    print(f"🧠 INTELLIGENT PLAN GENERATION")
    print(f"   Sources: {source_apps}")
    print(f"   Target: {target_app}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    apps_list = [a.strip() for a in source_apps.split(',')]
    
    plan = {
        "version": "9.0.0-intelligent",
        "created": datetime.now().isoformat(),
        "analysis_mode": "intelligent",
        "source_apps": apps_list,
        "target_app": target_app,
        "phases": [],
        "dependencies": {},
        "warnings": [],
        "estimated_time": "unknown"
    }
    
    all_doctypes = []
    doctype_dependencies = {}
    
    for app in apps_list:
        module_title = app.replace("_", " ").title()
        doctypes = frappe.get_all("DocType", 
            filters={"module": module_title}, 
            fields=["name", "istable"])
        
        for dt in doctypes:
            all_doctypes.append({"name": dt.name, "app": app, "is_child": dt.istable})
            
            # Analyze links (dependencies)
            try:
                meta = frappe.get_meta(dt.name)
                links = []
                for field in meta.fields:
                    if field.fieldtype == "Link" and field.options:
                        links.append(field.options)
                doctype_dependencies[dt.name] = links
            except:
                doctype_dependencies[dt.name] = []
    
    # Build phases based on dependencies
    phase1 = []  # No dependencies
    phase2 = []  # Has dependencies on phase1
    phase3 = []  # Everything else
    
    doctype_names = [d["name"] for d in all_doctypes]
    
    for dt in all_doctypes:
        deps = doctype_dependencies.get(dt["name"], [])
        internal_deps = [d for d in deps if d in doctype_names]
        
        if not internal_deps or dt["is_child"]:
            phase1.append(dt)
        elif all(d in [p["name"] for p in phase1] for d in internal_deps):
            phase2.append(dt)
        else:
            phase3.append(dt)
    
    plan["phases"] = [
        {"name": "Phase 1 - Foundation", "doctypes": [d["name"] for d in phase1], "count": len(phase1)},
        {"name": "Phase 2 - Dependent", "doctypes": [d["name"] for d in phase2], "count": len(phase2)},
        {"name": "Phase 3 - Complex", "doctypes": [d["name"] for d in phase3], "count": len(phase3)}
    ]
    plan["dependencies"] = doctype_dependencies
    
    # Estimate time
    total_doctypes = len(all_doctypes)
    if total_doctypes < 10:
        plan["estimated_time"] = "15-30 minutes"
    elif total_doctypes < 30:
        plan["estimated_time"] = "1-2 hours"
    else:
        plan["estimated_time"] = "2-4 hours"
    
    frappe.db.close()
    
    # Save plan
    with open(output, 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"\n📊 PLAN SUMMARY:")
    for phase in plan["phases"]:
        print(f"   {phase['name']}: {phase['count']} doctypes")
    print(f"\n⏱️ Estimated Time: {plan['estimated_time']}")
    print(f"\n✅ Plan saved: {output}")


# ==================== DIAGNOSE APP ====================

@click.command('app-migrator-diagnose')
@click.argument('app_name')
@click.option('--site', help='Site name (optional, for DB analysis)')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def diagnose_app(context, app_name, site, output):
    """Comprehensive app diagnosis for migration readiness"""
    print(f"🔬 APP DIAGNOSIS: {app_name}")
    print("=" * 60)
    
    diagnosis = {
        "app_name": app_name,
        "timestamp": datetime.now().isoformat(),
        "filesystem": {},
        "database": {},
        "hooks": {},
        "issues": [],
        "recommendations": []
    }
    
    app_path = os.path.expanduser(f"~/frappe-bench/apps/{app_name}")
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    # Filesystem analysis
    print(f"\n📁 FILESYSTEM ANALYSIS:")
    
    pkg_path = os.path.join(app_path, app_name)
    has_pyproject = os.path.exists(os.path.join(app_path, "pyproject.toml"))
    has_hooks = os.path.exists(os.path.join(pkg_path, "hooks.py"))
    has_modules = os.path.exists(os.path.join(pkg_path, "modules.txt"))
    
    diagnosis["filesystem"] = {
        "path": app_path,
        "has_pyproject": has_pyproject,
        "has_hooks": has_hooks,
        "has_modules_txt": has_modules,
        "structure": "modern" if has_pyproject else "traditional"
    }
    
    print(f"   Structure: {diagnosis['filesystem']['structure']}")
    print(f"   pyproject.toml: {'✅' if has_pyproject else '❌'}")
    print(f"   hooks.py: {'✅' if has_hooks else '❌'}")
    print(f"   modules.txt: {'✅' if has_modules else '❌'}")
    
    # Count modules and doctypes
    module_count = 0
    doctype_count = 0
    if os.path.isdir(pkg_path):
        for item in os.listdir(pkg_path):
            item_path = os.path.join(pkg_path, item)
            if os.path.isdir(item_path):
                doctype_dir = os.path.join(item_path, "doctype")
                if os.path.isdir(doctype_dir):
                    module_count += 1
                    doctype_count += len([d for d in os.listdir(doctype_dir) 
                                         if os.path.isdir(os.path.join(doctype_dir, d)) 
                                         and not d.startswith('_')])
    
    diagnosis["filesystem"]["modules"] = module_count
    diagnosis["filesystem"]["doctypes"] = doctype_count
    print(f"   Modules: {module_count}")
    print(f"   DocTypes: {doctype_count}")
    
    # Hooks analysis
    if has_hooks:
        print(f"\n🔗 HOOKS ANALYSIS:")
        hooks_path = os.path.join(pkg_path, "hooks.py")
        with open(hooks_path, 'r') as f:
            hooks_content = f.read()
        
        # Check for common hook types
        hook_types = [
            ("doc_events", "Document Events"),
            ("override_doctype_class", "DocType Overrides"),
            ("scheduler_events", "Scheduler"),
            ("on_session_creation", "Session Hooks"),
            ("jenv", "Jinja Environment"),
            ("fixtures", "Fixtures")
        ]
        
        found_hooks = []
        for hook, name in hook_types:
            if hook in hooks_content:
                found_hooks.append(name)
                print(f"   ✓ {name}")
        
        diagnosis["hooks"]["found"] = found_hooks
        diagnosis["hooks"]["lines"] = len(hooks_content.split('\n'))
    
    # Database analysis (if site provided)
    if site:
        print(f"\n💾 DATABASE ANALYSIS:")
        try:
            frappe.init(site=site)
            frappe.connect()
            
            module_title = app_name.replace("_", " ").title()
            db_doctypes = frappe.get_all("DocType", filters={"module": module_title})
            db_custom_fields = 0
            
            for dt in db_doctypes:
                cf = frappe.get_all("Custom Field", filters={"dt": dt.name})
                db_custom_fields += len(cf)
            
            diagnosis["database"] = {
                "doctypes_in_db": len(db_doctypes),
                "custom_fields": db_custom_fields
            }
            
            print(f"   DocTypes in DB: {len(db_doctypes)}")
            print(f"   Custom Fields: {db_custom_fields}")
            
            # Check for mismatches
            if len(db_doctypes) != doctype_count:
                issue = f"Mismatch: {doctype_count} doctypes in filesystem, {len(db_doctypes)} in database"
                diagnosis["issues"].append(issue)
                print(f"   ⚠️ {issue}")
            
            frappe.db.close()
        except Exception as e:
            print(f"   ⚠️ Could not analyze database: {e}")
    
    # Generate recommendations
    print(f"\n📋 RECOMMENDATIONS:")
    
    if not has_pyproject:
        rec = "Upgrade to modern pyproject.toml structure"
        diagnosis["recommendations"].append(rec)
        print(f"   • {rec}")
    
    if not has_modules:
        rec = "Create modules.txt to define app modules"
        diagnosis["recommendations"].append(rec)
        print(f"   • {rec}")
    
    if doctype_count > 30:
        rec = "Consider splitting into multiple apps for maintainability"
        diagnosis["recommendations"].append(rec)
        print(f"   • {rec}")
    
    if not diagnosis["recommendations"]:
        print(f"   ✅ App looks healthy for migration!")
    
    # Save output
    if output:
        with open(output, 'w') as f:
            json.dump(diagnosis, f, indent=2)
        print(f"\n✅ Diagnosis saved: {output}")


# Export commands
commands = [
    predict_success,
    generate_intelligent_plan,
    diagnose_app
]
