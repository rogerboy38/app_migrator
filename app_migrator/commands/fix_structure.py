"""fix-structure command (T1.8.3 — extracted from __init__.py)"""

import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

from ._shared import (
    ProgressTracker,
    MigrationSession,
    get_current_site,
    detect_available_benches,
    get_bench_apps,
)


@click.command('app-migrator-fix-structure')
@click.argument('app_name')
@pass_context
def app_migrator_fix_structure(context, app_name):
    """
    Analyze Frappe app folder structure and report findings.
    
    Frappe apps can have different valid structures:
    
    1. Single-module app (module name = app name):
       apps/{app}/{app}/{app}/doctype/  <- VALID (triple-nested)
       
    2. Multi-module app:
       apps/{app}/{app}/{module1}/doctype/
       apps/{app}/{app}/{module2}/doctype/
    
    This command analyzes the structure and reports what it finds.
    It does NOT automatically move files (that was causing issues).
    """
    print(f"🔍 ANALYZE APP STRUCTURE")
    print(f"   App: {app_name}")
    print("=" * 60)
    
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    app_path = os.path.join(apps_dir, app_name)
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    # Level structure
    level1 = app_path  # apps/{app}/
    level2 = os.path.join(level1, app_name)  # apps/{app}/{app}/
    
    print(f"\n📁 DIRECTORY STRUCTURE:")
    print(f"   Level 1 (repo root): {level1}")
    
    # Check level2
    if not os.path.isdir(level2):
        print(f"   ❌ Level 2 missing: {level2}")
        print(f"\n⚠️ Invalid app structure - missing Python package folder")
        return
    
    print(f"   Level 2 (package):   {level2}")
    
    # Check for hooks.py at level2
    hooks_path = os.path.join(level2, "hooks.py")
    modules_txt_path = os.path.join(level2, "modules.txt")
    
    print(f"\n📋 PACKAGE FILES:")
    print(f"   hooks.py:    {'✅ Found' if os.path.exists(hooks_path) else '❌ Missing'}")
    print(f"   modules.txt: {'✅ Found' if os.path.exists(modules_txt_path) else '❌ Missing'}")
    
    # Read modules.txt
    modules = []
    if os.path.exists(modules_txt_path):
        with open(modules_txt_path, 'r') as f:
            modules = [m.strip() for m in f.readlines() if m.strip()]
        print(f"\n📦 MODULES DEFINED ({len(modules)}):")
        for m in modules:
            print(f"   • {m}")
    
    # Check module folders at level2
    print(f"\n📂 MODULE FOLDERS AT LEVEL 2:")
    
    level2_dirs = [d for d in os.listdir(level2) 
                   if os.path.isdir(os.path.join(level2, d)) 
                   and not d.startswith('.') 
                   and d not in ['__pycache__', 'templates', 'public', 'patches', 'config', 'www']]
    
    for dir_name in sorted(level2_dirs):
        dir_path = os.path.join(level2, dir_name)
        has_doctype = os.path.isdir(os.path.join(dir_path, "doctype"))
        has_page = os.path.isdir(os.path.join(dir_path, "page"))
        has_report = os.path.isdir(os.path.join(dir_path, "report"))
        
        if has_doctype or has_page or has_report:
            # This is a module folder
            module_title = dir_name.replace("_", " ").title()
            in_modules_txt = module_title in modules or dir_name in [m.lower().replace(" ", "_") for m in modules]
            
            doctype_count = 0
            if has_doctype:
                doctype_path = os.path.join(dir_path, "doctype")
                doctype_count = len([d for d in os.listdir(doctype_path) 
                                    if os.path.isdir(os.path.join(doctype_path, d)) and d != '__pycache__'])
            
            status = "✅" if in_modules_txt else "⚠️ NOT IN modules.txt"
            print(f"   • {dir_name}/ - {doctype_count} doctypes {status}")
            
            if has_doctype:
                print(f"      └── doctype/")
            if has_page:
                print(f"      └── page/")
            if has_report:
                print(f"      └── report/")
    
    # Check for doctypes directly at level2
    direct_doctype = os.path.join(level2, "doctype")
    if os.path.isdir(direct_doctype):
        doctype_count = len([d for d in os.listdir(direct_doctype) 
                            if os.path.isdir(os.path.join(direct_doctype, d)) and d != '__pycache__'])
        print(f"\n⚠️ DOCTYPES DIRECTLY AT LEVEL 2 ({doctype_count}):")
        print(f"   Path: {direct_doctype}")
        print(f"   This is unusual - doctypes should be inside a module folder.")
        print(f"   Expected: apps/{app_name}/{app_name}/{app_name}/doctype/")
        print(f"   Found:    apps/{app_name}/{app_name}/doctype/")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    
    # Check if app_name is also a module
    app_module_path = os.path.join(level2, app_name, "doctype")
    if os.path.isdir(app_module_path):
        print(f"   ✅ App uses module '{app_name}' (triple-nested structure is CORRECT)")
    elif os.path.isdir(direct_doctype):
        print(f"   ⚠️ App has doctypes at level2 without module folder")
        print(f"      This may cause import issues. Consider:")
        print(f"      1. Create module folder: {app_name}/{app_name}/{app_name}/")
        print(f"      2. Move doctype/ into it")
        print(f"      3. Update modules.txt with module name")
    else:
        print(f"   ℹ️ App structure looks standard")


