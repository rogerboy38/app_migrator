"""Forensic-replay tests for the SessionBootFailed cascade (scenario 07).

Pattern 1.13 (`forensic_fixture_capture`) in action: each test asserts a
specific invariant of the captured chain. Light tests (default) do file-only
parsing — no DB, no Frappe import. The heavy test
(`test_orphan_scanner_replay_against_test_site`) is gated on the env var
``APP_MIGRATOR_INTEGRATION=1`` and a configured test site at
``APP_MIGRATOR_TEST_SITE``.
"""

import filecmp
import hashlib
import os
import re
from pathlib import Path

import pytest

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "orphan_scenarios"
    / "07_sessionbootfailed_cascade"
    / "forensic"
)

CHAIN_DIRS = {
    1: "01_ui_orphan_scan_20260507_201122",
    2: "02_broad_orphan_scan_20260507_201619",
    3: "03_cache_clear_probe_20260507_205110",
    4: "04_cache_clear_probe_20260507_205442",
    5: "05_resolved_20260507_205520",
}

TARGETED_DELETED_DOCTYPES = {
    "Repost Accounting Ledger Settings",
    "Label Management",
    "TDS Default Parameter",
    "BOM Scrap Item",
    "Job Card Scrap Item",
    "Subcontracting Inward Order Scrap Item",
}

BOOT_BLOCKING_ROW_IDS = {"71240vkm07", "79su7selqq"}


def _chain(num: int) -> Path:
    return FIXTURE_ROOT / CHAIN_DIRS[num]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ============================================================
# Light tests — pure file I/O, no DB, no Frappe
# ============================================================


def test_all_chains_present():
    """Every captured chain dir + expected files exist."""
    expected = {
        1: ["MANIFEST.txt", "scan.out", "scan.sql"],
        2: ["broad_scan.out", "discover.sql", "generated_scan.sql"],
        3: ["desk_response.html", "probe.log"],
        4: ["desk_response.html", "probe.log"],
        5: ["delete.sql", "desk_response_post_fix.html", "fix.log"],
    }
    for num, files in expected.items():
        chain = _chain(num)
        assert chain.is_dir(), f"missing chain dir: {chain}"
        for f in files:
            assert (chain / f).is_file(), f"missing {chain.name}/{f}"


def test_chain_03_and_04_byte_identical():
    """The two cache-clear probes are byte-identical — proof that cache
    invalidation alone did NOT fix the cascade. Pattern 1.11b's diagnostic
    moment: the fix had to be SQL, not cache."""
    for fname in ("desk_response.html", "probe.log"):
        a = _chain(3) / fname
        b = _chain(4) / fname
        assert filecmp.cmp(a, b, shallow=False), (
            f"chain 03 vs 04 {fname} differ — cascade was no longer "
            f"reproducible by 20:54Z; the fixture's narrative no longer holds"
        )


def test_chain_01_manifest_lists_targeted_doctypes():
    """MANIFEST.txt enumerates the 6 deleted DocTypes — the input to
    Pattern 1.11's detection scan."""
    manifest = _read(_chain(1) / "MANIFEST.txt")
    for name in TARGETED_DELETED_DOCTYPES:
        assert name in manifest, f"DocType {name!r} missing from MANIFEST"


def test_chain_01_scan_out_columns():
    """scan.out is TSV with exactly (src, name, ref) columns and 2 data rows
    targeting Repost Accounting Ledger Settings."""
    lines = [ln for ln in _read(_chain(1) / "scan.out").splitlines() if ln.strip()]
    assert lines, "scan.out is empty"
    header = lines[0].split("\t")
    assert header == ["src", "name", "ref"], f"unexpected columns: {header}"

    data = [ln.split("\t") for ln in lines[1:]]
    assert len(data) == 2, f"expected 2 hits, got {len(data)}"
    for src, name, ref in data:
        assert src == "tabWorkspace Sidebar Item", f"unexpected src: {src!r}"
        assert ref == "Repost Accounting Ledger Settings"
        assert name in BOOT_BLOCKING_ROW_IDS


