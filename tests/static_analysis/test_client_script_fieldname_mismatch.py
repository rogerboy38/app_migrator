"""Check: client-script-fieldname-mismatch — the tests.

This check reproduces the defect the app_migrator review called out: a client
script listened on ``sap_movement_type`` while the real field is
``custom_sap_movement_type``. The handler never fires, and the UI shows no
error — so the bug is invisible until someone reports the button does nothing.

The check is bench-free: these tests run with no Frappe and no ``bench`` CLI.
"""
from __future__ import annotations

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "client-script-fieldname-mismatch"


def test_a_client_script_listening_on_a_wrong_fieldname_is_reported(apps_root, inventory):
    """The positive case: the JS references a field the DocType does not have."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["item_code", "custom_sap_movement_type"]},
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) {\n"
                    "        if (frm.fields.sap_movement_type) {\n"
                    "            frm.set_value('sap_movement_type', '261');\n"
                    "        }\n"
                    "    }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["fieldname"] == "sap_movement_type"
    assert finding.evidence["doctype"] == "Stock Entry"
    # The near-miss suggestion is the actionable part of the finding.
    assert "custom_sap_movement_type" in finding.evidence["suggestions"]


def test_a_client_script_using_a_real_field_is_not_reported(apps_root, inventory):
    """The clean case must stay clean."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["item_code", "custom_sap_movement_type"]},
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) {\n"
                    "        frm.set_value('custom_sap_movement_type', '261');\n"
                    "    }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_js_file_outside_a_doctype_folder_is_skipped(apps_root, inventory):
    """Without a doctype there is no field list to compare against."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["item_code"]},
            js_files={
                "utils/common.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) { frm.set_value('not_a_field', 1); }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_document_api_pseudo_fields_are_not_reported(apps_root, inventory):
    """``frm.doc.name`` and friends exist on a document without being fields."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["item_code"]},
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) {\n"
                    "        console.log(frm.doc.name, frm.doc.owner, frm.doc.docstatus);\n"
                    "    }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_custom_field_shipped_by_the_app_is_a_known_field(apps_root, inventory):
    """A Custom Field the app itself ships is a real field."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["item_code"]},
            custom_fields=[
                {
                    "dt": "Stock Entry",
                    "fieldname": "custom_sap_movement_type",
                    "fieldtype": "Data",
                },
            ],
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) { frm.set_value('custom_sap_movement_type', '261'); }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_finding_ids_are_stable_across_runs(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["custom_sap_movement_type"]},
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) { frm.fields.sap_movement_type; }\n"
                    "});\n"
                ),
            },
        ),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first and first[0].startswith("integrity-client-script-fieldname-mismatch-")


def test_every_js_location_is_listed(apps_root, inventory):
    """The operator needs every place to fix, not just the first."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Stock Entry": ["custom_sap_movement_type"]},
            js_files={
                "stock_entry/stock_entry.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) { frm.fields.sap_movement_type; }\n"
                    "});\n"
                ),
                "stock_entry/extra.js": (
                    "frappe.ui.form.on('Stock Entry', {\n"
                    "    refresh(frm) { frm.fields.sap_movement_type; }\n"
                    "});\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    locations = result.findings[0].evidence["locations"]
    assert len(locations) == 2, locations
    assert all("line" in loc for loc in locations)
