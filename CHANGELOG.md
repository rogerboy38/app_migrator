# Changelog

## [10.0.0-rc1] — 2026-05-04

Phase 1 cleanup of `app_migrator` to make the codebase mutable for
Phase 2's orphan-detection rebuild. No new features yet — this release
restructures the existing CLI surface, deduplicates intelligence, and
removes accumulated cruft so future work can ship cleanly.

### Added
- `intelligence_engine.py` namespace structure on `MigrationIntelligence`:
  - `pattern_database` — 10 atomic-fact entries (was 2 in v9): payment
    gateway detection, hardcoded-secret regexes, webhook + encryption
    patterns, `frappe_cloud_dependency`, `api_key_storage_strategy`,
    `frappe_cloud_api_endpoints` (press.api.* contract), and
    `frappe_site_rest_endpoints` (per-site frappe.* REST contract).
  - `analysis_workflows` — 1 entry: `site_inventory_analysis_flow`
    (canonical "what's installed where" workflow for FC-hosted
    multi-site environments). NEW namespace.
  - `ai_prompts` — 2 entries: `nl_command_routing` (15 intent regexes
    + 9 exact-match routes + skill summary + app aliases) and
    `command_followup_graph` ("what's next" reasoning per command type).
    NEW namespace.
  - `risk_assessment_rules['severity_actions']` — 4 categorized
    risk → severity/category/impact/mitigation mappings.
- `app_migrator/_archive/` directory with attribution `README.md`.
  Holds 9 digested non-migration modules: `payment_gateway_migrator`,
  `payment_security_migrator`, `ai_integration`, `analyze_main`,
  `setup_FILE` (renamed from `setup.py` to disambiguate from the
  `setup/` package), `site_api`, `cloud_api`, plus archived test
  drivers (`test_payment_migration_suite`, `test_payment_security`).
- `commands/_shared.py` for cross-command helpers:
  `ProgressTracker`, `MigrationSession`, `get_current_site`,
  `find_bench_root`, `discover_all_benches`, `detect_available_benches`
  (legacy), `get_bench_apps`.
- `commands/_legacy/` directory for deprecated commands awaiting
  removal in v11.
- `tests/fixtures/orphan_scenarios/` — 6 fixture apps reproducing
  Phase 2's target failure modes (red tests).
- `pyproject.toml [tool.ruff]` config (target Python 3.14).
- `.github/workflows/lint.yml` for Ruff CI.
- 16 per-command modules under `app_migrator/commands/` (one file per
  Click command — see "Changed").

### Changed
- `commands/__init__.py` shrank from over 2,150 lines to ~260 lines.
  Each Click command now lives in its own module file: `health.py`,
  `scan.py`, `conflicts.py`, `plan.py`, `execute.py`, `benches.py`,
  `apps.py`, `session.py`, `analyze_cmd.py` (named to avoid colliding
  with the `analyze/` subdir), `create_host.py`, `stage.py`,
  `unstage.py`, `fix_structure.py`, `ensure_controllers.py`,
  `fix_app_field.py`, `fix_json_app.py`, `resolve_duplicates.py`,
  `orphans.py`. `commands/__init__.py` now contains only the
  `@click.group` definition, the from-imports of each command, and the
  `add_command()` registrations.
- Bench discovery: hardcoded `~/frappe-bench` paths replaced with
  `find_bench_root()` across 12 command/helper files. Resolution order:
  `FRAPPE_BENCH` env var → `BENCH_PATH` env var (back-compat) → walk
  up from cwd → fallback to `~/frappe-bench` with `DeprecationWarning`.
- `bench app-migrator benches` switched from `~/frappe-bench*` glob to
  `discover_all_benches()`, which uses a proper apps/ + sites/apps.txt
  + Procfile detection triple. Catches benches with non-conventional
  names; the legacy glob is kept as a fallback.
- `fix-orphan-modules` renamed to `fix-modules` (it's about Module Def
  normalization, not orphan handling).
- Module-load `print()` statements replaced with `logger.debug()` (no
  longer pollutes every bench command's stdout).
- `ProgressTracker` deduplicated: was defined in both `__init__.py`
  and `migration_engine.py`; canonical version now lives in
  `_shared.py`, both old sites import from there.

### Deprecated
- `fix-orphans` command — emits a deprecation banner pointing users to
  `orphans --fix --apply`. Lives under `commands/_legacy/fix_orphans.py`
  to make the v11 deletion an atomic dir-rm. Will be **removed in v11**.

### Removed
- 5 pure-orphan duplicate files: `api_keys.py`, `api_key_setup.py`,
  `commands/modules/__init__.py`, `commands/modules/api_keys.py`,
  `commands/modules/git_ops.py`.
- `commands/__init__.py.bak2`/`.bak3`, `setup/wizard_old.py`,
  `setup/wizard.py.bak`, root-level `*.backup` files, root-level
  `fix_*.py` and `check_*.py` ad-hoc scripts.
- `fix-orphans-safe` command (consolidated into canonical `orphans`
  command).
- Inline `wizard` command (consolidated into canonical `setup-wizard`).
- The `enhanced_interactive_wizard.py` module (was only referenced by
  the now-removed inline wizard).
- Module-load `print()` statements (silenced via `logger.debug()`).

### Breaking changes
- Customer-specific commands (`fix-amb-w-tds2`, `fix-alexa-orphan`,
  `fix-kpi-factors`) currently still in core. Will move to an
  `app_migrator_amb_overlay` companion app in v10.1. **No removal in
  v10.**
- Bench-path discovery now requires either running from inside a bench
  OR setting `FRAPPE_BENCH` (or `BENCH_PATH`) env var. The previous
  hardcoded `~/frappe-bench` fallback emits a `DeprecationWarning` —
  still works, but won't in v11.
- The `setup-wizard` CLI command now resolves to `setup/wizard.py`'s
  implementation (canonical). The old `setup.py` FILE that defined a
  colliding `setup-wizard` was archived to `_archive/setup_FILE.py`
  during T1.5b group 2 (was never registered in `__init__.py`, so no
  observable behavior change for users — but flagging since the
  resolver order would have changed if anyone ever imported
  `app_migrator.commands.setup`).

### Roadmap
- **v10.1**: Extract customer-specific commands to
  `app_migrator_amb_overlay`. Possibly extract `api_key_manager.py` and
  `simple_api_setup.py` to a Frappe Cloud companion app.
- **v10.2**: Phase 2 — rebuild `orphans` command with three-layer
  protection (class-name correction, `custom: 1` flag, before_migrate
  cache-priming) per Frappe issue #37799.
- **v10.3**: Cross-app field overlap detection in `conflicts` command
  (lessons from V13.9.0 transport).
- **v11**: Remove deprecated `fix-orphans` command. Remove
  `~/frappe-bench` fallback in `find_bench_root()`. Pi/IoT support
  reconsidered.
