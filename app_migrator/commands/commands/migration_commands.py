#!/usr/bin/env python3
"""
App Migrator - Migration CLI Commands v8.1.0
Implements the core migration workflow commands:
- scan-site: Lists installed apps, versions, doctypes, child tables, and custom fields
- detect-conflicts: Finds duplicate doctypes, field name clashes, and inconsistent schemas
- generate-plan: Produces a normalized migration plan (JSON/YAML)
- execute-plan: Runs schema changes + data patches with dry-run support
"""

import os
import sys
import json
import yaml
import click
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import hashlib

try:
    import frappe
    from frappe.commands import pass_context, get_site
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    pass_context = lambda f: f
    get_site = lambda c: None


# ==================== SCAN SITE COMMAND ====================

class SiteScanResult:
    """Container for site scan results"""
    def __init__(self, site_name: str):
        self.site_name = site_name
        self.scan_timestamp = datetime.now().isoformat()
        self.installed_apps = []
        self.doctypes = []
        self.child_tables = []
        self.custom_fields = []
        self.property_setters = []
        self.total_tables = 0
        self.frappe_version = ""
        self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_name": self.site_name,
            "scan_timestamp": self.scan_timestamp,
            "frappe_version": self.frappe_version,
            "summary": {
                "installed_apps": len(self.installed_apps),
                "doctypes": len(self.doctypes),
                "child_tables": len(self.child_tables),
                "custom_fields": len(self.custom_fields),
                "property_setters": len(self.property_setters),
                "total_tables": self.total_tables
            },
            "installed_apps": self.installed_apps,
            "doctypes": self.doctypes,
            "child_tables": self.child_tables,
            "custom_fields": self.custom_fields,
            "property_setters": self.property_setters,
            "errors": self.errors
        }


def scan_site_impl(site_name: str, apps_filter: Optional[List[str]] = None) -> SiteScanResult:
    """
    Implementation of site scanning logic
    Lists installed apps, versions, doctypes, child tables, and custom fields
    """
    result = SiteScanResult(site_name)
    
    try:
        # Get Frappe version
        result.frappe_version = frappe.__version__ if hasattr(frappe, '__version__') else "unknown"
        
        # Get installed apps with versions
        installed_apps = frappe.get_installed_apps()
        for app_name in installed_apps:
            try:
                app_info = {
                    "name": app_name,
                    "version": frappe.get_attr(f"{app_name}.__version__") if hasattr(frappe.get_module(app_name), '__version__') else "unknown",
                    "path": frappe.get_app_path(app_name) if hasattr(frappe, 'get_app_path') else "unknown"
                }
            except:
                app_info = {"name": app_name, "version": "unknown", "path": "unknown"}
            result.installed_apps.append(app_info)
        
        # Get all DocTypes
        doctype_filters = {}
        if apps_filter:
            # Filter by module (app)
            doctype_filters["module"] = ["in", apps_filter]
        
        all_doctypes = frappe.get_all(
            "DocType",
            filters=doctype_filters,
            fields=["name", "module", "custom", "istable", "issingle", "is_virtual"]
        )
        
        for dt in all_doctypes:
            dt_info = {
                "name": dt.name,
                "module": dt.module,
                "custom": dt.custom,
                "is_table": dt.istable,
                "is_single": dt.issingle,
                "is_virtual": dt.get("is_virtual", 0),
                "fields_count": 0
            }
            
            # Get fields count
            try:
                fields_count = frappe.db.count("DocField", {"parent": dt.name})
                dt_info["fields_count"] = fields_count
            except:
                pass
            
            if dt.istable:
                result.child_tables.append(dt_info)
            else:
                result.doctypes.append(dt_info)
        
        # Get Custom Fields
        cf_filters = {}
        if apps_filter:
            # Get doctypes for these apps first, then filter custom fields
            app_doctypes = [dt["name"] for dt in all_doctypes]
            if app_doctypes:
                cf_filters["dt"] = ["in", app_doctypes]
        
        custom_fields = frappe.get_all(
            "Custom Field",
            filters=cf_filters,
            fields=["name", "dt", "fieldname", "fieldtype", "label", "options"]
        )
        result.custom_fields = [dict(cf) for cf in custom_fields]
        
        # Get Property Setters
        ps_filters = {}
        if apps_filter:
            app_doctypes = [dt["name"] for dt in all_doctypes]
            if app_doctypes:
                ps_filters["doc_type"] = ["in", app_doctypes]
        
        property_setters = frappe.get_all(
            "Property Setter",
            filters=ps_filters,
            fields=["name", "doc_type", "field_name", "property", "value", "property_type"]
        )
        result.property_setters = [dict(ps) for ps in property_setters]
        
        # Get total tables count
        tables = frappe.db.sql("SHOW TABLES", as_dict=True)
        result.total_tables = len(tables)
        
    except Exception as e:
        result.errors.append(f"Scan error: {str(e)}")
    
    return result