def test_chain_02_broad_scan_finds_tabversion_false_positives():
    """Broad scan must report the tabVersion rows — they're real orphans
    in a structural sense, just not boot-blocking. Capturing them in the
    fixture proves the scanner saw them, so the fix's choice to leave
    them alone is *deliberate*, not a miss."""
    out = _read(_chain(2) / "broad_scan.out")
    assert "tabVersion" in out, "broad_scan.out must include tabVersion hits"
    # The 4 known tabVersion row names captured 2026-05-07
    for row_name in ("b59gis9vhi", "kqb8ba62uo", "k89bru48td", "kqdcp5rg7u"):
        assert row_name in out, f"tabVersion row {row_name} missing from broad scan"


def test_chain_05_delete_sql_targets_only_workspace_sidebar_item():
    """Negative assertion: the fix must NOT delete from tabVersion or any
    table other than tabWorkspace Sidebar Item. A naive fix would over-delete
    by acting on every hit from the broad scan."""
    sql = _read(_chain(5) / "delete.sql")
    # Find every DELETE statement target table
    delete_targets = re.findall(
        r"DELETE\s+FROM\s+`?([\w\s]+?)`?\s+WHERE",
        sql,
        flags=re.IGNORECASE,
    )
    assert delete_targets, "no DELETE statements found in delete.sql"
    for target in delete_targets:
        assert target.strip() == "tabWorkspace Sidebar Item", (
            f"unexpected DELETE target: {target!r} — fix must not touch "
            f"tabVersion or other tables"
        )


def test_chain_05_delete_sql_uses_captured_row_ids():
    """The fix's WHERE clause must reference the exact 2 row names captured
    in chain 01. Whole-column DELETEs (no IN clause) are forbidden — that's
    the data-loss footgun this assertion guards against."""
    sql = _read(_chain(5) / "delete.sql")
    in_clauses = re.findall(r"name\s+IN\s*\(([^)]+)\)", sql, flags=re.IGNORECASE)
    assert in_clauses, "delete.sql must scope by `name IN (...)` — no whole-column wipes"
    found_ids = set()
    for clause in in_clauses:
        for tok in re.findall(r"'([^']+)'", clause):
            found_ids.add(tok)
    assert BOOT_BLOCKING_ROW_IDS <= found_ids, (
        f"missing captured row ids in DELETE: "
        f"{BOOT_BLOCKING_ROW_IDS - found_ids}"
    )


def test_pattern_1_11_signature_in_capture():
    """The captured scan.sql must reflect Pattern 1.11's
    INFORMATION_SCHEMA-driven approach — i.e. it queries the workspace +
    UI tables documented in the pattern's `triggers` field."""
    sql = _read(_chain(1) / "scan.sql")
    # A subset of the 14 tables MANIFEST.txt enumerates as scanned
    expected_tables = (
        "Workspace Sidebar Item",
        "Workspace Link",
        "Report",
        "Print Format",
        "Client Script",
    )
    for tbl in expected_tables:
        assert tbl in sql, f"Pattern 1.11 expected to scan {tbl}; not in scan.sql"


def test_chain_05_fix_log_records_pre_post_counts():
    """fix.log must show PRE-DELETE=2 and POST-DELETE=0 — the verification
    proof Pattern 1.14 mandates."""
    log = _read(_chain(5) / "fix.log")
    assert re.search(r"PRE-DELETE.*\b2\b", log), "fix.log missing PRE-DELETE=2 marker"
    assert re.search(r"POST-DELETE.*\b0\b", log), "fix.log missing POST-DELETE=0 marker"


def test_forensic_capture_immutability():
    """Sanity hash — if any captured file is edited, this test surfaces it.
    The fixture is *evidence*; edits silently invalidate the replay tests
    that assert against captured content."""
    sha = hashlib.sha256()
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        if path.is_file():
            sha.update(path.relative_to(FIXTURE_ROOT).as_posix().encode())
            sha.update(b"\0")
            sha.update(path.read_bytes())
            sha.update(b"\0")
    digest = sha.hexdigest()
    expected = os.environ.get("FORENSIC_07_SHA256")
    if expected:
        assert digest == expected, (
            f"forensic chain modified — recompute hash via "
            f"FORENSIC_07_SHA256={digest} pytest -k forensic_capture_immutability"
        )
    else:
        # First-run / unset: print the hash so it can be pinned later.
        # Test does not fail; this is a soft watermark, not a gate.
        print(f"\n[fixture-immutability] sha256={digest}")


