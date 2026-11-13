# 07 — SessionBootFailed cascade (real prod forensic chain)

This fixture is the **first real-prod-forensic** scenario in `orphan_scenarios/`.
Scenarios 01–06 are synthetic minimal apps that reproduce a single failure mode
each. This scenario captures an end-to-end *real* incident from
`erp.sysmayal2.cloud` on 2026-05-07: discovery → diagnosis → failed cache-clear →
surgical SQL fix → verification.

## Source incident

Six DocTypes were deleted earlier on 2026-05-07 during a cleanup pass:

```
Repost Accounting Ledger Settings
Label Management
TDS Default Parameter
BOM Scrap Item
Job Card Scrap Item
Subcontracting Inward Order Scrap Item
```

The deletes left dangling references in two UI tables (`tabWorkspace Sidebar Item`,
`tabVersion`) which broke `/desk` boot with a `SessionBootFailed` cascade on
every page load. This is the canonical instance of the three patterns
just registered at `f7aa606`:

- **Pattern 1.11** `orphan_ui_reference_after_doctype_removal`
- **Pattern 1.11b** `cached_bootinfo_survives_doctype_removal`
- **Pattern 1.14** `browser_verified_health`

## The 5 captured chains (chronological)

| # | Captured at (UTC) | Source | What it shows |
|---|---|---|---|
| 01 | 20:11:22Z | `audit/sysmayal_ui_orphan_scan_*` | Pattern 1.11 detection — UI-table-targeted scan finds 2 rows in `tabWorkspace Sidebar Item` |
| 02 | 20:16:19Z | `audit/sysmayal_broad_orphan_scan_*` | Wider scan finds 4 more rows in `tabVersion` (audit history; *not* boot-blocking — false-positives for the fix) |
| 03 | 20:51:10Z | `audit/sysmayal_cache_clear_probe_*` | First cache-clear + restart attempt. `/desk` still returns empty body |
| 04 | 20:54:42Z | `audit/sysmayal_cache_clear_probe_*` | Second cache-clear, byte-identical result. **Proves cache invalidation alone does NOT fix this.** |
| 05 | 20:55:20Z | `FIXED/sessionbootfailed_orphan_cascade_resolved_*` | Surgical `DELETE` of just the 2 boot-blocking rows. Pre=2, Post=0. Re-verify clean. |

## Critical insight preserved by this fixture

The broad scan (chain 02) found **6 orphan references**, but the fix (chain 05)
deleted **only 2 of them** — the `tabWorkspace Sidebar Item` rows that were
actually breaking desk boot. The 4 `tabVersion` rows are *normal historical
audit entries* and should NOT be deleted.

A naive "delete-everything-the-scanner-finds" auto-fix would corrupt the
audit history. The forensic-fixture replay test asserts this discrimination
explicitly — see `test_chain_05_delete_sql_targets_only_workspace_sidebar_item`
in `tests/orphan_scenarios/test_07_sessionbootfailed_cascade.py`.

## Layout

```
07_sessionbootfailed_cascade/
├── README.md                ← this file
├── expected_outcome.md      ← what scanner+fix should produce on replay
└── forensic/
    ├── 01_ui_orphan_scan_20260507_201122/
    ├── 02_broad_orphan_scan_20260507_201619/
    ├── 03_cache_clear_probe_20260507_205110/
    ├── 04_cache_clear_probe_20260507_205442/
    └── 05_resolved_20260507_205520/
```

13 captured files, 188 KB total. Files are textual SQL/log/HTML preserved
verbatim — no synthesis, no editing. They are the ground truth.

## Pattern 1.13 — `forensic_fixture_capture`

This fixture instantiates Pattern 1.13: the convention of preserving real
incident chains as bit-exact replay material in the test tree. See the
intelligence-engine entry for the full pattern. In short:

- Capture every step of the live diagnosis as a discrete chain dir
- Preserve byte-identical artifacts (no reformatting)
- Number chronologically, name with UTC timestamp + role
- Include MANIFEST.txt with metadata where helpful
- Wire each chain into a pytest assertion that exercises one piece of the
  scanner/fix pipeline against the captured ground truth

## Provenance

Original captures: `s3://frappe-backups-prod-2026/audit/sysmayal_*` and
`/FIXED/sessionbootfailed_*`. Pulled into repo on 2026-05-10 via
`aws --profile frappe-backups s3 cp --recursive`. SHAs verifiable against
the source bucket.
