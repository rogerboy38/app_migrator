"""
DocType Classifier - Enhanced Classification System
Implements technical specification for doctype status detection

Classification Categories:
- STANDARD: Core doctype, not modified
- CUSTOMIZED: Standard doctype with Custom Fields or Property Setters
- CUSTOM: User-created doctype (custom=1)
- ORPHAN: Doctype with app=None or not in file system
"""

import frappe
from frappe.utils import get_sites
import os
import json
from pathlib import Path

class DoctypeStatus:
    """DocType status enumeration"""
    STANDARD = "standard"          # Not touched, from core app
    CUSTOMIZED = "customized"      # Has Custom Fields or Property Setters
    CUSTOM = "custom"              # Created by user (custom=1)
    ORPHAN = "orphan"              # app=None or not in file system
    UNKNOWN = "unknown"            # Unable to classify

def get_doctype_classification(doctype_name):
    """
    Classify a single doctype based on technical specifications
    
    Returns: dict with classification details
    """
    try:
        # Get DocType record
        doctype_doc = frappe.get_doc("DocType", doctype_name)
        
        classification = {
            "name": doctype_name,
            "status": DoctypeStatus.UNKNOWN,
            "app": doctype_doc.module,
            "custom_flag": doctype_doc.custom,
            "has_custom_fields": False,
            "has_property_setters": False,
            "custom_field_count": 0,
            "property_setter_count": 0,
            "is_orphan": False,
            "details": []
        }
        
        # Check 1: Is it a custom doctype? (custom=1)
        if doctype_doc.custom == 1:
            classification["status"] = DoctypeStatus.CUSTOM
            classification["details"].append("User-created custom doctype")
            return classification
        
        # Check 2: Is it orphaned? (app=None)
        if not doctype_doc.module or doctype_doc.module == "None":
            classification["status"] = DoctypeStatus.ORPHAN
            classification["is_orphan"] = True
            classification["details"].append("Orphan: No app assigned (app=None)")
            return classification
        
        # Check 3: Does it have Custom Fields?
        custom_fields = frappe.db.count("Custom Field", {"dt": doctype_name})
        if custom_fields > 0:
            classification["has_custom_fields"] = True
            classification["custom_field_count"] = custom_fields
            classification["details"].append(f"{custom_fields} Custom Fields")
        
        # Check 4: Does it have Property Setters?
        property_setters = frappe.db.count("Property Setter", {"doc_type": doctype_name})
        if property_setters > 0:
            classification["has_property_setters"] = True
            classification["property_setter_count"] = property_setters
            classification["details"].append(f"{property_setters} Property Setters")
        
        # Final classification
        if classification["has_custom_fields"] or classification["has_property_setters"]:
            classification["status"] = DoctypeStatus.CUSTOMIZED
        else:
            classification["status"] = DoctypeStatus.STANDARD
        
        return classification
        
    except Exception as e:
        return {
            "name": doctype_name,
            "status": DoctypeStatus.UNKNOWN,
            "error": str(e)
        }

def get_all_doctypes_by_app(app_name):
    """
    Get all doctypes for a specific app with classifications
    
    Returns: list of classified doctypes
    """
    doctypes = frappe.get_all(
        "DocType",
        filters={"module": ["like", f"%{app_name}%"]},
        fields=["name", "module", "custom"]
    )
    
    classified = []
    for dt in doctypes:
        classification = get_doctype_classification(dt.name)
        classified.append(classification)
    
    return classified

def get_all_custom_fields_by_app(app_name):
    """
    Get all Custom Fields applied to doctypes from a specific app
    
    Based on technical spec: Query tabCustom Field table
    """
    # Get all doctypes from the app first
    doctypes = frappe.get_all(
        "DocType",
        filters={"module": ["like", f"%{app_name}%"]},
        pluck="name"
    )
    
    if not doctypes:
        return []
    
    # Get Custom Fields for these doctypes
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"dt": ["in", doctypes]},
        fields=["name", "dt", "fieldname", "fieldtype", "label", "reqd", "options", "insert_after"]
    )
    
    return custom_fields

def get_all_property_setters_by_app(app_name):
    """
    Get all Property Setters for doctypes from a specific app
    
    Based on technical spec: Query tabProperty Setter table
    """
    # Get all doctypes from the app first
    doctypes = frappe.get_all(
        "DocType",
        filters={"module": ["like", f"%{app_name}%"]},
        pluck="name"
    )
    
    if not doctypes:
        return []
    
    # Get Property Setters for these doctypes
    property_setters = frappe.get_all(
        "Property Setter",
        filters={"doc_type": ["in", doctypes]},
        fields=["name", "doc_type", "field_name", "property", "value"]
    )
    
    return property_setters

def get_orphan_doctypes():
    """
    Detect orphan doctypes (app=None or not in file system)
    
    Based on technical spec: Analyze database for orphans
    """
    # Get all doctypes with app=None or empty module
    orphans = frappe.get_all(
        "DocType",
        filters=[
            ["module", "in", ["", "None", None]]
        ],
        fields=["name", "module", "custom"]
    )
    
    classified_orphans = []
    for orphan in orphans:
        classification = get_doctype_classification(orphan.name)
        classified_orphans.append(classification)
    
    return classified_orphans

