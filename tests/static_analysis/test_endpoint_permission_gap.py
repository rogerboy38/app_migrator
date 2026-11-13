"""Check: endpoint-permission-gap — the tests.

These tests reproduce the defect the 2026-11-05 audits actually found:
``amb_w_tds`` publishes ``cleanup_test_data`` — a whitelisted endpoint that
deletes rows — plus two FoxPro migration helpers, also whitelisted. Neither
audited app shipped a single ``allow_guest=True`` endpoint, so guest access
is a defect rather than a house style.

The check is bench-free: these tests run with no Frappe and no ``bench``
CLI, which is the point of placing them outside ``app_migrator/commands/``.
"""
from __future__ import annotations

import re
from pathlib import Path

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "endpoint-permission-gap"

UNGUARDED_WRITE = """
import frappe


@frappe.whitelist()
def run_batch(name):
    frappe.db.sql("UPDATE `tabItem` SET substrate = %s", name)
    frappe.db.commit()
    return {"ok": True}
"""

GUARDED_READ = """
import frappe


@frappe.whitelist()
def list_items():
    if not frappe.has_permission("Item", "read"):
        frappe.throw("Not permitted")
    return frappe.get_all("Item", fields=["name"])
"""

READ_ONLY = """
import frappe


@frappe.whitelist()
def list_items():
    return frappe.get_all("Item", fields=["name"])
"""

IGNORE_PERMISSIONS = """
import frappe


@frappe.whitelist()
def wipe(name):
    doc = frappe.get_doc("Item", name)
    doc.delete(ignore_permissions=True)
    return {"ok": True}
"""

GUEST_ENDPOINT = """
import frappe


@frappe.whitelist(allow_guest=True)
def public_status():
    return frappe.db.get_value("Item", "ITEM-0001", "name")
"""

CLEANUP_TEST_DATA = """
import frappe


@frappe.whitelist()
def cleanup_test_data():
    frappe.db.delete("TabTest Log")
    return {"deleted": True}
"""

MIGRATION_HELPER = """
import frappe


@frappe.whitelist()
def migrate_foxpro_stock():
    return {"migrated": 0}
"""