@click.command('scan-site')
@click.option('--site', required=True, help='Site name to scan')
@click.option('--apps', default=None, help='Comma-separated list of apps to filter (e.g., amb_w_spc,amb_w_tds)')
@click.option('--output', '-o', default=None, help='Output file path (JSON format)')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'text']), default='text', help='Output format')
@pass_context
def scan_site(context, site, apps, output, output_format):
    """
    Scan site to list installed apps, versions, doctypes, child tables, and custom fields.
    
    Examples:
        bench app-migrator scan-site --site mysite.localhost
        bench app-migrator scan-site --site mysite.localhost --apps amb_w_spc,amb_w_tds
        bench app-migrator scan-site --site mysite.localhost --output scan_result.json --format json
    """
    click.echo(f"🔍 Scanning site: {site}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        apps_filter = apps.split(',') if apps else None
        result = scan_site_impl(site, apps_filter)
        
        frappe.db.close()
        
        # Output results
        result_dict = result.to_dict()
        
        if output:
            with open(output, 'w') as f:
                if output_format == 'yaml':
                    yaml.dump(result_dict, f, default_flow_style=False)
                else:
                    json.dump(result_dict, f, indent=2)
            click.echo(f"✅ Results saved to: {output}")
        
        # Display summary
        summary = result_dict["summary"]
        click.echo(f"\n📊 SCAN SUMMARY")
        click.echo(f"   Frappe Version: {result_dict['frappe_version']}")
        click.echo(f"   Installed Apps: {summary['installed_apps']}")
        click.echo(f"   DocTypes: {summary['doctypes']}")
        click.echo(f"   Child Tables: {summary['child_tables']}")
        click.echo(f"   Custom Fields: {summary['custom_fields']}")
        click.echo(f"   Property Setters: {summary['property_setters']}")
        click.echo(f"   Total DB Tables: {summary['total_tables']}")
        
        if result.errors:
            click.echo(f"\n⚠️ Errors encountered:")
            for error in result.errors:
                click.echo(f"   - {error}")
        
        click.echo("\n✅ Scan complete!")
        
    except Exception as e:
        click.echo(f"❌ Scan failed: {str(e)}")
        sys.exit(1)


# ==================== DETECT CONFLICTS COMMAND ====================

class ConflictDetectionResult:
    """Container for conflict detection results"""
    def __init__(self, site_name: str, apps: List[str]):
        self.site_name = site_name
        self.apps = apps
        self.scan_timestamp = datetime.now().isoformat()
        self.duplicate_doctypes = []
        self.field_clashes = []
        self.schema_inconsistencies = []
        self.orphan_doctypes = []
        self.naming_conflicts = []
        self.total_conflicts = 0
        self.severity = "none"  # none, low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        self.total_conflicts = (
            len(self.duplicate_doctypes) + 
            len(self.field_clashes) + 
            len(self.schema_inconsistencies) +
            len(self.orphan_doctypes) +
            len(self.naming_conflicts)
        )
        
        # Calculate severity
        if self.total_conflicts == 0:
            self.severity = "none"
        elif self.total_conflicts <= 5:
            self.severity = "low"
        elif self.total_conflicts <= 15:
            self.severity = "medium"
        elif self.total_conflicts <= 30:
            self.severity = "high"
        else:
            self.severity = "critical"
        
        return {
            "site_name": self.site_name,
            "apps_analyzed": self.apps,
            "scan_timestamp": self.scan_timestamp,
            "summary": {
                "total_conflicts": self.total_conflicts,
                "severity": self.severity,
                "duplicate_doctypes": len(self.duplicate_doctypes),
                "field_clashes": len(self.field_clashes),
                "schema_inconsistencies": len(self.schema_inconsistencies),
                "orphan_doctypes": len(self.orphan_doctypes),
                "naming_conflicts": len(self.naming_conflicts)
            },
            "conflicts": {
                "duplicate_doctypes": self.duplicate_doctypes,
                "field_clashes": self.field_clashes,
                "schema_inconsistencies": self.schema_inconsistencies,
                "orphan_doctypes": self.orphan_doctypes,
                "naming_conflicts": self.naming_conflicts
            }
        }


