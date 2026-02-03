#!/usr/bin/env python3
"""
Enhanced Orphan Doctype Fixer
Fixes orphan doctypes by analyzing naming patterns:
- Title Case vs UPPERCASE vs snake_case
- Module name mismatches
- Case sensitivity issues
"""

import click
import json
import os
import re
import frappe
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def get_doctype_module_map(site: str) -> Dict[str, str]:
    """Get current doctype to module mapping from database"""
    try:
        frappe.init(site=site)
        frappe.connect()
        
        doctype_module_map = {}
        doctypes = frappe.get_all("DocType", fields=["name", "module"])
        for dt in doctypes:
            doctype_module_map[dt.name] = dt.module
        
        frappe.destroy()
        return doctype_module_map
    except Exception as e:
        click.echo(f"❌ Error connecting to site {site}: {e}")
        return {}

def analyze_naming_patterns(doctype_name: str) -> Dict[str, str]:
    """Analyze doctype naming patterns and suggest fixes"""
    patterns = {
        'original': doctype_name,
        'suggestions': []
    }
    
    # Common pattern issues
    # 1. Title Case (should match module naming)
    title_case = doctype_name.replace('_', ' ').title().replace(' ', '')
    if title_case != doctype_name:
        patterns['suggestions'].append({
            'type': 'title_case',
            'value': title_case,
            'description': 'Converted to TitleCase'
        })
    
    # 2. UPPERCASE (sometimes modules are all caps)
    uppercase = doctype_name.upper()
    if uppercase != doctype_name:
        patterns['suggestions'].append({
            'type': 'uppercase',
            'value': uppercase,
            'description': 'Converted to UPPERCASE'
        })
    
    # 3. snake_case (proper module naming)
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', doctype_name).lower()
    if snake_case != doctype_name.lower():
        patterns['suggestions'].append({
            'type': 'snake_case',
            'value': snake_case,
            'description': 'Converted to snake_case'
        })
    
    # 4. CamelCase (common in Frappe)
    camel_case = ''.join(word.capitalize() for word in doctype_name.split('_'))
    if camel_case != doctype_name and '_' in doctype_name:
        patterns['suggestions'].append({
            'type': 'camel_case',
            'value': camel_case,
            'description': 'Converted to CamelCase'
        })
    
    return patterns

def find_matching_module(doctype_name: str, available_modules: List[str]) -> Optional[str]:
    """Find best matching module for a doctype based on naming patterns"""
    if not available_modules:
        return None
    
    doctype_lower = doctype_name.lower()
    
    # Try exact match first
    for module in available_modules:
        if module.lower() == doctype_lower:
            return module
    
    # Try partial matches
    for module in available_modules:
        module_lower = module.lower()
        
        # Check if doctype contains module name or vice versa
        if module_lower in doctype_lower or doctype_lower in module_lower:
            return module
        
        # Check for common patterns
        module_no_space = module_lower.replace(' ', '')
        doctype_no_space = doctype_lower.replace(' ', '')
        
        if module_no_space in doctype_no_space or doctype_no_space in module_no_space:
            return module
    
    return None

def fix_orphan_doctype(site: str, doctype_name: str, target_module: str, dry_run: bool = True) -> bool:
    """Fix a single orphan doctype by reassigning its module"""
    try:
        frappe.init(site=site)
        frappe.connect()
        
        click.echo(f"🔧 Fixing: {doctype_name} → module: {target_module}")
        
        if not dry_run:
            # Get the doctype
            dt = frappe.get_doc("DocType", doctype_name)
            old_module = dt.module
            
            # Update module
            dt.module = target_module
            dt.save()
            
            click.echo(f"✅ Fixed: {doctype_name} ({old_module} → {target_module})")
            
            # Also update customizations if any
            frappe.db.commit()
        else:
            click.echo(f"📋 [DRY RUN] Would fix: {doctype_name} → module: {target_module}")
        
        frappe.destroy()
        return True
        
    except Exception as e:
        click.echo(f"❌ Error fixing {doctype_name}: {e}")
        frappe.destroy()
        return False

