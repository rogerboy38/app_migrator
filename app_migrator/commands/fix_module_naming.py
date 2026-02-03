#!/usr/bin/env python3
"""
Module Naming Consistency Fixer
Fixes inconsistent module naming patterns across all apps:
- Title Case vs UPPERCASE vs snake_case inconsistencies
- Case sensitivity issues
- Module name standardization
"""

import click
import frappe
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set

def analyze_module_naming_pattern(module_name: str) -> Dict:
    """Analyze a module name and suggest corrections"""
    analysis = {
        'original': module_name,
        'pattern': 'unknown',
        'suggestions': [],
        'issues': []
    }
    
    # Detect pattern
    if module_name.isupper():
        analysis['pattern'] = 'UPPERCASE'
    elif module_name.islower() and '_' in module_name:
        analysis['pattern'] = 'snake_case'
    elif ' ' in module_name and module_name.istitle():
        analysis['pattern'] = 'Title Case'
    elif module_name[0].isupper() and not ' ' in module_name and not '_' in module_name:
        analysis['pattern'] = 'CamelCase'
    elif any(c.isupper() for c in module_name[1:]) and not module_name.isupper():
        analysis['pattern'] = 'mixedCase'
    
    # Check for common issues
    if '  ' in module_name:  # Double spaces
        analysis['issues'].append('contains double spaces')
    
    if module_name.startswith(' ') or module_name.endswith(' '):
        analysis['issues'].append('has leading/trailing spaces')
    
    if re.search(r'[^\w\s-]', module_name):  # Special characters
        analysis['issues'].append('contains special characters')
    
    # Generate suggestions
    # 1. Proper Title Case (standard Frappe convention)
    title_case = ' '.join(word.capitalize() for word in re.split(r'[\s_]+', module_name))
    if title_case != module_name:
        analysis['suggestions'].append({
            'type': 'title_case',
            'value': title_case,
            'description': 'Standard Frappe Title Case'
        })
    
    # 2. snake_case (Python module convention)
    snake_case = re.sub(r'[\s-]+', '_', module_name).lower()
    if snake_case != module_name.lower():
        analysis['suggestions'].append({
            'type': 'snake_case',
            'value': snake_case,
            'description': 'Python snake_case convention'
        })
    
    # 3. Clean version (remove extra spaces, special chars)
    clean = re.sub(r'\s+', ' ', module_name.strip())
    clean = re.sub(r'[^\w\s-]', '', clean)
    if clean != module_name:
        analysis['suggestions'].append({
            'type': 'clean',
            'value': clean,
            'description': 'Cleaned version'
        })
    
    return analysis

def get_app_module_mapping() -> Dict[str, List[str]]:
    """Get mapping of apps to their modules from hooks.py files"""
    app_module_map = {}
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    
    for app_dir in (bench_path / 'apps').iterdir():
        if app_dir.is_dir() and not app_dir.name.startswith('.'):
            app_name = app_dir.name
            modules_file = app_dir / app_name / 'modules.txt'
            
            if modules_file.exists():
                try:
                    with open(modules_file, 'r') as f:
                        modules = [line.strip() for line in f if line.strip()]
                        app_module_map[app_name] = modules
                except:
                    pass
    
    return app_module_map

def find_best_module_match(module_name: str, available_modules: List[str]) -> Optional[Tuple[str, float]]:
    """Find the best matching module with confidence score"""
    if not available_modules:
        return None
    
    module_lower = module_name.lower()
    best_match = None
    best_score = 0
    
    for available in available_modules:
        available_lower = available.lower()
        score = 0
        
        # Exact match (case-insensitive)
        if available_lower == module_lower:
            score = 1.0
        # Contains match
        elif available_lower in module_lower or module_lower in available_lower:
            score = 0.8
        # Similar after normalization
        else:
            # Normalize both names (remove spaces, underscores, special chars)
            norm1 = re.sub(r'[\s_]+', '', module_lower)
            norm2 = re.sub(r'[\s_]+', '', available_lower)
            if norm1 == norm2:
                score = 0.9
        
        if score > best_score:
            best_score = score
            best_match = available
    
    if best_score > 0.6:  # Reasonable confidence threshold
        return (best_match, best_score)
    
    return None

@click.command('fix-module-names')
@click.option('--site', required=True, help='Site name')
@click.option('--app', help='Specific app to fix (optional)')
@click.option('--pattern', type=click.Choice(['title_case', 'snake_case', 'uppercase', 'all']), 
              default='all', help='Pattern to fix')