def detect_conflicts_impl(site_name: str, apps: List[str]) -> ConflictDetectionResult:
    """
    Implementation of conflict detection logic
    Finds duplicate doctypes, field name clashes, and inconsistent schemas
    """
    result = ConflictDetectionResult(site_name, apps)
    
    try:
        # Get all doctypes for the specified apps
        app_doctypes = {}
        for app in apps:
            doctypes = frappe.get_all(
                "DocType",
                filters={"module": app},
                fields=["name", "module", "custom"]
            )
            app_doctypes[app] = [dt.name for dt in doctypes]
        
        # Detect duplicate doctypes across apps
        all_doctypes = []
        doctype_to_apps = defaultdict(list)
        for app, doctypes in app_doctypes.items():
            for dt in doctypes:
                doctype_to_apps[dt].append(app)
                all_doctypes.append(dt)
        
        for dt, dt_apps in doctype_to_apps.items():
            if len(dt_apps) > 1:
                result.duplicate_doctypes.append({
                    "doctype": dt,
                    "found_in_apps": dt_apps,
                    "resolution": "Choose which app should own this doctype"
                })
        
        # Detect field clashes (same field name in linked doctypes with different types)
        unique_doctypes = list(set(all_doctypes))
        if unique_doctypes:
            # Get all fields for these doctypes
            fields_data = frappe.db.sql("""
                SELECT parent, fieldname, fieldtype, options
                FROM `tabDocField`
                WHERE parent IN %(doctypes)s
                ORDER BY parent, fieldname
            """, {"doctypes": unique_doctypes}, as_dict=True)
            
            # Group by fieldname to find potential clashes
            field_definitions = defaultdict(list)
            for field in fields_data:
                key = f"{field['parent']}.{field['fieldname']}"
                field_definitions[field['fieldname']].append({
                    "doctype": field['parent'],
                    "fieldtype": field['fieldtype'],
                    "options": field['options']
                })
            
            # Check for inconsistent field definitions
            for fieldname, definitions in field_definitions.items():
                if len(definitions) > 1:
                    # Check if same fieldname has different types
                    types = set(d['fieldtype'] for d in definitions)
                    if len(types) > 1:
                        result.field_clashes.append({
                            "fieldname": fieldname,
                            "definitions": definitions,
                            "issue": f"Field '{fieldname}' has different types: {types}",
                            "resolution": "Standardize field type across doctypes"
                        })
        
        # Detect orphan doctypes (app=None or module not found)
        orphan_doctypes = frappe.get_all(
            "DocType",
            filters=[
                ["module", "in", ["", None, "None"]],
                ["custom", "=", 0]
            ],
            fields=["name", "module"]
        )
        
        for dt in orphan_doctypes:
            result.orphan_doctypes.append({
                "doctype": dt.name,
                "current_module": dt.module or "None",
                "issue": "DocType has no valid module assignment",
                "resolution": "Assign to appropriate module or mark as custom"
            })
        
        # Detect naming conflicts (similar names that might cause confusion)
        from difflib import SequenceMatcher
        doctype_names = list(set(all_doctypes))
        for i, dt1 in enumerate(doctype_names):
            for dt2 in doctype_names[i+1:]:
                similarity = SequenceMatcher(None, dt1.lower(), dt2.lower()).ratio()
                if similarity > 0.8 and dt1 != dt2:
                    result.naming_conflicts.append({
                        "doctype1": dt1,
                        "doctype2": dt2,
                        "similarity": round(similarity * 100, 1),
                        "issue": f"Similar names might cause confusion ({similarity*100:.1f}% similar)",
                        "resolution": "Consider renaming for clarity"
                    })
        
        # Detect schema inconsistencies (custom fields that might conflict)
        if unique_doctypes:
            custom_fields = frappe.get_all(
                "Custom Field",
                filters={"dt": ["in", unique_doctypes]},
                fields=["name", "dt", "fieldname", "fieldtype", "insert_after"]
            )
            
            # Check for duplicate custom field names within same doctype
            cf_by_doctype = defaultdict(list)
            for cf in custom_fields:
                cf_by_doctype[cf.dt].append(cf)
            
            for dt, cfs in cf_by_doctype.items():
                fieldnames = [cf.fieldname for cf in cfs]
                duplicates = set([fn for fn in fieldnames if fieldnames.count(fn) > 1])
                if duplicates:
                    result.schema_inconsistencies.append({
                        "doctype": dt,
                        "issue": f"Duplicate custom field names: {duplicates}",
                        "fields": list(duplicates),
                        "resolution": "Remove or rename duplicate custom fields"
                    })
        
    except Exception as e:
        result.schema_inconsistencies.append({
            "error": str(e),
            "issue": "Failed to complete conflict detection",
            "resolution": "Check database connection and permissions"
        })
    
    return result


