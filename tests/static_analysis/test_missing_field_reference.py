"""Check: missing-field-reference — the tests.

This check reproduces the defect the 2026-11-05 audit of
``rnd_warehouse_management`` actually found: its Stock Entry controller reads
``movement_type_doc.sap_movement_code`` and
``movement_type_doc.requires_dual_signature``, but **neither field exists**
on the ``Movement Type`` fixture (whose fields are ``movement_code``,
``sap_equivalent``, ``purpose``, ``default_stock_entry_type``, …).

The bug survived for months precisely because the code was never executed —
which is the argument for detecting it statically.

The check is bench-free: these tests run with no Frappe and no ``bench`` CLI.
"""
from __future__ import annotations

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "missing-field-reference"


def _controller(body: str, doctype: str = "Item") -> str:
    """A minimal DocType controller source."""
    return (
        "import frappe\n"
        "from frappe.model.document import Document\n"
        "\n"
        "\n"
        f"class {doctype.replace(' ', '').replace('-', '')}(Document):\n"
        "    def validate(self):\n"
        f"{body}\n"
    )


def test_reading_a_field_that_does_not_exist_is_reported(apps_root, inventory):
    """The positive case: the controller reads a field the DocType lacks."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code", "movement_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.sap_movement_code:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["fieldname"] == "sap_movement_code"
    assert finding.evidence["doctype"] == "Item"
    assert finding.evidence["app"] == "rnd_warehouse_management"


def test_reading_a_field_that_does_exist_is_not_reported(apps_root, inventory):
    """The clean case must stay clean — a noisy check is a check nobody runs."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code", "movement_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.movement_code:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_framework_attributes_are_not_mistaken_for_fields(apps_root, inventory):
    """``self.docstatus`` / ``self.flags`` are BaseDocument API, not fields."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.docstatus and self.name and self.flags:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_custom_field_shipped_by_the_app_is_a_known_field(apps_root, inventory):
    """A Custom Field the app itself ships is a real field, not a missing one."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            custom_fields=[
                {"dt": "Item", "fieldname": "custom_sap_movement_type", "fieldtype": "Data"},
            ],
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.custom_sap_movement_type:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_non_controller_module_is_not_scanned(apps_root, inventory):
    """Only DocType controllers are in scope; a helper module is not a field."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            python_files={
                "utils/helpers.py": (
                    "def helper(doc):\n"
                    "    return doc.some_random_attribute\n"
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
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.sap_movement_code:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first and first[0].startswith("integrity-missing-field-reference-")


def test_severity_is_medium_not_high(apps_root, inventory):
    """A missing field usually raises at runtime; it does not corrupt data."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.nope:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings[0].severity == "medium"