def analyze_touched_tables():
    """
    Parse touched_tables.json for migration history
    
    Based on technical spec: Read sites/{sitename}/touched_tables.json
    """
    try:
        site_path = frappe.get_site_path()
        touched_file = os.path.join(site_path, "touched_tables.json")
        
        if not os.path.exists(touched_file):
            return {
                "exists": False,
                "message": "touched_tables.json not found - no migrations run yet"
            }
        
        with open(touched_file, 'r') as f:
            touched_tables = json.load(f)
        
        return {
            "exists": True,
            "count": len(touched_tables),
            "tables": touched_tables
        }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }

def generate_migration_risk_assessment(doctype_name):
    """
    Generate risk assessment for migrating a doctype
    
    Based on technical spec risk matrix
    """
    classification = get_doctype_classification(doctype_name)
    
    risk_matrix = {
        DoctypeStatus.STANDARD: {
            "level": "LOW",
            "description": "Standard doctype, low migration risk",
            "recommendations": ["Standard testing and backup procedures"]
        },
        DoctypeStatus.CUSTOMIZED: {
            "level": "MEDIUM",
            "description": "Customized doctype with Custom Fields or Property Setters",
            "recommendations": [
                "Document all custom fields before migration",
                "Use app-specific cleanup scripts",
                "Test in staging environment"
            ]
        },
        DoctypeStatus.CUSTOM: {
            "level": "LOW",
            "description": "Custom doctype, isolated from core system",
            "recommendations": ["Standard testing and backup procedures"]
        },
        DoctypeStatus.ORPHAN: {
            "level": "HIGH",
            "description": "Orphan doctype, requires special handling",
            "recommendations": [
                "Identify original app",
                "Fix app assignment before migration",
                "Consider cleanup if truly orphaned"
            ]
        }
    }
    
    status = classification.get("status", DoctypeStatus.UNKNOWN)
    risk = risk_matrix.get(status, {
        "level": "UNKNOWN",
        "description": "Unable to assess risk",
        "recommendations": ["Manual review required"]
    })
    
    return {
        "doctype": doctype_name,
        "status": status,
        "risk_level": risk["level"],
        "description": risk["description"],
        "recommendations": risk["recommendations"],
        "details": classification
    }

def display_classification_summary(classifications):
    """
    Display a formatted summary of doctype classifications
    """
    if not classifications:
        print("❌ No doctypes to classify")
        return
    
    # Count by status
    status_counts = {}
    for c in classifications:
        status = c.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n" + "=" * 80)
    print("📊 DOCTYPE CLASSIFICATION SUMMARY")
    print("=" * 80)
    
    total = len(classifications)
    print(f"\n📦 Total DocTypes: {total}")
    print("\n📈 Status Breakdown:")
    
    status_icons = {
        DoctypeStatus.STANDARD: "✅",
        DoctypeStatus.CUSTOMIZED: "⚙️",
        DoctypeStatus.CUSTOM: "🔧",
        DoctypeStatus.ORPHAN: "⚠️",
        DoctypeStatus.UNKNOWN: "❓"
    }
    
    for status, count in sorted(status_counts.items()):
        icon = status_icons.get(status, "📋")
        percentage = (count / total) * 100
        print(f"   {icon} {status.upper():12s}: {count:3d} ({percentage:5.1f}%)")
    
    print("\n" + "=" * 80)

def display_detailed_classifications(classifications, limit=None):
    """
    Display detailed information for each classified doctype
    """
    if not classifications:
        print("❌ No doctypes to display")
        return
    
    print("\n" + "=" * 80)
    print("📋 DETAILED DOCTYPE CLASSIFICATIONS")
    print("=" * 80)
    
    display_list = classifications[:limit] if limit else classifications
    
    for idx, c in enumerate(display_list, 1):
        status = c.get("status", "unknown")
        name = c.get("name", "Unknown")
        app = c.get("app", "N/A")
        
        status_icons = {
            DoctypeStatus.STANDARD: "✅",
            DoctypeStatus.CUSTOMIZED: "⚙️",
            DoctypeStatus.CUSTOM: "🔧",
            DoctypeStatus.ORPHAN: "⚠️",
            DoctypeStatus.UNKNOWN: "❓"
        }
        
        icon = status_icons.get(status, "📋")
        
        print(f"\n{idx}. {icon} {name}")
        print(f"   Status: {status.upper()}")
        print(f"   App: {app}")
        
        if c.get("has_custom_fields"):
            print(f"   Custom Fields: {c.get('custom_field_count', 0)}")
        if c.get("has_property_setters"):
            print(f"   Property Setters: {c.get('property_setter_count', 0)}")
        
        if c.get("details"):
            print(f"   Details: {', '.join(c['details'])}")
    
    if limit and len(classifications) > limit:
        remaining = len(classifications) - limit
        print(f"\n... and {remaining} more doctypes")
    
    print("\n" + "=" * 80)
