"""W2 (d): in-process tests for L394 cross-app symbol collision detection.

These bypass the bench CLI (which hangs on this substrate, L433) by driving the
collision core and the click command directly against a synthetic apps_root, so
the detection logic + envelope contract are verified without a live bench.
"""
import json
import os
import types

import pytest

# frappe's pass_context reads ctx.obj.profile; supply a minimal bench-context stub.
_CTX_OBJ = types.SimpleNamespace(profile=False)

from app_migrator.commands import module_conflicts as mc
from app_migrator.commands._envelope import SCHEMA_VERSION

REQUIRED_ENVELOPE_KEYS = {
    "schema_version", "command", "site", "status", "summary",
    "findings", "risks", "suggested_next_commands", "evidence", "meta",
}


def _make_app(apps_root, app, rel_path, source):
    """Write a .py file inside a synthetic app's inner package."""
    full = os.path.join(apps_root, app, app, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        fh.write(source)


@pytest.fixture
def two_app_root(tmp_path):
    """Two apps sharing class `SharedThing` and constant `SHARED_CONST`."""
    root = str(tmp_path / "apps")
    _make_app(root, "app_one", "mod_a.py",
              "class SharedThing:\n    pass\n\nSHARED_CONST = 1\n\ndef only_in_one():\n    pass\n")
    _make_app(root, "app_two", "sub/mod_b.py",
              "class SharedThing:\n    pass\n\nSHARED_CONST = 2\n\ndef only_in_two():\n    pass\n")
    # apps.txt manifest so _iter_app_names finds them deterministically.
    with open(os.path.join(root, "apps.txt"), "w") as fh:
        fh.write("app_one\napp_two\n")
    return root


def test_scan_detects_cross_app_collisions(two_app_root):
    result = mc.scan_collisions(apps_root=two_app_root)
    collisions = result["collisions"]
    assert "SharedThing" in collisions
    assert "SHARED_CONST" in collisions
    assert collisions["SharedThing"] == ["app_one", "app_two"]
    # Symbols unique to one app are NOT collisions.
    assert "only_in_one" not in collisions
    assert "only_in_two" not in collisions
    assert result["_stats"]["apps_scanned"] == 2
    assert result["_stats"]["collision_count"] == 2


def test_filter_restricts_symbols(two_app_root):
    result = mc.scan_collisions(apps_root=two_app_root, symbol_filter=r"^SHARED_")
    assert set(result["collisions"]) == {"SHARED_CONST"}


def test_private_symbols_excluded_by_default(tmp_path):
    root = str(tmp_path / "apps")
    _make_app(root, "a", "m.py", "def _helper():\n    pass\n")
    _make_app(root, "b", "m.py", "def _helper():\n    pass\n")
    with open(os.path.join(root, "apps.txt"), "w") as fh:
        fh.write("a\nb\n")
    assert "_helper" not in mc.scan_collisions(apps_root=root)["collisions"]
    assert "_helper" in mc.scan_collisions(apps_root=root, all_symbols=True)["collisions"]


def test_build_findings_shape():
    findings = mc.build_findings({"Foo": ["app_one", "app_two", "app_three"]})
    assert len(findings) == 1
    f = findings[0]
    assert f["id"] == "l394-collision-Foo"
    assert f["severity"] == "high"
    assert f["apps"] == ["app_one", "app_two", "app_three"]


def test_command_emits_valid_envelope(two_app_root):
    """CliRunner drives the click command with --json; assert envelope contract."""
    from click.testing import CliRunner

    runner = CliRunner()
    # emit_envelope calls sys.exit(rc); CliRunner captures it as result.exit_code.
    result = runner.invoke(
        mc.app_migrator_module_conflicts,
        ["--json", "--apps-root", two_app_root],
        obj=_CTX_OBJ,
    )
    # status=warn (collisions present) -> rc=10.
    assert result.exit_code == 10, f"unexpected rc={result.exit_code}; out={result.output[:300]}"
    envelope = json.loads(result.output)
    assert not (REQUIRED_ENVELOPE_KEYS - envelope.keys()), (
        f"missing keys: {REQUIRED_ENVELOPE_KEYS - envelope.keys()}"
    )
    assert envelope["schema_version"] == SCHEMA_VERSION
    assert envelope["status"] == "warn"
    assert envelope["command"] == "module-conflicts"
    # Every finding carries a stable id and high severity.
    ids = [f["id"] for f in envelope["findings"]]
    assert "l394-collision-SharedThing" in ids
    for f in envelope["findings"]:
        assert "id" in f
        assert f["severity"] == "high"


def test_command_clean_root_is_ok(tmp_path):
    """No collisions -> status ok, rc 0."""
    from click.testing import CliRunner

    root = str(tmp_path / "apps")
    _make_app(root, "solo", "m.py", "def unique_symbol():\n    pass\n")
    with open(os.path.join(root, "apps.txt"), "w") as fh:
        fh.write("solo\n")
    result = CliRunner().invoke(
        mc.app_migrator_module_conflicts, ["--json", "--apps-root", root],
        obj=_CTX_OBJ,
    )
    assert result.exit_code == 0, f"rc={result.exit_code}; out={result.output[:300]}"
    envelope = json.loads(result.output)
    assert envelope["status"] == "ok"
    assert envelope["findings"] == []


def test_default_apps_root_env_var_fallback(monkeypatch):
    """L433 spirit: env var BENCH_APPS_ROOT overrides hardcoded default."""
    import importlib
    import app_migrator.commands.module_conflicts as mc
    # Clear env var first
    monkeypatch.delenv("BENCH_APPS_ROOT", raising=False)
    importlib.reload(mc)
    assert mc.DEFAULT_APPS_ROOT == "/home/frappe/frappe-bench/apps"
    # Set env var + reload
    monkeypatch.setenv("BENCH_APPS_ROOT", "/custom/env/path")
    importlib.reload(mc)
    assert mc.DEFAULT_APPS_ROOT == "/custom/env/path"
