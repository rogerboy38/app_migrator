# Orphan scanner — non-production path pollution fix

**Date:** 2026-05-08
**Branch:** `release/v10.2.0` (UbuntuVM, app_migrator)
**Trigger:** sysmayal report via Cowork (1162 FS DocTypes vs 1085 DB; COA AMB2 attributed to `app_migrator.pre-v10.1.x-backup`)
**Status:** Hypothesis CONFIRMED. Patch applied and helper-tested.

---

## 1. Root cause

`app_migrator/commands/orphans.py` (the `bench app-migrator orphans` command).
Old scanner code at lines 80–115 walked the FS with two unguarded loops:

```python
apps_path = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))
for app_name in os.listdir(apps_path):                  # ← any sibling dir
    app_dir = os.path.join(apps_path, app_name)
    if not os.path.isdir(app_dir) or app_name.startswith('.'):
        continue
    for root, _dirs, files in os.walk(app_dir):         # ← no prune
        if '/doctype/' in root:
            ...
            filesystem_doctypes[dt_name] = {...}        # ← last-write-wins
```

Three concrete defects:

1. **No app whitelist.** `os.listdir(apps_path)` returned every directory under `apps/`, including sibling backups like `app_migrator.pre-v10.1.x-backup/`.
2. **No walk pruning.** `os.walk` recursed into `tests/`, `fixtures/`, `_archive/`, `__pycache__/`, `.git/`, etc. Any path containing the substring `/doctype/` was treated as canonical — including `tests/fixtures/orphan_scenarios/.../doctype/tds_settings/`.
3. **Last-write-wins on collision.** When the same DocType (`coa_amb2.json`) existed in both `amb_w_tds/` and `app_migrator.pre-v10.1.x-backup/`, the alphabetically-later directory silently overwrote the earlier one in `filesystem_doctypes`, then the comparison against DB classified `dt.app=amb_w_tds` as `wrong_app` with "correct app" = the backup directory.

The third defect explains the misattribution; the first two explain the inflated counts (1162 vs 1085).

## 2. Files changed

- `app_migrator/commands/orphans.py` — only file modified.

Two additions:

- New module-level helpers `_load_apps_txt()`, `_should_skip_app_dir()`, `_should_prune_walk()`, plus three constants `NON_APP_NAME_PATTERNS`, `SKIP_WALK_COMPONENTS`, `SKIP_WALK_NAME_PATTERNS`.
- Replaced the FS scan loop with a filtered version using those helpers + sorted-listdir + collision detection.
- Added a `🔎 SCAN FILTERS` block to the report so users can see what was excluded and which DocTypes had cross-app collisions.

No mutations to control flow of `--fix`, `--reassign`, `--delete` modes; same call sites, same data shapes downstream.

## 3. Final skip rules

### Layer 1 — APP-LEVEL (whitelist)

`sites/apps.txt` is **authoritative**. A top-level dir under `apps/` is walked iff:

- name does not start with `.` or `_`, AND
- name appears in `sites/apps.txt`

If `sites/apps.txt` is missing, fall back to a name-pattern blocklist (`backup`, `archive`, `.bak`, `_bak`, `snapshot`, `.old`, `_old`, `.pre-`) and emit a warning. This fallback is loose by design — apps.txt is the right answer.

### Layer 2 — PATH-LEVEL (walk prune)

Inside an accepted app, `dirs[:]` is filtered before `os.walk` recurses. A directory is pruned iff:

- name starts with `.` or `_`, OR
- name is in the SKIP_WALK_COMPONENTS set:
  - `__pycache__`, `.git`, `.github`, `.hg`, `.svn`
  - `node_modules`, `.venv`, `venv`, `env`
  - `tests`, `test`, `fixtures`, `fixture`
  - `_archive`, `archive`
  - `docs`, `doc`, `build`, `dist`
  - `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.tox`
- OR name (case-folded) contains: `backup`, `archive`, `_bak`, `.bak`, `snapshot`

### Collision policy

`filesystem_doctypes[dt_name] = record` only writes if no record exists. Subsequent hits append to `fs_collisions` (logged in the SCAN FILTERS block) instead of silently overwriting. `sorted(os.listdir(apps_path))` makes "first hit wins" deterministic.

## 4. Validation

### Helper unit tests (passed on UbuntuVM, 2026-05-08)

