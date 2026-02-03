#!/usr/bin/env python3
"""
Targeted fix for amb_w_tds2 orphan module issue
"""

import click
import frappe

@click.command('fix-amb-w-tds2')
@click.option('--site', required=True, help='Site name')
@click.option('--apply', is_flag=True, help='Apply fixes')
def fix_amb_w_tds2(site, apply):
    """
    Fix amb_w_tds2 orphan module by reassigning doctypes to correct module
    """
    
    dry_run = not apply
    
    click.echo(f"🔧 FIXING amb_w_tds2 ORPHAN MODULE")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 50)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Doctypes that are in wrong module (amb_w_tds2 instead of Amb W Tds2)
        problem_doctypes = ["AMB KPI Factors", "Container Selection"]
        
        fixed_count = 0
        
        for dt_name in problem_doctypes:
            if frappe.db.exists("DocType", dt_name):
                dt = frappe.get_doc("DocType", dt_name)
                current_module = dt.module
                
                # Check if it's in the wrong module
                if current_module == "amb_w_tds2":
                    target_module = "Amb W Tds2"
                    
                    if dry_run:
                        click.echo(f"📋 Would fix: {dt_name} ('{current_module}' → '{target_module}')")
                    else:
                        dt.module = target_module
                        dt.save()
                        frappe.db.commit()
                        click.echo(f"✅ Fixed: {dt_name} → '{target_module}'")
                        fixed_count += 1
                else:
                    click.echo(f"📋 {dt_name} already in correct module: '{current_module}'")
            else:
                click.echo(f"⚠️ Doctype not found: {dt_name}")
        
        # Also check for any other doctypes in amb_w_tds2 module
        click.echo(f"\n🔍 CHECKING FOR OTHER DOCTYPES IN 'amb_w_tds2' MODULE:")
        other_doctypes = frappe.get_all("DocType", 
            filters={"module": "amb_w_tds2"},
            fields=["name"])
        
        if other_doctypes:
            click.echo(f"   Found {len(other_doctypes)} doctypes in 'amb_w_tds2' module:")
            for dt in other_doctypes:
                click.echo(f"     • {dt['name']}")
                
                if dt['name'] not in problem_doctypes and not dry_run:
                    # Move them too
                    dt_doc = frappe.get_doc("DocType", dt['name'])
                    dt_doc.module = "Amb W Tds2"
                    dt_doc.save()
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
    fix_amb_w_tds2()
