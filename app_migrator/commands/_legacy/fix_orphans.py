"""[DEPRECATED] fix-orphans command — extracted to _legacy/ in T1.8.5.

This command emits a deprecation banner pointing users to
'orphans --fix --apply'. Scheduled for removal in v11.

Lives under _legacy/ to make the v11 deletion an atomic dir-rm.
"""

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
@click.command('app-migrator-fix-orphans')
@click.option('--site', required=True, help='Site name')
@click.option('--target-module', default=None, help='Target module for orphans')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_fix_orphans(context, site, target_module, dry_run):
    """[DEPRECATED] Fix orphan doctypes — use 'orphans --fix --apply' instead (will be removed in v11)"""
    click.echo("⚠️  DEPRECATED: 'fix-orphans' is deprecated and will be removed in v11.")
    click.echo("   Use 'bench app-migrator orphans --fix --apply' instead.")
    click.echo("")
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIXING ORPHAN DOCTYPES [{mode}]")
    print(f"   Site: {site}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    # Find orphan doctypes - those with empty/null module or module not matching any app
    installed_apps = frappe.get_installed_apps()

    # Get all modules from installed apps
    valid_modules = set()
    for app in installed_apps:
        try:
            modules = frappe.get_all("Module Def", filters={"app_name": app}, pluck="name")
            valid_modules.update(modules)
        except Exception:
            pass

    # Also add app names as valid modules (some doctypes use app name as module)
    valid_modules.update(installed_apps)

    # Find orphans
    orphans = []

    # 1. DocTypes with empty/null module
    empty_module = frappe.get_all("DocType",
        filters=[["module", "in", ["", None]]],
        fields=["name", "module", "custom"])
    orphans.extend([{"name": d.name, "module": d.module or "(empty)", "type": "empty_module", "custom": d.custom} for d in empty_module])

    # 2. DocTypes with module not in valid_modules (excluding custom doctypes)
    all_doctypes = frappe.get_all("DocType",
        filters={"custom": 0},
        fields=["name", "module"])

    for dt in all_doctypes:
        if dt.module and dt.module not in valid_modules:
            orphans.append({"name": dt.name, "module": dt.module, "type": "invalid_module", "custom": 0})

    # 3. Custom Fields with orphan dt
    orphan_custom_fields = frappe.db.sql("""
        SELECT cf.name, cf.dt, cf.fieldname
        FROM `tabCustom Field` cf
        LEFT JOIN `tabDocType` dt ON cf.dt = dt.name
        WHERE dt.name IS NULL
    """, as_dict=True)

    print("\n📊 ORPHAN ANALYSIS:")
    print(f"   DocTypes with empty module: {len([o for o in orphans if o['type'] == 'empty_module'])}")
    print(f"   DocTypes with invalid module: {len([o for o in orphans if o['type'] == 'invalid_module'])}")
    print(f"   Orphan Custom Fields: {len(orphan_custom_fields)}")

    if orphans:
        print(f"\n⚠️ ORPHAN DOCTYPES ({len(orphans)}):")
        for o in orphans[:20]:  # Show first 20
            print(f"   • {o['name']:40} module='{o['module']}' ({o['type']})")
        if len(orphans) > 20:
            print(f"   ... and {len(orphans) - 20} more")

    if orphan_custom_fields:
        print(f"\n⚠️ ORPHAN CUSTOM FIELDS ({len(orphan_custom_fields)}):")
        for cf in orphan_custom_fields[:10]:
            print(f"   • {cf['name']} → dt='{cf['dt']}'")
        if len(orphan_custom_fields) > 10:
            print(f"   ... and {len(orphan_custom_fields) - 10} more")

    if not dry_run and target_module:
        print(f"\n🔧 APPLYING FIXES (target module: {target_module})...")
        fixed = 0

        for o in orphans:
            # Fix both empty_module and invalid_module types
            frappe.db.sql("""
                UPDATE `tabDocType` SET module = %s WHERE name = %s
            """, (target_module, o['name']))
            print(f"   📝 Fixed: {o['name']} → {target_module}")
            fixed += 1

        # Delete orphan custom fields
        for cf in orphan_custom_fields:
            frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name = %s", cf['name'])

        frappe.db.commit()
        print(f"\n   ✅ Fixed {fixed} doctypes")
        print(f"   ✅ Deleted {len(orphan_custom_fields)} orphan custom fields")
    elif not dry_run and not target_module:
        print("\n❌ --target-module required when using --apply")
    else:
        print("\n📋 Run with --apply --target-module <module> to fix")

    frappe.db.close()