@click.option('--apply', is_flag=True, help='Apply fixes')
@click.option('--dry-run', is_flag=True, help='Dry run only')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def fix_module_names(site, app, pattern, apply, dry_run, verbose):
    """
    Fix inconsistent module naming patterns across apps
    """
    if dry_run:
        apply = False
    
    click.echo(f"🔧 MODULE NAMING CONSISTENCY FIXER")
    click.echo(f"   Site: {site}")
    click.echo(f"   App: {app or 'All apps'}")
    click.echo(f"   Pattern: {pattern}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Get all modules from database
        db_modules = frappe.get_all("Module Def", fields=["name"], order_by="name")
        db_module_names = [m["name"] for m in db_modules]
        
        click.echo(f"📊 Found {len(db_module_names)} modules in database")
        
        # Get app-module mapping from filesystem
        app_module_map = get_app_module_mapping()
        click.echo(f"📁 Found {len(app_module_map)} apps with modules.txt")
        
        # Collect all unique module names from filesystem
        fs_module_names = set()
        for app_name, modules in app_module_map.items():
            if app and app_name != app:
                continue
            fs_module_names.update(modules)
        
        click.echo(f"📝 Found {len(fs_module_names)} unique module names in apps")
        
        # Analyze inconsistencies
        click.echo("\n🔍 ANALYZING NAMING INCONSISTENCIES:")
        
        inconsistencies = []
        for module_name in sorted(db_module_names):
            analysis = analyze_module_naming_pattern(module_name)
            
            has_issues = len(analysis['issues']) > 0
            pattern_mismatch = analysis['pattern'] not in ['Title Case', 'CamelCase', 'snake_case']
            
            if has_issues or pattern_mismatch or analysis['suggestions']:
                # Check if this module exists in any app
                in_apps = []
                for app_name, modules in app_module_map.items():
                    if module_name in modules:
                        in_apps.append(app_name)
                
                inconsistencies.append({
                    'module': module_name,
                    'pattern': analysis['pattern'],
                    'issues': analysis['issues'],
                    'suggestions': analysis['suggestions'],
                    'in_apps': in_apps,
                    'in_fs': module_name in fs_module_names
                })
        
        if not inconsistencies:
            click.echo("✅ No naming inconsistencies found!")
            frappe.destroy()
            return
        
        click.echo(f"⚠️ Found {len(inconsistencies)} modules with naming issues")
        
        # Process inconsistencies
        fixed_count = 0
        for inc in inconsistencies:
            if verbose or inc['in_fs']:  # Show modules that exist in filesystem
                click.echo(f"\n📋 Module: {inc['module']}")
                click.echo(f"   Pattern: {inc['pattern']}")
                if inc['issues']:
                    click.echo(f"   Issues: {', '.join(inc['issues'])}")
                if inc['in_apps']:
                    click.echo(f"   Used in: {', '.join(inc['in_apps'])}")
                
                # Show suggestions
                if inc['suggestions']:
                    click.echo("   Suggestions:")
                    for suggestion in inc['suggestions']:
                        if pattern == 'all' or pattern == suggestion['type']:
                            click.echo(f"     • {suggestion['type']}: {suggestion['value']}")
                    
                    # Apply fix if requested
                    if apply and inc['suggestions']:
                        # Use first suggestion that matches pattern
                        target_suggestion = None
                        for suggestion in inc['suggestions']:
                            if pattern == 'all' or pattern == suggestion['type']:
                                target_suggestion = suggestion
                                break
                        
                        if target_suggestion:
                            old_name = inc['module']
                            new_name = target_suggestion['value']
                            
                            # Check if new name already exists
                            if new_name in db_module_names and new_name != old_name:
                                click.echo(f"   ⚠️ Cannot rename to '{new_name}' - already exists")
                                continue
                            
                            # Update module definition
                            try:
                                module_doc = frappe.get_doc("Module Def", old_name)
                                module_doc.module_name = new_name
                                module_doc.save()
                                
                                # Update all doctypes using this module
                                doctypes = frappe.get_all("DocType", 
                                    filters={"module": old_name},
                                    fields=["name"])
                                
                                for dt in doctypes:
                                    dt_doc = frappe.get_doc("DocType", dt["name"])
                                    dt_doc.module = new_name
                                    dt_doc.save()
                                
                                frappe.db.commit()
                                click.echo(f"   ✅ Renamed: '{old_name}' → '{new_name}'")
                                click.echo(f"      Updated {len(doctypes)} doctypes")
                                fixed_count += 1
                                
                            except Exception as e:
                                click.echo(f"   ❌ Error renaming: {e}")
        
        # Also check for modules in DB that don't exist in filesystem
        click.echo("\n🔍 CHECKING FOR ORPHAN MODULES (in DB but not in apps):")
        orphan_modules = []
        for module_name in db_module_names:
            if module_name not in fs_module_names:
                # Check if any doctypes use this module
                doctypes = frappe.get_all("DocType", 
                    filters={"module": module_name},
                    fields=["name"])
                
                if doctypes:
                    orphan_modules.append({
                        'module': module_name,
                        'doctype_count': len(doctypes),
                        'doctypes': [d["name"] for d in doctypes[:3]]  # First 3
                    })
        
        if orphan_modules:
            click.echo(f"⚠️ Found {len(orphan_modules)} modules in DB not linked to apps:")
            for orphan in orphan_modules[:5]:  # Show first 5
                click.echo(f"   • {orphan['module']} ({orphan['doctype_count']} doctypes)")
                if verbose:
                    click.echo(f"     Doctypes: {', '.join(orphan['doctypes'])}")
            
            if len(orphan_modules) > 5:
                click.echo(f"   ... and {len(orphan_modules) - 5} more")
        else:
            click.echo("✅ No orphan modules found")
        
        frappe.destroy()
        
        # Summary
        click.echo("\n" + "=" * 60)
        click.echo("📊 SUMMARY:")
        click.echo(f"   Analyzed: {len(db_module_names)} modules")
        click.echo(f"   Found: {len(inconsistencies)} naming inconsistencies")
        click.echo(f"   Fixed: {fixed_count} modules")
        
        if not apply and fixed_count > 0:
            click.echo("\n💡 Run with --apply to fix these inconsistencies")
        
        click.echo("✅ Analysis complete!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        frappe.destroy()

@click.command('standardize-modules')
@click.option('--site', required=True, help='Site name')
@click.option('--to', type=click.Choice(['title_case', 'snake_case']), 
              default='title_case', help='Target naming convention')
@click.option('--apply', is_flag=True, help='Apply standardization')
def standardize_modules(site, to, apply):
    """
    Standardize all modules to a consistent naming convention
    """
    click.echo(f"🎯 MODULE STANDARDIZATION: Converting to {to}")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Get all modules
        modules = frappe.get_all("Module Def", fields=["name"])
        
        conversions = []
        for module in modules:
            old_name = module["name"]
            
            # Convert to target convention
            if to == 'title_case':
                new_name = ' '.join(word.capitalize() for word in re.split(r'[\s_]+', old_name))
            elif to == 'snake_case':
                new_name = re.sub(r'[\s-]+', '_', old_name).lower()
            
            # Only add if name would change
            if new_name != old_name:
                # Check if new name already exists
                if frappe.db.exists("Module Def", new_name):
                    click.echo(f"⚠️ Skipping '{old_name}' → '{new_name}' (already exists)")
                    continue
                
                conversions.append({
                    'old': old_name,
                    'new': new_name
                })
        
        if not conversions:
            click.echo("✅ All modules already follow the target convention!")
            frappe.destroy()
            return
        
        click.echo(f"📋 Found {len(conversions)} modules to standardize")
        
        if apply:
            click.echo("\n🔄 APPLYING STANDARDIZATION:")
            for conv in conversions:
                try:
                    # Update module definition
                    module_doc = frappe.get_doc("Module Def", conv['old'])
                    module_doc.module_name = conv['new']
                    module_doc.save()
                    
                    # Update all doctypes
                    doctypes = frappe.get_all("DocType", 
                        filters={"module": conv['old']},
                        fields=["name"])
                    
                    for dt in doctypes:
                        dt_doc = frappe.get_doc("DocType", dt["name"])
                        dt_doc.module = conv['new']
                        dt_doc.save()
                    
                    click.echo(f"   ✅ {conv['old']} → {conv['new']} ({len(doctypes)} doctypes)")
                    
                except Exception as e:
                    click.echo(f"   ❌ Error converting {conv['old']}: {e}")
            
            frappe.db.commit()
            click.echo(f"\n✅ Standardized {len(conversions)} modules")
            
        else:
            click.echo("\n📋 PROPOSED CHANGES (dry run):")
            for conv in conversions[:20]:  # Show first 20
                # Count doctypes
                doctypes = frappe.get_all("DocType", 
                    filters={"module": conv['old']},
                    fields=["name"])
                
                click.echo(f"   • {conv['old']} → {conv['new']} ({len(doctypes)} doctypes)")
            
            if len(conversions) > 20:
                click.echo(f"   ... and {len(conversions) - 20} more")
            
            click.echo(f"\n💡 Run with --apply to standardize {len(conversions)} modules")
        
        frappe.destroy()
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        frappe.destroy()

if __name__ == "__main__":
    fix_module_names()
