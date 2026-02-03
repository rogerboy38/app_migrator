#!/usr/bin/env python3
"""
Quick fix for orphan modules identified in scan
"""

import click
import frappe

@click.command('fix-orphan-modules')
@click.option('--site', required=True, help='Site name')
@click.option('--apply', is_flag=True, help='Apply fixes')
def fix_orphan_modules(site, apply):
    """
    Fix orphan modules by reassigning doctypes to correct modules
    """
    
    dry_run = not apply
    
    click.echo(f"🔧 FIXING ORPHAN MODULES")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 50)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Define module remappings based on analysis
        module_remappings = {
            # Module in DB -> Should be (based on apps/modules.txt)
            "amb_w_tds2": "Amb W Tds2",  # Should match modules.txt
            "RND": "RND Nutrition",      # Likely should be RND Nutrition
            "RND Nutrition": "RND Nutrition",  # Already correct, just ensure
        }
        
        fixed_count = 0
        
        for old_module, new_module in module_remappings.items():
            # Check if old module exists in DB
            if not frappe.db.exists("Module Def", old_module):
                click.echo(f"⚠️ Module '{old_module}' not found in DB")
                continue
            
            # Get doctypes in this module
            doctypes = frappe.get_all("DocType", 
                filters={"module": old_module},
                fields=["name", "custom"])
            
            if not doctypes:
                click.echo(f"📋 Module '{old_module}' has no doctypes")
                continue
            
            click.echo(f"\n📋 Module '{old_module}' has {len(doctypes)} doctypes")
            
            # Check if new module exists
            if not frappe.db.exists("Module Def", new_module):
                click.echo(f"   ⚠️ Target module '{new_module}' not found")
                # Could create it, but for now skip
                continue
            
            # Apply changes
            for dt in doctypes:
                dt_name = dt["name"]
                if dry_run:
                    click.echo(f"   📝 Would move: {dt_name} → '{new_module}'")
                else:
                    try:
                        dt_doc = frappe.get_doc("DocType", dt_name)
                        dt_doc.module = new_module
                        dt_doc.save()
                        click.echo(f"   ✅ Moved: {dt_name} → '{new_module}'")
                        fixed_count += 1
                    except Exception as e:
                        click.echo(f"   ❌ Error moving {dt_name}: {e}")
            
            if not dry_run and doctypes:
                frappe.db.commit()
        
        # Also check for the Alexa User Mapping specific case
        click.echo(f"\n🔍 CHECKING SPECIFIC ORPHAN: Alexa User Mapping")
        doctype_name = "Alexa User Mapping"
        if frappe.db.exists("DocType", doctype_name):
            dt = frappe.get_doc("DocType", doctype_name)
            current_module = dt.module
            
            # Check if it's in a problematic module
            if current_module in ["Raven AI Agent", "Raven Ai Agent"]:
                # Find correct module
                possible_modules = ["Raven AI Agent", "Raven Ai Agent", "Raven", "Raven AI"]
                target_module = None
                
                for module in possible_modules:
                    if frappe.db.exists("Module Def", module):
                        target_module = module
                        break
                
                if target_module and target_module != current_module:
                    if dry_run:
                        click.echo(f"   📝 Would fix: {doctype_name} ('{current_module}' → '{target_module}')")
                    else:
                        dt.module = target_module
                        dt.save()
                        frappe.db.commit()
                        click.echo(f"   ✅ Fixed: {doctype_name} ('{current_module}' → '{target_module}')")
                        fixed_count += 1
        
        frappe.destroy()
        
        click.echo(f"\n📊 SUMMARY:")
        click.echo(f"   Fixed: {fixed_count} doctypes")
        
        if dry_run and fixed_count > 0:
            click.echo(f"\n💡 Run with --apply to fix {fixed_count} doctypes")
        
        click.echo("✅ Complete!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        frappe.destroy()

if __name__ == "__main__":
    fix_orphan_modules()
