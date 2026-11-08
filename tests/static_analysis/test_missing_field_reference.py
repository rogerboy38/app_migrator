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


# The ``Movement Type`` DocType as ``rnd_warehouse_management`` ships it: a
# fixture export, not a package ``doctype/`` directory. Its fields are the
# ones the fixture declares -- note that ``sap_movement_code`` and
# ``requires_dual_signature`` are NOT among them.
MOVEMENT_TYPE_FIXTURE = [
    {
        "name": "Movement Type",
        "fields": [
            {"fieldname": "movement_code", "fieldtype": "Data"},
            {"fieldname": "purpose", "fieldtype": "Select"},
            {"fieldname": "sap_equivalent", "fieldtype": "Data"},
        ],
    }
]


def _loads_document(local: str, doctype: str, field: str) -> str:
    """A controller that loads a document of ``doctype`` and reads ``field``.

    The local name is deliberately *not* ``<doctype>_doc``, so the read can
    only be judged through the binding, not through the naming convention.
    """
    return (
        "import frappe\n"
        "from frappe.model.document import Document\n"
        "\n"
        "\n"
        "class Item(Document):\n"
        "    def validate(self):\n"
        f"        {local} = frappe.get_doc('{doctype}', self.item_code)\n"
        f"        if {local} and {local}.{field}:\n"
        "            frappe.throw('boom')\n"
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


# --------------------------------------------------------------------------
# A call is not a read
# --------------------------------------------------------------------------
def test_a_method_call_is_not_a_field_read(apps_root, inventory):
    """``self.add_comment(...)`` calls a method; it does not read a field.

    ``add_comment`` is part of the Frappe ``Document`` API. Reporting it as a
    missing field was a false positive: the name is *called*, and a method
    that does not exist is a different bug class.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        self.add_comment('Info', 'Amended from')\n"
                    "        frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_method_call_off_another_document_is_not_a_field_read(apps_root, inventory):
    """``batch.add_comment(...)`` is a call on another document, too."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            doctypes={"Item": ["item_code"], "Batch AMB": ["batch_id"]},
            python_files={
                "doctype/item/item.py": (
                    "import frappe\n"
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class Item(Document):\n"
                    "    def validate(self):\n"
                    "        batch = frappe.get_doc('Batch AMB', self.item_code)\n"
                    "        batch.add_comment('Info', 'done')\n"
                    "        frappe.throw('boom')\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


# --------------------------------------------------------------------------
# A guarded read is deliberate
# --------------------------------------------------------------------------
def test_a_guarded_read_is_not_a_field_read(apps_root, inventory):
    """``getattr(self, 'title', None)`` says "this field may not be there".

    The plain ``self.title`` that follows it is the fallback of that same
    deliberate pattern, so neither may be reported.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        title = getattr(self, 'title', None)\n"
                    "        if title or self.title:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_hasattr_guard_is_not_a_field_read(apps_root, inventory):
    """``hasattr(self, 'x')`` is the same deliberate guard."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if hasattr(self, 'upper_limit'):\n"
                    "            frappe.throw(self.upper_limit)"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


# --------------------------------------------------------------------------
# A plain read of a field the DocType lacks is the real finding
# --------------------------------------------------------------------------
def test_a_plain_read_of_an_unknown_field_is_reported(apps_root, inventory):
    """The positive case stays positive after the false positives are gone."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _controller(
                    "        if self.some_unknown_field:\n"
                    "            frappe.throw('boom')"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["fieldname"] == "some_unknown_field"
    assert finding.evidence["doctype"] == "Item"
    assert finding.id.startswith("integrity-missing-field-reference-")


# --------------------------------------------------------------------------
# A document loaded from another DocType
# --------------------------------------------------------------------------
def test_a_field_read_off_another_document_is_reported(apps_root, inventory):
    """``loaded = frappe.get_doc("Item", ...)`` then ``loaded.nope``.

    The binding names the DocType, so the read can be judged against that
    DocType's fields instead of the controller's own.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"], "Batch AMB": ["batch_id"]},
            python_files={
                "doctype/item/item.py": _loads_document(
                    "loaded", "Batch AMB", "nope"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.evidence["fieldname"] == "nope"
    assert finding.evidence["doctype"] == "Batch AMB"
    assert finding.severity == "medium"


def test_a_field_that_exists_on_another_document_is_not_reported(apps_root, inventory):
    """The same shape, reading a field the other DocType does have."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"], "Batch AMB": ["batch_id"]},
            python_files={
                "doctype/item/item.py": _loads_document(
                    "loaded", "Batch AMB", "batch_id"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_binding_to_an_unknown_doctype_is_not_judged(apps_root, inventory):
    """An unknown DocType means an unknown field set: stay silent.

    Guessing would report a field that may well exist on a DocType the
    inventory has never seen.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            python_files={
                "doctype/item/item.py": _loads_document(
                    "loaded", "Unknown DocType", "whatever"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


# --------------------------------------------------------------------------
# A DocType shipped as a fixture (audit F1)
# --------------------------------------------------------------------------
def test_the_inventory_indexes_a_fixture_shipped_doctype(apps_root, inventory):
    """``Movement Type`` ships only as a fixture; the inventory must see it.

    An inventory that only walks package ``doctype/`` directories cannot see
    the DocType at all, and every check that asks "does this DocType have
    that field?" then answers "no such DocType".
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            fixtures={"doctype.json": MOVEMENT_TYPE_FIXTURE},
        ),
    ])
    inv = inventory(root)
    app = inv.app("rnd_warehouse_management")
    assert app is not None
    assert "Movement Type" in app.doctype_json_paths()
    assert app.fieldnames_for("Movement Type") == {
        "movement_code",
        "purpose",
        "sap_equivalent",
    }


def test_a_field_read_off_a_fixture_shipped_doctype_is_reported(apps_root, inventory):
    """Audit F1: ``sap_movement_code`` is not a field of ``Movement Type``.

    The controller loads the document with ``frappe.get_doc("Movement
    Type", ...)`` and reads a field the DocType does not define.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            fixtures={"doctype.json": MOVEMENT_TYPE_FIXTURE},
            python_files={
                "doctype/item/item.py": _loads_document(
                    "movement_type_doc", "Movement Type", "sap_movement_code"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.evidence["fieldname"] == "sap_movement_code"
    assert finding.evidence["doctype"] == "Movement Type"
    assert finding.evidence["app"] == "rnd_warehouse_management"
    assert finding.severity == "medium"
    assert finding.id == (
        "integrity-missing-field-reference-"
        "rnd_warehouse_management-movement_type-sap_movement_code"
    )


def test_a_field_that_exists_on_a_fixture_shipped_doctype_is_not_reported(apps_root, inventory):
    """The same shape, reading ``movement_code`` -- which does exist."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            fixtures={"doctype.json": MOVEMENT_TYPE_FIXTURE},
            python_files={
                "doctype/item/item.py": _loads_document(
                    "movement_type_doc", "Movement Type", "movement_code"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_module_read_of_a_bound_document_is_reported(apps_root, inventory):
    """The audited case, exactly: the code is a *module*, not a controller.

    ``rnd_warehouse_management`` ships the offending code as
    ``stock_entry.py`` with ``class CustomStockEntry(Document)``, and never
    registers that class as a controller. A controller-only scan therefore
    missed the very defect the check exists for. The local is named ``mt``
    so that only the *binding* can identify the DocType -- the
    ``<name>_doc`` convention is not allowed to do the work here.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            fixtures={"doctype.json": MOVEMENT_TYPE_FIXTURE},
            python_files={
                "stock_entry.py": (
                    "import frappe\n"
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class CustomStockEntry(Document):\n"
                    "    def validate(self):\n"
                    "        mt = frappe.get_doc('Movement Type', self.custom_movement_type)\n"
                    "        if mt.sap_movement_code:\n"
                    "            frappe.throw('nope')\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.evidence["fieldname"] == "sap_movement_code"
    assert finding.evidence["doctype"] == "Movement Type"
    assert finding.evidence["app"] == "rnd_warehouse_management"


def test_self_reads_outside_a_controller_are_not_reported(apps_root, inventory):
    """Outside a controller there is no document type to judge ``self`` against.

    ``self.unknown_field`` in a plain module may be a field of anything at
    all. Reporting it would be a guess, and a check that guesses is a check
    whose findings get ignored.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            doctypes={"Item": ["item_code"]},
            python_files={
                "helpers.py": (
                    "import frappe\n"
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class Helper(Document):\n"
                    "    def run(self):\n"
                    "        frappe.throw(self.unknown_field)\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_the_naming_convention_alone_is_not_enough_outside_a_controller(apps_root, inventory):
    """``movement_type_doc`` is a *convention*, not a fact.

    Outside a controller the convention is not used: the local has to be
    bound to a real document for the read to be judged. Here the local holds
    the result of a query -- a list of dicts -- so ``.sap_movement_code`` is
    a dict key, not a DocType field, and must not be reported.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Item": ["item_code"]},
            fixtures={"doctype.json": MOVEMENT_TYPE_FIXTURE},
            python_files={
                "batch.py": (
                    "import frappe\n"
                    "\n"
                    "\n"
                    "def collect():\n"
                    "    movement_type_doc = frappe.get_all('Movement Type', fields=['name'])\n"
                    "    return movement_type_doc.sap_movement_code\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_a_workflow_state_field_is_not_a_missing_field(apps_root, inventory):
    """Frappe creates the workflow state field as a Custom Field.

    The name is configurable -- the audited apps use both ``workflow_state``
    and ``workflow_state_1`` -- so it is read from the Workflow fixture
    rather than hard-coded.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            doctypes={"Stock Entry": ["item_code"]},
            fixtures={
                "workflow.json": [
                    {
                        "document_type": "Stock Entry",
                        "workflow_state_field": "workflow_state_1",
                    }
                ],
            },
            python_files={
                "doctype/stock_entry/stock_entry.py": _controller(
                    "        frappe.throw(self.workflow_state_1)",
                    doctype="Stock Entry",
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
