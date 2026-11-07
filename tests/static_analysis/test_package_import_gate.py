"""P0 gate: the app_migrator package must import.

Why this test exists
--------------------
Commit ``a3c297b`` (2026-05-07) added ``from .audit_app_for_antipattern
import ...`` to ``commands/__init__.py`` for a module that was not in the
tree. The result was that **every** ``bench app-migrator`` command died with
``ModuleNotFoundError: No module named 'app_migrator.commands.audit_app_for_antipattern'``.

What makes that worth a permanent test: the repository's lint job **passed**.
ruff never imports the package, so a package that cannot load sailed through
CI. This test closes that gap — it is the "fast CI job" the 2026-11-04 review
asked for, reduced to the smallest form that catches the P0 class of break.

It also pins the audit-derived commands to the CLI, so a rename or a dropped
registration fails here instead of on a production bench.
"""
from __future__ import annotations

import _frappe_stub


def _install_stub():
    """Install the frappe stand-in before importing app_migrator."""
    _frappe_stub.install()


def test_package_imports_without_a_bench():
    """The whole package must import with no Frappe and no ``bench`` CLI."""
    _install_stub()
    import app_migrator.commands  # noqa: F401

    assert app_migrator.commands is not None


def test_the_integrity_package_imports_with_no_frappe_at_all():
    """``app_migrator._integrity`` must not need frappe — that is its whole point."""
    import app_migrator._integrity as integrity

    assert integrity.Inventory is not None
    assert integrity.DEFAULT_APPS_ROOT


def test_the_audit_derived_commands_are_registered():
    """Both new CLI commands must be reachable from the app_migrator group."""
    _install_stub()
    import app_migrator.commands as commands

    group = getattr(commands, "app_migrator", None)
    assert group is not None, "the app_migrator click group is missing"
    registered = set(group.commands.keys())
    assert "audit-integrity" in registered, sorted(registered)
    assert "select-option-drift" in registered, sorted(registered)


def test_audit_integrity_exposes_the_json_flag():
    """The envelope contract requires a --json flag bound to ``as_json``."""
    _install_stub()
    from app_migrator.commands.audit_integrity import app_migrator_audit_integrity

    flags = {flag for param in app_migrator_audit_integrity.params
             for flag in getattr(param, "opts", [])}
    assert "--json" in flags, sorted(flags)
    json_params = [p for p in app_migrator_audit_integrity.params
                   if "--json" in getattr(p, "opts", [])]
    assert json_params[0].name == "as_json", (
        f"--json binds to {json_params[0].name!r}, expected 'as_json'"
    )


def test_every_registered_check_is_unique_and_kebab_case():
    """Check ids land in the envelope, so they must be stable and well-formed."""
    from app_migrator._integrity.checks import CHECKS

    ids = [spec.check_id for spec in CHECKS]
    assert len(ids) == len(set(ids)), ids
    for check_id in ids:
        assert check_id == check_id.lower()
        assert " " not in check_id
        assert "_" not in check_id, check_id


def test_every_check_declares_a_title_and_description():
    """The registry is what an agent reads; blank metadata is a bug."""
    from app_migrator._integrity.checks import CHECKS

    for spec in CHECKS:
        assert spec.title, spec.check_id
        assert spec.description, spec.check_id
