"""Check: dead-hook-target — the tests.

These tests reproduce the defects the 2026-11-05 audit of
``rnd_warehouse_management`` found:

- ``override_whitelisted_methods`` points at
  ``...stock_entry.make_custom_stock_entry``, a function that exists nowhere;
- ``has_website_permission`` points at ``...permissions.warehouse_query``
  while the app has no ``permissions`` module at all;
- ``class CustomStockEntry(Document)`` carries real business logic but is
  never referenced anywhere and is not registered in
  ``override_doctype_class``;
- four of the five ``doc_events`` Stock Entry handlers are literally ``pass``.

The checks are bench-free: these tests run with no Frappe and no ``bench``
CLI, which is the point of placing them outside ``app_migrator/commands/``.

Note: ``FakeApp.hooks`` is raw ``hooks.py`` source that the builder runs
through ``str.format``, so every literal brace in a hook body is doubled.
"""
from __future__ import annotations

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "dead-hook-target"


def test_override_whitelisted_target_that_does_not_exist_is_high(apps_root, inventory):
    """The audited case: the override points at a function that is nowhere."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "override_whitelisted_methods = {{\n"
                '    "erpnext.stock.stock_ledger.get_batch_entries":\n'
                '    "rnd_warehouse_management.stock_entry.make_custom_stock_entry",\n'
                "}}\n"
            ),
            python_files={
                "stock_entry.py": "def get_batch_entries():\n    return []\n",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.evidence["kind"] == "override-whitelisted"
    assert finding.evidence["hook"] == "override_whitelisted_methods"
    assert (
        finding.evidence["value"]
        == "rnd_warehouse_management.stock_entry.make_custom_stock_entry"
    )
    assert finding.evidence["originals"] == ["erpnext.stock.stock_ledger.get_batch_entries"]
    assert finding.id == (
        "integrity-dead-hook-target-rnd_warehouse_management-override-whitelisted-"
        "stock-entry-make-custom-stock-entry"
    )


def test_has_website_permission_without_a_module_is_medium(apps_root, inventory):
    """A website permission that points at a missing module is medium.

    This is the **list** shape of the hook (a plain list of handler paths),
    which some Frappe versions accept. Frappe only calls this hook on a
    website request, so the failure is quieter than a broken migrate-time
    hook.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "has_website_permission = "
                '["rnd_warehouse_management.permissions.warehouse_query"]\n'
            ),
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["kind"] == "website-permission"
    assert "does not exist" in finding.evidence["reason"], finding.evidence["reason"]
    # The list shape names no owner, so no DocType evidence is invented.
    assert "doctypes" not in finding.evidence
    assert finding.id == (
        "integrity-dead-hook-target-rnd_warehouse_management-website-permission-"
        "permissions-warehouse-query"
    )


def test_has_website_permission_dict_shape_is_reported(apps_root, inventory):
    """The REAL shape: a dict keyed by DocType.

    ``rnd_warehouse_management`` writes (audit 2026-11-05, hooks.py L24)::

        has_website_permission = {
            "Warehouse": "rnd_warehouse_management.permissions.warehouse_query",
            "Stock Entry": "rnd_warehouse_management.permissions.stock_entry_query",
        }

    The app ships no ``permissions`` module at all, so both targets are dead.
    A scanner that only reads the list shape sees nothing here and reports
    nothing — which is how this defect shipped.
    """
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "has_website_permission = {{\n"
                '    "Warehouse": '
                '"rnd_warehouse_management.permissions.warehouse_query",\n'
                '    "Stock Entry": '
                '"rnd_warehouse_management.permissions.stock_entry_query"\n'
                "}}\n"
            ),
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 2, finding_ids(result)

    warehouse_id = (
        "integrity-dead-hook-target-rnd_warehouse_management-website-permission-"
        "permissions-warehouse-query"
    )
    stock_entry_id = (
        "integrity-dead-hook-target-rnd_warehouse_management-website-permission-"
        "permissions-stock-entry-query"
    )
    findings = {f.id: f for f in result.findings}
    assert set(findings) == {warehouse_id, stock_entry_id}

    warehouse = findings[warehouse_id]
    assert warehouse.severity == "medium", warehouse.severity
    assert warehouse.evidence["kind"] == "website-permission"
    assert warehouse.evidence["hook"] == "has_website_permission"
    assert (
        warehouse.evidence["value"]
        == "rnd_warehouse_management.permissions.warehouse_query"
    )
    assert "does not exist" in warehouse.evidence["reason"], warehouse.evidence["reason"]
    # The owning DocType is the evidence the dict shape carries.
    assert warehouse.evidence["doctypes"] == ["Warehouse"]
    assert warehouse.evidence["doctype"] == "Warehouse"

    stock_entry = findings[stock_entry_id]
    assert stock_entry.severity == "medium", stock_entry.severity
    assert stock_entry.evidence["doctypes"] == ["Stock Entry"]
    assert stock_entry.evidence["doctype"] == "Stock Entry"

    # The counter must count the dict targets too, not only the list ones.
    assert result.stats["hooks_scanned"] == 2
    assert result.stats["targets_missing"] == 2