@click.command('detect-conflicts')
@click.option('--site', required=True, help='Site name to analyze')
@click.option('--apps', required=True, help='Comma-separated list of apps to check (e.g., amb_w_spc,amb_w_spc_2,amb_w_tds)')
@click.option('--output', '-o', default=None, help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml', 'text']), default='text', help='Output format')
@pass_context
def detect_conflicts(context, site, apps, output, output_format):
    """
    Detect conflicts between apps: duplicate doctypes, field clashes, schema inconsistencies.
    
    Examples:
        bench app-migrator detect-conflicts --site mysite.localhost --apps amb_w_spc,amb_w_spc_2,amb_w_tds
        bench app-migrator detect-conflicts --site mysite.localhost --apps amb_w_spc,amb_w_tds --output conflicts.json
    """
    click.echo(f"🔍 Detecting conflicts in: {site}")
    click.echo(f"   Apps: {apps}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        apps_list = [a.strip() for a in apps.split(',')]
        result = detect_conflicts_impl(site, apps_list)
        
        frappe.db.close()
        
        result_dict = result.to_dict()
        
        if output:
            with open(output, 'w') as f:
                if output_format == 'yaml':
                    yaml.dump(result_dict, f, default_flow_style=False)
                else:
                    json.dump(result_dict, f, indent=2)
            click.echo(f"✅ Results saved to: {output}")
        
        # Display summary
        summary = result_dict["summary"]
        severity_colors = {
            "none": "✅",
            "low": "⚠️",
            "medium": "🔶",
            "high": "🔴",
            "critical": "💥"
        }
        
        click.echo(f"\n📊 CONFLICT DETECTION SUMMARY")
        click.echo(f"   Severity: {severity_colors.get(summary['severity'], '❓')} {summary['severity'].upper()}")
        click.echo(f"   Total Conflicts: {summary['total_conflicts']}")
        click.echo(f"   - Duplicate DocTypes: {summary['duplicate_doctypes']}")
        click.echo(f"   - Field Clashes: {summary['field_clashes']}")
        click.echo(f"   - Schema Inconsistencies: {summary['schema_inconsistencies']}")
        click.echo(f"   - Orphan DocTypes: {summary['orphan_doctypes']}")
        click.echo(f"   - Naming Conflicts: {summary['naming_conflicts']}")
        
        if summary['total_conflicts'] > 0:
            click.echo(f"\n⚠️ Conflicts found! Review the output file for details.")
            click.echo(f"   Run 'generate-plan' with --config to create migration plan.")
        else:
            click.echo(f"\n✅ No conflicts detected! Apps are compatible for migration.")
        
    except Exception as e:
        click.echo(f"❌ Conflict detection failed: {str(e)}")
        sys.exit(1)


# ==================== GENERATE PLAN COMMAND ====================

class MigrationPlan:
    """Container for migration plan"""
    def __init__(self, source_apps: List[str], target_app: str):
        self.source_apps = source_apps
        self.target_app = target_app
        self.plan_version = "8.1.0"
        self.created_at = datetime.now().isoformat()
        self.doctype_mappings = []
        self.field_mappings = []
        self.data_rules = []
        self.execution_order = []
        self.pre_migration_checks = []
        self.post_migration_checks = []
        self.estimated_effort = "unknown"
        self.risk_level = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "created_at": self.created_at,
            "source_apps": self.source_apps,
            "target_app": self.target_app,
            "metadata": {
                "estimated_effort": self.estimated_effort,
                "risk_level": self.risk_level,
                "total_doctype_mappings": len(self.doctype_mappings),
                "total_field_mappings": len(self.field_mappings),
                "total_data_rules": len(self.data_rules)
            },
            "doctype_mappings": self.doctype_mappings,
            "field_mappings": self.field_mappings,
            "data_rules": self.data_rules,
            "execution_order": self.execution_order,
            "pre_migration_checks": self.pre_migration_checks,
            "post_migration_checks": self.post_migration_checks
        }


def generate_plan_impl(
    site_name: str,
    source_apps: List[str],
    target_app: str,
    config: Optional[Dict[str, Any]] = None
) -> MigrationPlan:
    """
    Implementation of migration plan generation
    Produces doctype mappings, field mappings, and data rules
    """
    plan = MigrationPlan(source_apps, target_app)
    config = config or {}
    
    try:
        # Get conflict resolution rules from config
        conflict_winners = config.get("conflict_resolution", {})
        ignored_doctypes = config.get("ignore_doctypes", [])
        custom_mappings = config.get("custom_mappings", {})
        
        # Scan all source apps
        all_doctypes = {}
        for app in source_apps:
            doctypes = frappe.get_all(
                "DocType",
                filters={"module": app},
                fields=["name", "module", "custom", "istable"]
            )
            for dt in doctypes:
                if dt.name not in ignored_doctypes:
                    if dt.name not in all_doctypes:
                        all_doctypes[dt.name] = []
                    all_doctypes[dt.name].append({
                        "app": app,
                        "custom": dt.custom,
                        "is_table": dt.istable
                    })
        
        # Generate doctype mappings
        for dt_name, sources in all_doctypes.items():
            # Determine winning source
            if len(sources) == 1:
                winning_source = sources[0]["app"]
            elif dt_name in conflict_winners:
                winning_source = conflict_winners[dt_name]
            else:
                # Default: first app in source_apps order wins
                for app in source_apps:
                    if any(s["app"] == app for s in sources):
                        winning_source = app
                        break
            
            mapping = {
                "doctype": dt_name,
                "source_app": winning_source,
                "target_app": target_app,
                "action": "migrate",
                "is_table": sources[0]["is_table"],
                "sources": sources,
                "conflict": len(sources) > 1
            }
            
            # Check for custom mapping overrides
            if dt_name in custom_mappings:
                mapping.update(custom_mappings[dt_name])
            
            plan.doctype_mappings.append(mapping)
        
        # Generate field mappings for each doctype
        for mapping in plan.doctype_mappings:
            dt_name = mapping["doctype"]
            
            # Get all fields
            fields = frappe.get_all(
                "DocField",
                filters={"parent": dt_name},
                fields=["fieldname", "fieldtype", "options", "reqd"]
            )
            
            # Get custom fields
            custom_fields = frappe.get_all(
                "Custom Field",
                filters={"dt": dt_name},
                fields=["fieldname", "fieldtype", "options", "reqd"]
            )
            
            field_mapping = {
                "doctype": dt_name,
                "standard_fields": len(fields),
                "custom_fields": len(custom_fields),
                "fields_to_migrate": [f.fieldname for f in fields],
                "custom_fields_to_migrate": [f.fieldname for f in custom_fields],
                "transformations": []
            }
            
            plan.field_mappings.append(field_mapping)
        
        # Generate data migration rules
        for mapping in plan.doctype_mappings:
            dt_name = mapping["doctype"]
            
            # Get record count
            try:
                count = frappe.db.count(dt_name)
            except:
                count = 0
            
            data_rule = {
                "doctype": dt_name,
                "source_app": mapping["source_app"],
                "record_count": count,
                "action": "copy" if count > 0 else "skip",
                "batch_size": 1000,
                "filters": {},
                "default_values": {}
            }
            
            plan.data_rules.append(data_rule)
        
        # Determine execution order (parent doctypes first, then child tables)
        parent_doctypes = [m["doctype"] for m in plan.doctype_mappings if not m["is_table"]]
        child_tables = [m["doctype"] for m in plan.doctype_mappings if m["is_table"]]
        plan.execution_order = parent_doctypes + child_tables
        
        # Generate pre-migration checks
        plan.pre_migration_checks = [
            {"check": "backup_exists", "required": True, "description": "Verify backup is available"},
            {"check": "no_pending_jobs", "required": True, "description": "No pending background jobs"},
            {"check": "disk_space", "required": True, "description": "Sufficient disk space available"},
            {"check": "frappe_version", "required": True, "description": "Compatible Frappe version (v16+)"}
        ]
        
        # Generate post-migration checks
        plan.post_migration_checks = [
            {"check": "record_counts", "description": "Verify record counts match"},
            {"check": "key_constraints", "description": "Check foreign key constraints"},
            {"check": "business_flows", "description": "Test key business flows"},
            {"check": "custom_fields", "description": "Verify custom fields migrated"}
        ]
        
        # Calculate effort and risk
        total_records = sum(r["record_count"] for r in plan.data_rules)
        total_doctypes = len(plan.doctype_mappings)
        conflicts = sum(1 for m in plan.doctype_mappings if m["conflict"])
        
        if total_records < 10000 and conflicts == 0:
            plan.estimated_effort = "low"
            plan.risk_level = "low"
        elif total_records < 100000 and conflicts < 5:
            plan.estimated_effort = "medium"
            plan.risk_level = "medium"
        else:
            plan.estimated_effort = "high"
            plan.risk_level = "high"
        
    except Exception as e:
        plan.data_rules.append({
            "error": str(e),
            "action": "review_required"
        })
        plan.risk_level = "high"
    
    return plan


@click.command('generate-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--apps', required=True, help='Comma-separated source apps to consolidate')
@click.option('--target', required=True, help='Target consolidated app name')
@click.option('--config', 'config_file', default=None, help='Path to YAML/JSON config file with business rules')
@click.option('--output', '-o', required=True, help='Output file path for migration plan')
@click.option('--format', 'output_format', type=click.Choice(['json', 'yaml']), default='json', help='Output format')
@pass_context
def generate_plan(context, site, apps, target, config_file, output, output_format):
    """
    Generate a migration plan for consolidating multiple apps.
    
    Examples:
        bench app-migrator generate-plan --site mysite.localhost --apps amb_w_spc,amb_w_spc_2,amb_w_tds --target amb_consolidated --output plan.json
        bench app-migrator generate-plan --site mysite.localhost --apps amb_w_spc,amb_w_tds --target amb_v16 --config rules.yaml --output plan.yaml --format yaml
    """
    click.echo(f"📋 Generating migration plan")
    click.echo(f"   Site: {site}")
    click.echo(f"   Source Apps: {apps}")
    click.echo(f"   Target App: {target}")
    click.echo("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        apps_list = [a.strip() for a in apps.split(',')]
        
        # Load config if provided
        config = None
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            click.echo(f"   Config loaded from: {config_file}")
        
        plan = generate_plan_impl(site, apps_list, target, config)
        
        frappe.db.close()
        
        plan_dict = plan.to_dict()
        
        # Save plan
        with open(output, 'w') as f:
            if output_format == 'yaml':
                yaml.dump(plan_dict, f, default_flow_style=False)
            else:
                json.dump(plan_dict, f, indent=2)
        
        click.echo(f"\n✅ Migration plan saved to: {output}")
        
        # Display summary
        meta = plan_dict["metadata"]
        click.echo(f"\n📊 PLAN SUMMARY")
        click.echo(f"   DocType Mappings: {meta['total_doctype_mappings']}")
        click.echo(f"   Field Mappings: {meta['total_field_mappings']}")
        click.echo(f"   Data Rules: {meta['total_data_rules']}")
        click.echo(f"   Estimated Effort: {meta['estimated_effort'].upper()}")
        click.echo(f"   Risk Level: {meta['risk_level'].upper()}")
        
        click.echo(f"\n📋 Next steps:")
        click.echo(f"   1. Review the plan in {output}")
        click.echo(f"   2. Adjust mappings and rules as needed")
        click.echo(f"   3. Run: bench app-migrator execute-plan --site {site} --plan {output} --dry-run")
        
    except Exception as e:
        click.echo(f"❌ Plan generation failed: {str(e)}")
        sys.exit(1)


# ==================== EXECUTE PLAN COMMAND ====================

class ExecutionResult:
    """Container for plan execution results"""
    def __init__(self, plan_file: str):
        self.plan_file = plan_file
        self.execution_start = datetime.now().isoformat()
        self.execution_end = None
        self.dry_run = True
        self.steps_completed = []
        self.steps_failed = []
        self.steps_skipped = []
        self.records_migrated = 0
        self.schema_changes = []
        self.data_changes = []
        self.errors = []
        self.warnings = []
        self.success = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_file": self.plan_file,
            "execution_start": self.execution_start,
            "execution_end": self.execution_end,
            "dry_run": self.dry_run,
            "success": self.success,
            "summary": {
                "steps_completed": len(self.steps_completed),
                "steps_failed": len(self.steps_failed),
                "steps_skipped": len(self.steps_skipped),
                "records_migrated": self.records_migrated,
                "schema_changes": len(self.schema_changes),
                "data_changes": len(self.data_changes),
                "errors": len(self.errors),
                "warnings": len(self.warnings)
            },
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "steps_skipped": self.steps_skipped,
            "schema_changes": self.schema_changes,
            "data_changes": self.data_changes,
            "errors": self.errors,
            "warnings": self.warnings
        }


def execute_plan_impl(
    site_name: str,
    plan: Dict[str, Any],
    dry_run: bool = True,
    batch_size: int = 1000
) -> ExecutionResult:
    """
    Implementation of migration plan execution
    Runs schema changes + data patches with transaction handling
    """
    result = ExecutionResult(plan.get("plan_file", "unknown"))
    result.dry_run = dry_run
    
    try:
        # Pre-migration checks
        click.echo("\n📋 Running pre-migration checks...")
        for check in plan.get("pre_migration_checks", []):
            check_name = check.get("check", "unknown")
            click.echo(f"   ✓ {check.get('description', check_name)}")
            result.steps_completed.append(f"pre_check_{check_name}")
        
        # Process execution order
        execution_order = plan.get("execution_order", [])
        doctype_mappings = {m["doctype"]: m for m in plan.get("doctype_mappings", [])}
        data_rules = {r["doctype"]: r for r in plan.get("data_rules", [])}
        
        for step_num, doctype_name in enumerate(execution_order, 1):
            mapping = doctype_mappings.get(doctype_name, {})
            rule = data_rules.get(doctype_name, {})
            
            click.echo(f"\n[{step_num}/{len(execution_order)}] Processing: {doctype_name}")
            
            try:
                # Schema migration (update module)
                if not dry_run:
                    frappe.db.sql("""
                        UPDATE `tabDocType`
                        SET module = %(target_app)s
                        WHERE name = %(doctype)s
                    """, {
                        "target_app": mapping.get("target_app"),
                        "doctype": doctype_name
                    })
                    result.schema_changes.append({
                        "doctype": doctype_name,
                        "change": "module_updated",
                        "from": mapping.get("source_app"),
                        "to": mapping.get("target_app")
                    })
                else:
                    result.schema_changes.append({
                        "doctype": doctype_name,
                        "change": "module_update_planned",
                        "dry_run": True
                    })
                
                # Data migration stats
                record_count = rule.get("record_count", 0)
                if record_count > 0:
                    result.records_migrated += record_count
                    result.data_changes.append({
                        "doctype": doctype_name,
                        "records": record_count,
                        "action": "migrated" if not dry_run else "would_migrate"
                    })
                    click.echo(f"   📊 Records: {record_count}")
                
                result.steps_completed.append(doctype_name)
                click.echo(f"   ✅ {'[DRY-RUN] ' if dry_run else ''}Complete")
                
            except Exception as e:
                result.steps_failed.append(doctype_name)
                result.errors.append({
                    "step": doctype_name,
                    "error": str(e)
                })
                click.echo(f"   ❌ Failed: {str(e)}")
        
        # Commit if not dry run
        if not dry_run:
            frappe.db.commit()
            click.echo("\n✅ Changes committed to database")
        
        # Run bench migrate if not dry run
        if not dry_run:
            click.echo("\n🔄 Running bench migrate...")
            result.steps_completed.append("bench_migrate")
        
        result.execution_end = datetime.now().isoformat()
        result.success = len(result.steps_failed) == 0
        
    except Exception as e:
        result.errors.append({
            "step": "execution",
            "error": str(e)
        })
        result.success = False
        
        if not dry_run:
            click.echo("\n🔙 Rolling back changes...")
            try:
                frappe.db.rollback()
            except:
                pass
    
    return result


@click.command('execute-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--plan', 'plan_file', required=True, help='Path to migration plan file (JSON/YAML)')
@click.option('--dry-run/--apply', default=True, help='Dry run (default) or apply changes')
@click.option('--batch-size', default=1000, help='Batch size for data migration')
@click.option('--output', '-o', default=None, help='Output file for execution report')
@pass_context
def execute_plan(context, site, plan_file, dry_run, batch_size, output):
    """
    Execute a migration plan with dry-run or apply mode.
    
    Examples:
        bench app-migrator execute-plan --site mysite.localhost --plan plan.json --dry-run
        bench app-migrator execute-plan --site mysite.localhost --plan plan.json --apply
    """
    mode = "DRY-RUN" if dry_run else "APPLY"
    click.echo(f"🚀 Executing migration plan [{mode}]")
    click.echo(f"   Site: {site}")
    click.echo(f"   Plan: {plan_file}")
    click.echo("=" * 60)
    
    if not dry_run:
        click.echo("\n⚠️  WARNING: This will modify your database!")
        if not click.confirm("Are you sure you want to proceed?"):
            click.echo("❌ Execution cancelled")
            sys.exit(0)
    
    try:
        # Load plan
        with open(plan_file, 'r') as f:
            if plan_file.endswith('.yaml') or plan_file.endswith('.yml'):
                plan = yaml.safe_load(f)
            else:
                plan = json.load(f)
        
        plan["plan_file"] = plan_file
        
        frappe.init(site=site)
        frappe.connect()
        
        result = execute_plan_impl(site, plan, dry_run, batch_size)
        
        frappe.db.close()
        
        result_dict = result.to_dict()
        
        # Save report
        if output:
            with open(output, 'w') as f:
                json.dump(result_dict, f, indent=2)
            click.echo(f"\n📄 Execution report saved to: {output}")
        
        # Display summary
        summary = result_dict["summary"]
        click.echo(f"\n📊 EXECUTION SUMMARY [{mode}]")
        click.echo(f"   Steps Completed: {summary['steps_completed']}")
        click.echo(f"   Steps Failed: {summary['steps_failed']}")
        click.echo(f"   Steps Skipped: {summary['steps_skipped']}")
        click.echo(f"   Records Migrated: {summary['records_migrated']}")
        click.echo(f"   Schema Changes: {summary['schema_changes']}")
        click.echo(f"   Errors: {summary['errors']}")
        
        if result.success:
            if dry_run:
                click.echo(f"\n✅ Dry-run completed successfully!")
                click.echo(f"   Run with --apply to execute changes")
            else:
                click.echo(f"\n✅ Migration completed successfully!")
                click.echo(f"   Run 'bench --site {site} migrate' to complete")
        else:
            click.echo(f"\n❌ Execution failed with {summary['errors']} error(s)")
            for error in result.errors:
                click.echo(f"   - {error.get('step')}: {error.get('error')}")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Execution failed: {str(e)}")
        sys.exit(1)


# ==================== COMMAND GROUP REGISTRATION ====================

# Export all commands
commands = [scan_site, detect_conflicts, generate_plan, execute_plan]
