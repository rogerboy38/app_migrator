#!/usr/bin/env python3
"""
Module Diagnostic Tool
Quick diagnostic for module naming and orphan issues
"""

import click
import frappe

@click.command('module-diagnostic')
@click.option('--site', required=True, help='Site name')
def module_diagnostic(site):
    """
    Quick diagnostic of module naming and orphan issues
    
    Example:
        bench app-migrator module-diagnostic --site mysite
    """
    
    click.echo(f"🔍 MODULE DIAGNOSTIC FOR: {site}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        # Get all modules
        modules = frappe.get_all("Module Def", fields=["name", "app_name"], order_by="name")
        
        click.echo(f"📊 Total modules: {len(modules)}")
        
        # Group by app
        app_modules = {}
        for module in modules:
            app = module.get("app_name", "Unknown")
            if app not in app_modules:
                app_modules[app] = []
            app_modules[app].append(module["name"])
        
        click.echo(f"📦 Modules across {len(app_modules)} apps")
        
        # Show modules with potential issues
        click.echo("\n⚠️ POTENTIAL ISSUES:")
        
        issues_found = False
        
        # 1. Check for inconsistent capitalization
        for module in modules:
            name = module["name"]
            
            # Check for "Ai" vs "AI" inconsistency
            if ' ai ' in name.lower():
                if ' Ai ' in name or name.endswith(' Ai'):
                    click.echo(f"   • Inconsistent 'Ai' in: {name}")
                    issues_found = True
            
            # Check for mixed case issues
            if name != name.title() and ' ' in name and not name.isupper():
                words = name.split()
                if any(word[0].islower() for word in words if len(word) > 1):
                    click.echo(f"   • Mixed case in: {name}")
                    issues_found = True
        
        # 2. Check for modules without doctypes
        modules_without_doctypes = []
        for module in modules:
            doctypes = frappe.get_all("DocType", 
                filters={"module": module["name"]},
                fields=["name"])
            
            if not doctypes:
                modules_without_doctypes.append(module["name"])
        
        if modules_without_doctypes:
            click.echo(f"\n   Modules without doctypes: {len(modules_without_doctypes)}")
            for module in modules_without_doctypes[:5]:
                click.echo(f"     • {module}")
            if len(modules_without_doctypes) > 5:
                click.echo(f"     ... and {len(modules_without_doctypes) - 5} more")
            issues_found = True
        
        if not issues_found:
            click.echo("   ✅ No obvious issues found")
        
        # 3. Show quick stats
        click.echo("\n📈 QUICK STATS:")
        
        # Count by naming pattern
        patterns = {
            "Title Case": 0,
            "snake_case": 0,
            "UPPERCASE": 0,
            "Mixed/Other": 0
        }
        
        for module in modules:
            name = module["name"]
            if ' ' in name and name.istitle():
                patterns["Title Case"] += 1
            elif '_' in name and name.islower():
                patterns["snake_case"] += 1
            elif name.isupper():
                patterns["UPPERCASE"] += 1
            else:
                patterns["Mixed/Other"] += 1
        
        for pattern, count in patterns.items():
            if count > 0:
                click.echo(f"   {pattern}: {count}")
        
        frappe.destroy()
        click.echo("\n✅ Diagnostic complete!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        frappe.destroy()

if __name__ == "__main__":
    module_diagnostic()