def test_has_website_permission_dict_finding_ids_are_stable(apps_root, inventory):
    """The id is the diff key an agent uses; it must not drift."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "has_website_permission = {{\n"
                '    "Warehouse": '
                '"rnd_warehouse_management.permissions.warehouse_query",\n'
                '    "Stock Entry": '
                '"rnd_warehouse_management.permissions.stock_entry_query"\n'
                "}}\n"
            ),
        ),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first == [
        "integrity-dead-hook-target-rnd_warehouse_management-website-permission-"
        "permissions-stock-entry-query",
        "integrity-dead-hook-target-rnd_warehouse_management-website-permission-"
        "permissions-warehouse-query",
    ]


def test_has_website_permission_dict_that_resolves_is_not_reported(apps_root, inventory):
    """A dict hook whose target exists must not produce a finding.

    The fix must not turn the check into a noise machine: only the targets
    that resolve nowhere are reported.
    """
    root = apps_root([
        FakeApp(
            name="app_a",
            hooks=(
                "has_website_permission = {{\n"
                '    "Warehouse": "app_a.permissions.warehouse_query",\n'
                "}}\n"
            ),
            python_files={
                "permissions.py": "def warehouse_query(doc):\n    return True\n",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["targets_missing"] == 0
    assert result.stats["hooks_scanned"] == 1


def test_has_website_permission_skips_non_string_entries(apps_root, inventory):
    """A mixed shape is skipped — not crashed on, and not invented from."""
    root = apps_root([
        FakeApp(
            name="app_a",
            hooks=(
                "has_website_permission = {{\n"
                '    "Warehouse": 42,\n'
                '    "Stock Entry": "app_a.permissions.stock_entry_query",\n'
                "}}\n"
            ),
        ),
        FakeApp(
            name="app_b",
            hooks=(
                "has_website_permission = "
                "['app_b.permissions.warehouse_query', 42]\n"
            ),
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 2, finding_ids(result)
    by_app = {f.evidence["app"]: f for f in result.findings}
    assert by_app["app_a"].evidence["doctypes"] == ["Stock Entry"]
    assert by_app["app_b"].evidence["value"] == "app_b.permissions.warehouse_query"
    assert "doctypes" not in by_app["app_b"].evidence


def test_doc_events_handler_that_only_passes_is_medium(apps_root, inventory):
    """The handler exists but does nothing: the rule never takes effect."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "doc_events = {{\n"
                '    "Stock Entry": {{\n'
                '        "on_update": ["rnd_warehouse_management.stock_entry.on_update"],\n'
                "    }},\n"
                "}}\n"
            ),
            python_files={
                "stock_entry.py": "def on_update(doc, method=None):\n    pass\n",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["kind"] == "doc-event"
    assert finding.evidence["reason"] == "handler is a no-op"
    assert finding.evidence["file"] == "rnd_warehouse_management/stock_entry.py"
    assert finding.evidence["line"] == 1
    assert finding.evidence["doctypes"] == ["Stock Entry"]
    assert finding.evidence["events"] == ["on_update"]


def test_scheduler_event_handler_that_does_not_exist_is_high(apps_root, inventory):
    """A scheduler event pointing at nothing never runs: high."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "scheduler_events = {{\n"
                '    "daily": ["rnd_warehouse_management.tasks.run_daily"],\n'
                "}}\n"
            ),
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.evidence["kind"] == "scheduler-event"
    assert finding.evidence["events"] == ["daily"]
    assert finding.id == (
        "integrity-dead-hook-target-rnd_warehouse_management-scheduler-event-"
        "tasks-run-daily"
    )


def test_override_doctype_class_without_the_class_is_high(apps_root, inventory):
    """The override names a class that does not exist: high."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            hooks=(
                "override_doctype_class = {{\n"
                '    "Plant Configuration": '
                '"amb_w_tds.overrides.plant_configuration.PlantConfiguration",\n'
                "}}\n"
            ),
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.evidence["kind"] == "doctype-class"
    assert finding.evidence["doctype"] == "Plant Configuration"
    assert finding.id == (
        "integrity-dead-hook-target-amb_w_tds-doctype-class-plant-configuration"
    )


def test_override_doctype_class_claiming_another_apps_doctype_is_medium(apps_root, inventory):
    """The audited drift: amb_w_tds claims a DocType amb_w_spc ships."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Plant Configuration": ["name"]}),
        FakeApp(
            name="amb_w_tds",
            hooks=(
                "override_doctype_class = {{\n"
                '    "Plant Configuration": '
                '"amb_w_tds.overrides.plant_configuration.PlantConfiguration",\n'
                "}}\n"
            ),
            python_files={
                "overrides/plant_configuration.py": (
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class PlantConfiguration(Document):\n"
                    "    def validate(self):\n"
                    "        return True\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["kind"] == "doctype-class"
    assert finding.evidence["owner_app"] == "amb_w_spc"
    assert finding.evidence["shipped_as"] == "Plant Configuration"
    assert finding.id == (
        "integrity-dead-hook-target-amb_w_tds-doctype-class-plant-configuration"
    )


def test_document_class_that_is_never_referenced_is_high(apps_root, inventory):
    """Real business logic nothing references: the logic never runs."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            python_files={
                "stock_entry.py": (
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class CustomStockEntry(Document):\n"
                    "    def validate(self):\n"
                    "        if not self.docstatus:\n"
                    "            return True\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.evidence["kind"] == "unregistered-class"
    assert finding.evidence["class"] == "CustomStockEntry"
    assert finding.evidence["file"] == "rnd_warehouse_management/stock_entry.py"
    assert finding.evidence["line"] == 4
    assert finding.evidence["reason"] == "defined but never registered or referenced"
    assert finding.id == (
        "integrity-dead-hook-target-rnd_warehouse_management-unregistered-class-"
        "customstockentry"
    )


def test_hooks_that_all_resolve_are_not_reported(apps_root, inventory):
    """The clean case must stay clean — a noisy check is a check nobody runs."""
    root = apps_root([
        FakeApp(
            name="app_a",
            hooks=(
                "doc_events = {{\n"
                '    "Stock Entry": {{\n'
                '        "on_update": ["app_a.stock_entry.on_update"],\n'
                "    }},\n"
                "}}\n"
                "override_whitelisted_methods = {{\n"
                '    "erpnext.stock.stock_ledger.get_batch_entries":\n'
                '    "app_a.stock_entry.get_batch_entries",\n'
                "}}\n"
                'has_website_permission = ["app_a.permissions.warehouse_query"]\n'
                "override_doctype_class = {{\n"
                '    "Stock Entry": "app_a.overrides.stock_entry.StockEntry",\n'
                "}}\n"
                "scheduler_events = {{\n"
                '    "daily": ["app_a.tasks.run"],\n'
                "}}\n"
            ),
            python_files={
                "stock_entry.py": (
                    "def on_update(doc, method=None):\n"
                    "    doc.save()\n"
                    "\n"
                    "\n"
                    "def get_batch_entries():\n"
                    "    return []\n"
                ),
                "permissions.py": "def warehouse_query(doc):\n    return True\n",
                "overrides/stock_entry.py": (
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class StockEntry(Document):\n"
                    "    def validate(self):\n"
                    "        return True\n"
                ),
                "tasks.py": "def run():\n    print('daily')\n",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["targets_missing"] == 0


def test_doctype_controller_class_is_not_reported_as_unregistered(apps_root, inventory):
    """Frappe loads DocType controllers by convention, not by reference.

    A controller in ``doctype/<slug>/<slug>.py`` is never imported anywhere,
    and that is normal — it must not be reported.
    """
    root = apps_root([
        FakeApp(name="app_a", doctypes={"Stock Entry": ["name"]}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_stats_report_what_was_scanned(apps_root, inventory):
    """The stats block says how much was looked at, not just what was found."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "override_whitelisted_methods = {{\n"
                '    "erpnext.stock.stock_ledger.get_batch_entries":\n'
                '    "rnd_warehouse_management.stock_entry.make_custom_stock_entry",\n'
                "}}\n"
            ),
            python_files={
                "stock_entry.py": (
                    "from frappe.model.document import Document\n"
                    "\n"
                    "\n"
                    "class CustomStockEntry(Document):\n"
                    "    def validate(self):\n"
                    "        return True\n"
                ),
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.stats["apps_scanned"] == 1
    assert result.stats["hooks_scanned"] == 1
    assert result.stats["targets_missing"] == 1
    assert result.stats["targets_noop"] == 0
    assert result.stats["classes_scanned"] == 1
    assert result.stats["unregistered_classes"] == 1


def test_finding_ids_are_stable_across_runs(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    root = apps_root([
        FakeApp(
            name="rnd_warehouse_management",
            hooks=(
                "override_whitelisted_methods = {{\n"
                '    "erpnext.stock.stock_ledger.get_batch_entries":\n'
                '    "rnd_warehouse_management.stock_entry.make_custom_stock_entry",\n'
                "}}\n"
            ),
            python_files={
                "stock_entry.py": "def get_batch_entries():\n    return []\n",
            },
        ),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first == [
        "integrity-dead-hook-target-rnd_warehouse_management-override-whitelisted-"
        "stock-entry-make-custom-stock-entry"
    ]
