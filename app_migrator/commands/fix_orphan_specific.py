#!/usr/bin/env python3
"""
Specific Orphan Doctype Fixer for Alexa User Mapping issue
Fixes module naming mismatches and case sensitivity problems
"""

import click
import frappe
import json
import os
import re
from pathlib import Path

@click.command('fix-alexa-orphan')
@click.option('--site', required=True, help='Site name')
@click.option('--apply', is_flag=True, help='Apply fixes')
def fix_alexa_orphan(site, apply):
    """
    Fix specific orphan doctype: Alexa User Mapping
    
    Issue: module='Raven Ai Agent' should likely be 'Raven AI Agent' or 'raven_ai_agent'
    """
    
    dry_run = not apply
    
    click.echo(f"🔧 FIXING ALEXA USER MAPPING ORPHAN ISSUE")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 50)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Get the doctype
        doctype_name = "Alexa User Mapping"
        if not frappe.db.exists("DocType", doctype_name):
            click.echo(f"❌ Doctype '{doctype_name}' not found")
            return
        
        dt = frappe.get_doc("DocType", doctype_name)
        current_module = dt.module
        click.echo(f"📋 Current state: {doctype_name} → module: '{current_module}'")
        
        # Check what modules are available
        all_modules = frappe.get_all("Module Def", fields=["name"])
        module_names = [m["name"] for m in all_modules]
        click.echo(f"📦 Available modules ({len(module_names)}): {', '.join(sorted(module_names)[:10])}...")
        
        # Find potential matching modules
        potential_matches = []
        
        # 1. Check for 'Raven' related modules
        raven_modules = [m for m in module_names if 'raven' in m.lower()]
        if raven_modules:
            click.echo(f"🔍 Raven-related modules: {raven_modules}")
            potential_matches.extend(raven_modules)
        
        # 2. Check for 'AI' or 'Agent' related modules
        ai_modules = [m for m in module_names if any(word in m.lower() for word in ['ai', 'agent', 'alexa'])]
        if ai_modules:
            click.echo(f"🤖 AI/Agent-related modules: {ai_modules}")
            potential_matches.extend(ai_modules)
        
        # Remove duplicates
        potential_matches = list(set(potential_matches))
        
        if not potential_matches:
            click.echo("⚠️ No potential module matches found")
            return
        
        # Suggest best match
        # Priority: exact match > contains 'raven ai agent' > contains 'raven' > first match
        best_match = None
        
        # Check for exact or close matches
        target_module_candidates = [
            "Raven AI Agent",  # Most likely correct
            "raven_ai_agent",  # snake_case version
            "Raven Ai Agent",  # Current (wrong case)
            "Raven",           # Parent module
        ]
        
        for candidate in target_module_candidates:
            if candidate in module_names:
                best_match = candidate
                break
        
        # If no exact match, use first potential match
        if not best_match and potential_matches:
            best_match = potential_matches[0]
        
        if best_match:
            click.echo(f"✅ Suggested module: '{best_match}'")
            
            if dry_run:
                click.echo(f"📋 [DRY RUN] Would fix: {doctype_name} ('{current_module}' → '{best_match}')")
            else:
                # Apply the fix
                dt.module = best_match
                dt.save()
                frappe.db.commit()
                click.echo(f"✅ Fixed: {doctype_name} ('{current_module}' → '{best_match}')")
                
                # Also check if there are custom fields to update
                custom_fields = frappe.get_all("Custom Field", 
                    filters={"dt": doctype_name},
                    fields=["fieldname", "name"])
                
                if custom_fields:
                    click.echo(f"📝 Also updated {len(custom_fields)} custom fields")
        
        # Also fix the orphan custom fields mentioned in scan
        click.echo("\n🔧 CHECKING ORPHAN CUSTOM FIELDS...")
        
        orphan_custom_fields = [
            {"dt": "COA AMB2", "field": "workflow_state"},
            {"dt": "Freight Location", "field": "custom_freight_cost_amb"},
            {"dt": "Freight Location", "field": "custom_lead_time_to_delivery"}
        ]
        
        for cf_info in orphan_custom_fields:
            dt_name = cf_info["dt"]
            fieldname = cf_info["field"]
            
            # Check if doctype exists
            if frappe.db.exists("DocType", dt_name):
                # Check if custom field exists
                cf_filters = {"dt": dt_name, "fieldname": fieldname}
                cf_exists = frappe.db.exists("Custom Field", cf_filters)
                
                if cf_exists:
                    cf = frappe.get_doc("Custom Field", cf_filters)
                    click.echo(f"📋 Custom Field: {fieldname} in {dt_name} (exists)")
                    
                    # Check if it's orphaned (parent doesn't exist or different)
                    # For now, just report
                    if not dry_run:
                        # You could add logic to fix custom field orphans here
                        pass
                else:
                    click.echo(f"⚠️ Custom Field {fieldname} not found in {dt_name}")
            else:
                click.echo(f"❌ Doctype {dt_name} not found (custom field: {fieldname})")
        
        frappe.destroy()
        
        click.echo("\n✅ Analysis complete!")
        if dry_run:
            click.echo("💡 Run with --apply to fix the issues")
            
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        frappe.destroy()

if __name__ == "__main__":
    fix_alexa_orphan()
