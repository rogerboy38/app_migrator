# Expected outcome — 07_sessionbootfailed_cascade

## Setup
Six DocTypes were deleted from `tabDocType` on 2026-05-07 in prod. Two
`tabWorkspace Sidebar Item` rows still pointed at `Repost Accounting Ledger
Settings`. Those references broke `/desk` boot with `SessionBootFailed`.

State to reproduce in a test site (replay):
- 6 entries in `tabDocType` for the targeted names — *removed* (not present)
- 2 entries in `tabWorkspace Sidebar Item` with `link_type='DocType'`,
  `link_to='Repost Accounting Ledger Settings'`, names `71240vkm07` and `79su7selqq`
- 4 entries in `tabVersion` with `ref_doctype IN ('Label Management',
  'Repost Accounting Ledger Settings')` (historical audit, optional)

## Bug symptom (current, pre-fix)
`/desk` page load triggers `frappe.DoesNotExistError` in `get_meta()` during
workspace permission check. Cascade fails the entire boot. `curl /desk` returns
HTTP 200 to `/login?redirect-to=/desk` with 0-byte body — false-positive
"healthy" if you only check status code (Pattern 1.14 explains this).

## Expected behavior (after Phase 2 fix is applied)

`bench app-migrator orphans --site <test_site> --fix --apply` (or the eventual
`audit-modules-disk-vs-db` consumer command) should:

1. **Detect** — Run Pattern 1.11's `INFORMATION_SCHEMA`-driven scan. Output
   must include the 2 `tabWorkspace Sidebar Item` row names from chain 01.
   Reference: `forensic/01_ui_orphan_scan_20260507_201122/scan.out`.

2. **Classify by tier** — Per Pattern 1.11 risk-score split:
   - `tabWorkspace Sidebar Item` rows → **blocking-tier** (`risk_score=0.85`),
     auto-fix with confirmation
   - `tabVersion` rows → **informational-tier** (`risk_score=0.4`),
     prompt user, default leave intact
   - Reference for the discriminator: chain 02's `broad_scan.out` shows both
     classes; chain 05's `delete.sql` shows only the blocking-tier got deleted.

3. **Fix** — Take backup, then `DELETE` exactly the 2 blocking-tier rows.
   The fix's SQL must match (modulo whitespace) the captured
   `forensic/05_resolved_20260507_205520/delete.sql`. Pre-count=2, post-count=0.

4. **Verify** — Per Pattern 1.14, post-fix verification must:
   - `curl -sIL /desk` follow-redirects → HTTP 200 baseline
   - `curl -sIL /api/method/frappe.auth.get_logged_user` *with session cookie*
     → 200 + JSON user (not just an anonymous redirect)
   - Optional: headless render to confirm workspace sidebar visible

5. **Chain** to Pattern 1.11b (`cached_bootinfo_survives_doctype_removal`):
   `bench clear-cache && bench --site <site> clear-website-cache && redis-cli
   FLUSHALL && container restart` after the surgical DELETE. Without this,
   bootinfo-cached references can still trip the cascade.

## Negative assertions (what the fix MUST NOT do)

- Must NOT `DELETE FROM tabVersion` — those are historical audit records.
  Chain 05 explicitly leaves them. The replay test `test_chain_05_delete_sql_targets_only_workspace_sidebar_item`
  enforces this.
- Must NOT issue `DELETE` without the captured row-name `IN` clause —
  i.e. no whole-column wipes. The replay test
  `test_chain_05_delete_sql_uses_captured_row_ids` enforces this.
- Must NOT report green from chain 03 / chain 04 alone. Both probes show
  `HTTP 200 / bytes=0` — the cascade was still active. Pattern 1.14's
  authenticated check is what catches this.

## Frappe issue references
- Pattern 1.11/1.11b/1.14 commit: `f7aa606` on `release/v10.2.0`
- Forensic source: `s3://frappe-backups-prod-2026/audit/sysmayal_*` +
  `/FIXED/sessionbootfailed_orphan_cascade_resolved_20260507_205520/`
- Cowork brief 2026-05-08 § "PRIMARY TASK — Step 2"
