#!/usr/bin/env python3
"""
Orphan fixer that works without developer mode
Fixes orphan doctypes by reassigning to existing modules
"""

import click
import frappe
import json
import os
from pathlib import Path

def get_safe_module_mapping():
    """Get module mappings that should work without dev mode"""
    return {
        # Orphan module -> Safe target module
        "amb_w_tds2": "Amb W Tds2",  # Should exist
        "RND": "Rnd Nutrition",      # Consolidated
        "RND Nutrition": "Rnd Nutrition",  # Standardized
        "Raven Ai Agent": "Raven",   # Parent module
        "raven_ai_agent": "Raven",   # snake_case version
    }

@click.command('fix-orphans-safe')
@click.option('--site', required=True, help='Site name')
@click.option('--apply', is_flag=True, help='Apply fixes')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def fix_orphans_safe(site, apply, verbose):
    """
    Fix orphan doctypes safely without requiring developer mode
    
    This focuses on reassigning orphan doctypes to existing valid modules
    rather than renaming modules themselves.
    """
    
    dry_run = not apply
    
    click.echo(f"🔧 SAFE ORPHAN FIXER (No dev mode required)")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        click.echo("✅ Connected to site")
        
        # Get module mappings
        module_map = get_safe_module_mapping()
        
        # Track fixes
        fixes_applied = []
        
        # 1. Fix doctypes with invalid modules
        click.echo("\n🔍 CHECKING DOCTYPES WITH INVALID MODULES:")
        
        all_doctypes = frappe.get_all("DocType", 
            fields=["name", "module", "custom"],
            filters={"custom": 1})  # Only custom doctypes can be modified
        
        for dt in all_doctypes:
            dt_name = dt["name"]
            current_module = dt["module"]
            
            # Check if module exists
            module_exists = frappe.db.exists("Module Def", current_module)
            
            if not module_exists or current_module in module_map:
                # This doctype needs fixing
                target_module = None
                
                # Try to find a safe target module
                if current_module in module_map:
                    target_module = module_map[current_module]
                else:
                    # Try to find best match from existing modules
                    all_modules = frappe.get_all("Module Def", fields=["name"])
                    existing_modules = [m["name"] for m in all_modules]
                    
                    # Look for modules with similar names
                    dt_lower = dt_name.lower()
                    for module in existing_modules:
                        module_lower = module.lower()
                        if (module_lower in dt_lower or 
                            dt_lower in module_lower or
                            any(word in dt_lower for word in module_lower.split())):
                            target_module = module
                            break
                
                if target_module and frappe.db.exists("Module Def", target_module):
                    if verbose:
                        click.echo(f"📋 {dt_name}: '{current_module}' → '{target_module}'")
                    
                    if dry_run:
                        fixes_applied.append(f"{dt_name}: '{current_module}' → '{target_module}'")
                    else:
                        try:
                            dt_doc = frappe.get_doc("DocType", dt_name)
                            dt_doc.module = target_module
                            dt_doc.save()
                            frappe.db.commit()
                            click.echo(f"✅ Fixed: {dt_name} → '{target_module}'")
                            fixes_applied.append(f"{dt_name}: '{current_module}' → '{target_module}'")
                        except Exception as e:
                            click.echo(f"❌ Error fixing {dt_name}: {e}")
        
        # 2. Specifically fix Alexa User Mapping
        click.echo("\n🔍 SPECIFIC FIX: Alexa User Mapping")
        
        if frappe.db.exists("DocType", "Alexa User Mapping"):
            dt = frappe.get_doc("DocType", "Alexa User Mapping")
            
            # Check if it's in a problematic module
            if dt.module in ["Raven Ai Agent", "raven_ai_agent"]:
                # Find a safe alternative
                safe_modules = ["Raven", "Raven AI", "Raven Bot", "Raven Integrations"]
                target_module = None
                
                for module in safe_modules:
                    if frappe.db.exists("Module Def", module):
                        target_module = module
                        break
                
                if target_module:
                    if dry_run:
                        click.echo(f"📋 Would fix: Alexa User Mapping → '{target_module}'")
                        fixes_applied.append(f"Alexa User Mapping: '{dt.module}' → '{target_module}'")
                    else:
                        dt.module = target_module
                        dt.save()
                        frappe.db.commit()
                        click.echo(f"✅ Fixed: Alexa User Mapping → '{target_module}'")
                        fixes_applied.append(f"Alexa User Mapping: '{dt.module}' → '{target_module}'")
        
        # 3. Fix orphan custom fields
        click.echo("\n🔍 CHECKING ORPHAN CUSTOM FIELDS:")
        
        # Get the orphan custom fields from earlier scan
        orphan_cf_data = [
            {"dt": "COA AMB2", "field": "workflow_state"},
            {"dt": "Freight Location", "field": "custom_freight_cost_amb"},
            {"dt": "Freight Location", "field": "custom_lead_time_to_delivery"}
        ]
        
        for cf_info in orphan_cf_data:
            dt_name = cf_info["dt"]
            fieldname = cf_info["field"]
            
            # Check if doctype exists
            if frappe.db.exists("DocType", dt_name):
                # Check if custom field exists
                cf_exists = frappe.db.exists("Custom Field", {"dt": dt_name, "fieldname": fieldname})
                
                if cf_exists:
                    if verbose:
                        click.echo(f"📋 Custom field exists: {fieldname} in {dt_name}")
                    # Custom field is not actually orphaned if doctype exists
                else:
                    click.echo(f"⚠️ Custom field not found: {fieldname} in {dt_name}")
        
        frappe.destroy()
        
        # Summary
        click.echo("\n" + "=" * 60)
        click.echo("📊 SUMMARY:")
        
        if fixes_applied:
            click.echo(f"   Proposed/Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                click.echo(f"     • {fix}")
            
            if dry_run:
                click.echo(f"\n💡 Run with --apply to apply these {len(fixes_applied)} fixes")
        else:
            click.echo("   No fixes needed")
        
        click.echo("✅ Analysis complete!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'frappe' in locals():
            frappe.destroy()

if __name__ == "__main__":
    fix_orphans_safe()