@click.command('fix-orphans-enhanced')
@click.option('--site', required=True, help='Site name')
@click.option('--app', help='Specific app to analyze (optional)')
@click.option('--module-pattern', help='Module pattern to match (regex)')
@click.option('--apply', is_flag=True, help='Apply fixes (without this, dry run)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def fix_orphans_enhanced(site, app, module_pattern, apply, verbose):
    """
    Enhanced orphan doctype fixer with pattern matching
    
    Fixes orphan doctypes by analyzing:
    - Title Case vs UPPERCASE vs snake_case patterns
    - Module name mismatches
    - Case sensitivity issues
    
    Example:
        bench app-migrator fix-orphans-enhanced --site mysite --apply
    """
    
    dry_run = not apply
    
    if dry_run:
        click.echo("🔍 RUNNING IN DRY RUN MODE (use --apply to make changes)")
    
    click.echo(f"🔧 ENHANCED ORPHAN DOCTYPE FIXER")
    click.echo(f"   Site: {site}")
    click.echo(f"   App: {app or 'All apps'}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 50)
    
    # Get current doctype-module mapping
    click.echo("📊 Analyzing current doctype-module mapping...")
    doctype_module_map = get_doctype_module_map(site)
    
    if not doctype_module_map:
        click.echo("❌ Could not retrieve doctype information")
        return
    
    click.echo(f"📋 Found {len(doctype_module_map)} doctypes in database")
    
    # Group doctypes by module to find orphans
    module_doctypes = {}
    orphan_doctypes = []
    
    for doctype, module in doctype_module_map.items():
        if module not in module_doctypes:
            module_doctypes[module] = []
        module_doctypes[module].append(doctype)
    
    # Find modules with very few doctypes (potential orphans)
    for module, doctypes in module_doctypes.items():
        if len(doctypes) <= 2:  # Modules with 2 or fewer doctypes
            for doctype in doctypes:
                orphan_doctypes.append({
                    'name': doctype,
                    'current_module': module,
                    'doctype_count': len(doctypes)
                })
    
    click.echo(f"🔍 Found {len(orphan_doctypes)} potential orphan doctypes")
    
    if not orphan_doctypes:
        click.echo("✅ No orphan doctypes found!")
        return
    
    # Analyze and suggest fixes
    click.echo("\n📝 ANALYZING ORPHAN DOCTYPES:")
    fixed_count = 0
    
    for orphan in orphan_doctypes:
        doctype_name = orphan['name']
        current_module = orphan['current_module']
        
        click.echo(f"\n📋 Doctype: {doctype_name}")
        click.echo(f"   Current module: {current_module} ({orphan['doctype_count']} doctypes)")
        
        # Analyze naming patterns
        patterns = analyze_naming_patterns(doctype_name)
        
        if patterns['suggestions']:
            click.echo("   Pattern analysis:")
            for suggestion in patterns['suggestions']:
                click.echo(f"     • {suggestion['type']}: {suggestion['value']} ({suggestion['description']})")
        
        # Get available modules (excluding current)
        available_modules = [m for m in module_doctypes.keys() 
                           if m != current_module and len(module_doctypes[m]) > 2]
        
        # Find best matching module
        target_module = find_matching_module(doctype_name, available_modules)
        
        if target_module:
            click.echo(f"   ✅ Suggested module: {target_module}")
            
            # Apply fix
            if fix_orphan_doctype(site, doctype_name, target_module, dry_run):
                fixed_count += 1
        else:
            click.echo(f"   ⚠️  No clear module match found")
    
    # Summary
    click.echo("\n" + "=" * 50)
    click.echo("📊 SUMMARY:")
    click.echo(f"   Analyzed: {len(orphan_doctypes)} orphan doctypes")
    click.echo(f"   Fixed: {fixed_count} doctypes")
    
    if dry_run and fixed_count > 0:
        click.echo("\n💡 Run with --apply to apply these fixes")
    
    click.echo("✅ Analysis complete!")

if __name__ == "__main__":
    fix_orphans_enhanced()