| Case | Expected | Got |
|---|---|---|
| `app_migrator.pre-v10.1.x-backup` w/ apps.txt = `{amb_w_tds, app_migrator, frappe, erpnext}` | SKIP, reason "not listed in sites/apps.txt" | ✓ |
| `amb_w_tds` w/ same apps.txt | ACCEPT | ✓ |
| `backup_manager` w/ apps.txt = `{backup_manager, frappe}` (apps.txt overrides name pattern) | ACCEPT | ✓ |
| Walk prune of `tests`, `fixtures`, `__pycache__`, `.git`, `node_modules`, `_archive`, `build`, `venv`, `.venv`, `.pytest_cache`, `some_backup`, `data_archive` | PRUNE all | ✓ (12/12) |
| Walk keep of `doctype`, `controllers`, `amb_w_tds`, `public`, `templates` | KEEP all | ✓ (5/5) |
| `_load_apps_txt('/home/frappe/frappe-bench/apps')` | parses 26 apps | ✓ |

### Specimen regression target (sysmayal)

After the patch lands on sysmayal, with a directory tree containing both `apps/amb_w_tds/` (real) and `apps/app_migrator.pre-v10.1.x-backup/` (sibling not in apps.txt):

- COA AMB2 must NOT appear in `wrong_app` with "correct app" = `app_migrator.pre-v10.1.x-backup`.
- `Filesystem DocTypes found:` count should drop materially (the ~77-DocType gap, 1162→1085, is the expected ballpark, give or take fixtures inside other apps).
- The `🔎 SCAN FILTERS` block should list `apps/app_migrator.pre-v10.1.x-backup/` under "Skipped app-level dirs — not listed in sites/apps.txt".
- All DB DocTypes belonging to genuinely-installed apps must still be present in `filesystem_doctypes` (zero false negatives on legit apps).

I cannot fully reproduce the COA AMB2 specimen here on UbuntuVM (no `app_migrator.pre-v10.1.x-backup/` sibling exists locally), but the helper-level test with the exact specimen string passes.

## 5. CLI / UX recommendations

The new `🔎 SCAN FILTERS` report block shows what was excluded each run, so users do not need to source-dive when counts surprise them. Two further suggestions if results stay noisy:

- **`--include-non-installed-apps` flag** for the rare case someone genuinely wants the old behavior (e.g. forensic diff against a parked backup). Defaults to off.
- **`--strict-app-validation`** that errors out (rather than skips) when it finds a sibling dir that *looks* like an app (has `<dir>/<dir>/modules.txt` and `__init__.py`) but is not in apps.txt — this surfaces accidentally-uninstalled apps before the migrate step.

Neither is needed to land this fix; they are optional follow-ups.

## 6. Verification commands for Hugh on sysmayal

After pulling this patch onto sysmayal's `release/v10.2.0`:

```bash
# 1. Confirm the patch landed
cd ~/frappe-bench/apps/app_migrator
git log --oneline -1                 # head should be the new commit
grep -c '_should_skip_app_dir'       # expected: ≥3 hits in app_migrator/commands/orphans.py

# 2. Re-run the scanner on the affected site (dry-run, read-only)
cd ~/frappe-bench
bench --site <sysmayal-site> app-migrator orphans

# 3. Compare against the previous numbers
#    Expected: Filesystem DocTypes found ↓ from 1162, Total orphans ↓ from 1074
#    Expected new section: "🔎 SCAN FILTERS" listing apps/app_migrator.pre-v10.1.x-backup/

# 4. Spot-check the specimen
bench --site <sysmayal-site> app-migrator orphans 2>&1 | grep -i 'COA AMB2'
#    Expected: empty (or, if it still shows, the suggested-app must NOT be
#    app_migrator.pre-v10.1.x-backup)

# 5. Confirm legitimate DocTypes from amb_w_tds still scan correctly
bench --site <sysmayal-site> app-migrator orphans 2>&1 | grep -i 'amb_w_tds'
#    Spot-check that real amb_w_tds DocTypes are not in any orphan bucket
#    that they shouldn't be in (i.e., no regressions).

# 6. (Optional) JSON-equivalent run if you want a diffable snapshot
#    The orphans command doesn't have --json yet; use the new audit-modules-disk-vs-db
#    for a structured equivalent:
bench --site <sysmayal-site> app-migrator audit-modules-disk-vs-db --json > /tmp/audit_after.json
```

## 7. Out of scope (kept untouched per coordination protocol)

- `raven_ai_agent v2` scaffold work on sysmayal — not modified, not referenced.
- `audit_orphan_doctypes.py` (DB→FS direction, different command) — not affected; only does point-checks against expected paths and never enumerates the FS.
- `audit_modules_disk_vs_db.py` — already had its own filtered FS walk (skip set on line 81–85, scoped reads via `apps.txt`); reviewed and confirmed it is not affected by the same bug.