# ============================================================
# Heavy test — replay against a real test site
# ============================================================

requires_integration = pytest.mark.skipif(
    not os.environ.get("APP_MIGRATOR_INTEGRATION"),
    reason=(
        "set APP_MIGRATOR_INTEGRATION=1 and APP_MIGRATOR_TEST_SITE=<sitename> "
        "to run forensic replay against a real Frappe site"
    ),
)


@requires_integration
def test_orphan_scanner_replay_against_test_site():
    """End-to-end replay: insert the captured row state into a test site,
    run Pattern 1.11's detection_query, assert the same orphans are found,
    apply the captured delete.sql, assert post-state is clean.

    Validates Pattern 1.13: a forensic chain captured in production must
    reproduce identically when replayed against an isolated bench site.
    """
    import frappe  # noqa: I900 — frappe only required for integration path

    site = os.environ["APP_MIGRATOR_TEST_SITE"]
    frappe.init(site=site)
    frappe.connect()
    try:
        # 1. Replay setup — insert the 2 boot-blocking Workspace Sidebar Item rows.
        # The DocType target ('Repost Accounting Ledger Settings') is intentionally
        # absent from tabDocType to mirror the real cascade.
        for row_name in BOOT_BLOCKING_ROW_IDS:
            frappe.db.sql(
                """INSERT INTO `tabWorkspace Sidebar Item`
                (name, link_type, link_to, parent, parenttype, parentfield)
                VALUES (%s, 'DocType', 'Repost Accounting Ledger Settings',
                        'Forensic Replay 07', 'Workspace', 'links')
                ON DUPLICATE KEY UPDATE link_to=VALUES(link_to)""",
                (row_name,),
            )
        frappe.db.commit()

        # 2. Run the Pattern 1.11 detection scan from the captured SQL.
        scan_sql = (_chain(1) / "scan.sql").read_text()
        # The captured scan.sql wraps several SELECT statements separated by `;`.
        # Execute each and collect (src, name, ref) tuples.
        hits = set()
        for stmt in (s.strip() for s in scan_sql.split(";") if s.strip()):
            try:
                rows = frappe.db.sql(stmt)
            except Exception:  # noqa: BLE001 — captured SQL can include known-failing
                continue       # statements (e.g. tabSingles column shape mismatch)
            for r in rows:
                if len(r) >= 3 and r[2] == "Repost Accounting Ledger Settings":
                    hits.add((r[0], r[1], r[2]))

        assert {h[1] for h in hits} >= BOOT_BLOCKING_ROW_IDS, (
            f"replay scan did not surface the captured row ids; got {hits!r}"
        )

        # 3. Apply the captured fix.
        delete_sql = (_chain(5) / "delete.sql").read_text()
        for stmt in (s.strip() for s in delete_sql.split(";") if s.strip() and not s.strip().startswith("--")):
            frappe.db.sql(stmt)
        frappe.db.commit()

        # 4. Assert post-fix: the boot-blocking rows are gone.
        remaining = frappe.db.sql(
            """SELECT COUNT(*) FROM `tabWorkspace Sidebar Item`
               WHERE link_type='DocType'
                 AND link_to='Repost Accounting Ledger Settings'""",
            as_dict=False,
        )
        assert remaining[0][0] == 0, (
            f"post-fix scan still found {remaining[0][0]} rows — replay did "
            f"not converge to the captured POST-DELETE=0 state"
        )
    finally:
        # Cleanup — leave the test site in the pre-replay state.
        for row_name in BOOT_BLOCKING_ROW_IDS:
            frappe.db.sql(
                "DELETE FROM `tabWorkspace Sidebar Item` WHERE name=%s",
                (row_name,),
            )
        frappe.db.commit()
        frappe.destroy()