def test_unwhitelisted_write_is_not_reported(apps_root, inventory):
    """The common case must stay clean — a noisy check is a check nobody runs."""
    root = apps_root([
        FakeApp(
            name="app_a",
            python_files={"api/internal.py": UNGUARDED_WRITE.replace(
                "@frappe.whitelist()\n", ""
            )},
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["unprotected_endpoints"] == 0


def test_guarded_endpoint_is_not_reported(apps_root, inventory):
    """An endpoint that checks its own permissions is doing the right thing."""
    root = apps_root([
        FakeApp(name="app_a", python_files={"api/guarded.py": GUARDED_READ}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["whitelisted_endpoints"] == 1


def test_unprotected_write_endpoint_is_high(apps_root, inventory):
    """A whitelisted endpoint that writes raw SQL and has no guard: high."""
    root = apps_root([
        FakeApp(name="amb_w_tds", python_files={"api/batch_api.py": UNGUARDED_WRITE}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.app == "amb_w_tds"
    evidence = finding.evidence
    assert evidence["file"] == "api/batch_api.py"
    assert evidence["function"] == "run_batch"
    assert evidence["apis"] == ["frappe.db.commit", "frappe.db.sql"]
    assert evidence["write_capable"] is True
    assert evidence["allow_guest"] is False
    assert evidence["module_kind"] == "application"
    assert isinstance(evidence["line"], int)


def test_read_only_endpoint_is_medium(apps_root, inventory):
    """A read-only bypass is a leak, not a data-loss: medium."""
    root = apps_root([
        FakeApp(name="app_a", python_files={"api/read.py": READ_ONLY}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["apis"] == ["frappe.get_all"]
    assert finding.evidence["write_capable"] is False


def test_ignore_permissions_write_is_high(apps_root, inventory):
    """``doc.delete(ignore_permissions=True)`` is a permission bypass too."""
    root = apps_root([
        FakeApp(name="app_a", python_files={"api/wipe.py": IGNORE_PERMISSIONS}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.evidence["apis"] == ["delete(ignore_permissions=True)"]
    assert finding.evidence["write_capable"] is True


def test_commit_without_a_write_is_not_a_bypass(apps_root, inventory):
    """``frappe.db.commit`` alone proves nothing — it must not create noise."""
    root = apps_root([
        FakeApp(
            name="app_a",
            python_files={"api/commit.py": (
                "import frappe\n\n\n"
                "@frappe.whitelist()\n"
                "def flush():\n"
                "    frappe.db.commit()\n"
                "    return {'ok': True}\n"
            )},
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_whitelisted_function_in_test_module_is_high(apps_root, inventory):
    """Audit evidence: ``cleanup_test_data`` is a whitelisted endpoint."""
    root = apps_root([
        FakeApp(name="amb_w_tds", python_files={"tests/test_cleanup.py": CLEANUP_TEST_DATA}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.evidence["module_kind"] == "test_or_migration"
    assert finding.evidence["file"] == "tests/test_cleanup.py"


def test_whitelisted_function_in_migration_module_is_high(apps_root, inventory):
    """Audit evidence: two FoxPro migration helpers are whitelisted."""
    root = apps_root([
        FakeApp(name="amb_w_tds", python_files={"migrations/v1_0.py": MIGRATION_HELPER}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.evidence["module_kind"] == "test_or_migration"


def test_guest_endpoint_is_surfaced_in_the_evidence(apps_root, inventory):
    """A guest endpoint needs no session at all — it must be obvious."""
    root = apps_root([
        FakeApp(name="app_a", python_files={"api/public.py": GUEST_ENDPOINT}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.evidence["allow_guest"] is True
    assert "GUEST" in finding.title, finding.title
    assert result.stats["guest_endpoints"] == 1


def test_finding_id_is_stable_and_carries_no_line_number(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    root = apps_root([
        FakeApp(name="amb_w_tds", python_files={"api/batch_api.py": UNGUARDED_WRITE}),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first == ["integrity-endpoint-permission-gap-amb-w-tds-api-batch-api-run-batch"]


def test_finding_id_survives_a_line_shift(apps_root, inventory):
    """Moving the function down the file must not change its id."""
    source = "import frappe\n\n\n@frappe.whitelist()\ndef run_batch(name):\n    frappe.db.sql('UPDATE tabItem SET x = 1')\n"
    shifted = "\n\n" + source
    before = finding_ids(run_check(CHECK_ID, inventory(
        apps_root([FakeApp(name="app_a", python_files={"api/x.py": source})])
    )))
    after = finding_ids(run_check(CHECK_ID, inventory(
        apps_root([FakeApp(name="app_a", python_files={"api/x.py": shifted})])
    )))
    assert before == after
    assert before == ["integrity-endpoint-permission-gap-app-a-api-x-run-batch"]


def test_check_module_never_imports_frappe():
    """The package must stay importable without a bench."""
    import app_migrator._integrity.checks.endpoint_permission_gap as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*import\s+frappe\b", source, re.M)
    assert not re.search(r"^\s*from\s+frappe\b", source, re.M)


GUEST_LOGIN_ENDPOINT = """
import frappe


@frappe.whitelist(allow_guest=True)
def bot_authenticate(api_key, bot_type):
    cfg = frappe.get_all("Bot Config", filters={"api_key": api_key}, fields=["name"])
    if not cfg:
        frappe.throw("Invalid")
    return {"status": "authenticated", "session_token": "abc123"}
"""

GUEST_WRITE_ENDPOINT = """
import frappe


@frappe.whitelist(allow_guest=True)
def receive_weight_event(**kwargs):
    doc = frappe.get_doc({"doctype": "Weight Event"})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success"}
"""


def test_a_guest_login_endpoint_is_not_reported_as_a_permission_bypass(apps_root, inventory):
    """An endpoint that hands out a credential is an *authentication* endpoint.

    ``amb_w_spc`` ships ``bot_authenticate`` with ``allow_guest=True``.
    Calling it "a guest permission bypass" says something false: guest
    access is the point -- establishing the session is its job. It is still
    reported, because a credential-minting endpoint that anyone can reach
    is worth a human's attention, but under its own framing.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            python_files={"scripts/automation_scripts.py": GUEST_LOGIN_ENDPOINT},
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert "Authentication endpoint" in finding.title, finding.title
    assert "permission bypass" not in finding.title, finding.title
    assert finding.evidence["is_auth_endpoint"] is True
    assert finding.evidence["allow_guest"] is True


def test_a_guest_write_endpoint_is_still_a_permission_bypass(apps_root, inventory):
    """Guest access is only excusable when the endpoint is a login endpoint.

    ``receive_weight_event`` accepts guests *and* writes with
    ``ignore_permissions=True``. That is the real defect, and it keeps the
    high severity.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            python_files={
                "system_integration/doctype/weight_event/weight_event.py":
                    GUEST_WRITE_ENDPOINT
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert "bypasses the permission model" in finding.title, finding.title
    assert finding.evidence["is_auth_endpoint"] is False


def test_the_guest_wording_does_not_say_logged_in_users(apps_root, inventory):
    """A guest endpoint is reachable by anyone at all, not only by logged-in users."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            python_files={
                "system_integration/doctype/weight_event/weight_event.py":
                    GUEST_WRITE_ENDPOINT
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    description = result.findings[0].description
    assert "any logged-in user" not in description, description
    assert "anyone at all" in description, description
