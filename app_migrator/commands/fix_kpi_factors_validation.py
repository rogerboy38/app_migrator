#!/usr/bin/env python3
"""
Fix for AMB KPI Factors validation error
"""

import click
import frappe


@click.command('fix-kpi-factors')
@click.option('--site', required=True, help='Site name')
@click.option('--apply', is_flag=True, help='Apply fixes')
def fix_kpi_factors(site, apply):
    """
    Fix AMB KPI Factors validation error by checking/correcting field references
    """

    dry_run = not apply

    click.echo("🔧 FIXING AMB KPI FACTORS VALIDATION ERROR")
    click.echo(f"   Site: {site}")
    click.echo(f"   Mode: {'APPLY' if apply else 'DRY RUN'}")
    click.echo("=" * 50)

    try:
        frappe.init(site=site)
        frappe.connect()

        if not frappe.db.exists("DocType", "AMB KPI Factors"):
            click.echo("❌ Doctype 'AMB KPI Factors' not found")
            return

        dt = frappe.get_doc("DocType", dt_name="AMB KPI Factors")
        current_module = dt.module

        click.echo("📋 Doctype: AMB KPI Factors")
        click.echo(f"   Current module: {current_module}")

        # The error message says: "Options must be a valid DocType for field KPI Factors in row 19"
        # Let's check row 19 specifically
        click.echo("\n🔍 CHECKING ROW 19 SPECIFICALLY...")

        # Get the fields
        problem_field = None

        # Check standard fields
        for field in dt.fields:
            if field.idx == 19:  # Row 19 from error message
                problem_field = field
                break

        if problem_field:
            click.echo("   Found field at row 19:")
            click.echo(f"     Fieldname: {problem_field.fieldname}")
            click.echo(f"     Label: {problem_field.label}")
            click.echo(f"     Fieldtype: {problem_field.fieldtype}")
            click.echo(f"     Options: {problem_field.options}")

            # Check if the referenced doctype exists
            if problem_field.options:
                doctype_exists = frappe.db.exists("DocType", problem_field.options)
                click.echo(f"     Referenced doctype exists: {doctype_exists}")

                if not doctype_exists:
                    click.echo(f"     ⚠️ Referenced doctype '{problem_field.options}' doesn't exist!")

                    # Try to find similar doctypes
                    similar_doctypes = frappe.get_all("DocType",
                        filters={"name": ["like", f"%{problem_field.options}%"]},
                        fields=["name"])

                    if similar_doctypes:
                        click.echo("     Similar doctypes found:")
                        for similar in similar_doctypes:
                            click.echo(f"       • {similar['name']}")

                        # Suggest fix
                        if not dry_run and similar_doctypes:
                            # Update to first similar doctype
                            new_options = similar_doctypes[0]['name']
                            problem_field.options = new_options
                            dt.save()
                            frappe.db.commit()
                            click.echo(f"     ✅ Updated options to: {new_options}")
        else:
            click.echo("   ⚠️ Could not find field at row 19")
            click.echo("   Checking all fields for 'KPI Factors' reference...")

            # Search for field with "KPI Factors" in name
            for field in dt.fields:
                if "kpi" in field.fieldname.lower() or "kpi" in (field.label or "").lower():
                    click.echo(f"     Field: {field.fieldname} (row {field.idx})")
                    click.echo(f"       Label: {field.label}")
                    click.echo(f"       Options: {field.options}")

        # Also fix the module assignment while we're at it
        click.echo("\n🔧 FIXING MODULE ASSIGNMENT...")

        if current_module == "amb_w_tds2":
            target_module = "Amb W Tds2"

            if dry_run:
                click.echo(f"📋 Would reassign: AMB KPI Factors → '{target_module}'")
            else:
                dt.module = target_module
                dt.save()
                frappe.db.commit()
                click.echo(f"✅ Reassigned: AMB KPI Factors → '{target_module}'")

        # Also fix Container Selection if needed
        click.echo("\n🔧 CHECKING CONTAINER SELECTION...")

        if frappe.db.exists("DocType", "Container Selection"):
            cs_dt = frappe.get_doc("DocType", "Container Selection")

            if cs_dt.module == "amb_w_tds2":
                target_module = "Amb W Tds2"

                if dry_run:
                    click.echo(f"📋 Would reassign: Container Selection → '{target_module}'")
                else:
                    cs_dt.module = target_module
                    cs_dt.save()
                    frappe.db.commit()
                    click.echo(f"✅ Reassigned: Container Selection → '{target_module}'")

        frappe.destroy()

        click.echo("\n✅ Fix complete!")
        if dry_run:
            click.echo("💡 Run with --apply to fix the validation error and module assignment")

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        frappe.destroy()

if __name__ == "__main__":
    fix_kpi_factors()
