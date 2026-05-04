# Changelog

## [10.0.0-rc1] — 2026-05-04

Phase 1 cleanup of `app_migrator` to make the codebase mutable for
Phase 2's orphan-detection rebuild. No new features yet — this release
restructures the existing CLI surface, deduplicates intelligence, and
removes accumulated cruft so future work can ship cleanly.

### Added
- `intelligence_engine.py` namespace structure on `MigrationIntelligence`
  (5 namespaces total). All five are **instance attributes** populated
  in `__init__` from `_load_*` helper methods — instantiate the class
  to access them:

  ```python
  from app_migrator.commands.intelligence_engine import MigrationIntelligence
  mi = MigrationIntelligence()
  mi.pattern_database          # 10 entries
  mi.analysis_workflows        # 1 entry
  mi.ai_prompts                # 2 entries
  mi.risk_assessment_rules     # high_risk_factors / medium_risk_factors / severity_actions
  mi.success_patterns          # 2 entries
  ```

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
  - `success_patterns` — 2 entries (unchanged from v9).
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
- `fix-orphans` command — emits a deprecation banner from inside the
  function body (`commands/_legacy/fix_orphans.py:23-24`) directing
  users to `orphans --fix --apply`. The command itself still works
  for back-compat. Lives under `commands/_legacy/` so the v11 removal
  is a single `git rm -r commands/_legacy/`. **Scheduled for removal
  in v11.**

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

### Lint Cleanup (11 commits — Ruff: 3,814 errors → 0)

Post-init-pass cleanup arc that landed after the per-command extraction
work. Each commit was a focused mechanical pass over a single rule
class, keeping the diffs reviewable.

- `5794855` — exclude `_archive/` and `tests/legacy_command_tests/` from
  Ruff's lint scope (they hold preserved historical code, not active
  surface)
- `890190f` — `ruff --fix`: 3,090 mechanical fixes across the active
  command surface
- `8b11cf0` — fix: properly import `find_bench_root` in 10 command
  modules (T1.9's sweep had introduced 16 NameError bugs by adding the
  call without consistently importing the symbol)
- `d4d85ea` — fix: import `ensure_controller_files` in `unstage.py`
  (was being called transitively but no longer in scope after the
  T1.8.3 split)
- `5803c59` — `E722`: replace 38 bare `except:` with `except Exception:`
- `ef04adf` — `UP035`: remove 33 PEP 585-deprecated typing imports
  (`typing.Dict` → `dict`, etc.)
- `33dd9f1` — `E731`: replace 24 lambda fallback assignments with `def`
  blocks (`pass_context = lambda f: f` → `def pass_context(f): return f`)
- `5f78b37` — `W293/W291/I001`: strip whitespace in 85 docstring sites
- `d9cba94` — `B007/F841/RUF005`: 23 mechanical cleanups (unused loop
  vars, dead bindings, list-concat style)
- `58e6d94` — config: ignore `RUF001` (intentional Unicode info icons
  like 🆕 in CLI banners)
- `09cb61c` — `E701/B007/RUF013/RUF059`: final 9 lint fixes

### Wiring Fixes (2 commits)

Post-extraction wiring corrections — surfaced once the per-command
modules were active, revealing commands that had been registered in
some places but missed in others.

- `f50f3e9` — fix: export `app_migrator_resolve_duplicates` as a
  top-level command. Was registered in the click group but absent from
  the bench command list, so `bench app-migrator-resolve-duplicates`
  (top-level form) wouldn't work.
- `951d60a` — fix: wire orphaned `analyze-apps` and `quick-setup` as
  subcommands. Both were defined in their source files (analyze/apps.py
  and simple_api_setup.py respectively) but never registered.

### Smoke test

The full fresh-bench install smoke (`bench get-app` → `bench install-app`
→ `bench app-migrator health` on a previously-app-migrator-free bench)
could not be run as written: every non-default bench on UbuntuVM at
acceptance time is on Python 3.12.3, while v10.0.0-rc1's
`pyproject.toml` requires `>=3.14`. Only the active bench
(`/home/frappe/frappe-bench`) has Python 3.14. Creating a fresh
Python-3.14 bench is left to a follow-up; a tagged build awaits.

**Partial smoke (run on the active Python 3.14 bench, all green):**

| Check                                                         | Result |
|---------------------------------------------------------------|--------|
| `pip install -e ./apps/app_migrator` (build + install)        | ✅     |
| dist-info reflects the new version                            | ✅ `app_migrator-10.0.0rc1.dist-info` |
| `python3 -c "import app_migrator; print(__version__)"`        | ✅ `10.0.0-rc1` |
| All 18 extracted per-command modules import cleanly           | ✅     |
| All 6 helpers in `_shared.py` import                          | ✅     |
| `MigrationIntelligence()` instantiates; 5 namespaces present  | ✅ `pattern_database=10, risk_assessment_rules=3, success_patterns=2, analysis_workflows=1, ai_prompts=2` |
| `bench app-migrator --help` command count                     | ✅ 41 (was 39 pre-wiring; +2 from `951d60a`'s `analyze-apps` + `quick-setup`) |
| `bench list-apps`                                             | ✅ `app_migrator    10.0.0-rc1    release/v10.0.0-cleanup` |
| `ruff check app_migrator`                                     | ✅ "All checks passed!" (0 errors; verifies the 3,814-error cleanup arc holds) |

These partial smokes validate everything about the install path that
doesn't require a separate Python interpreter — build, install, import,
CLI surface, intelligence engine, lint. The portion deferred is
"installs cleanly on a Python 3.14 bench other than the one used to
build it," which requires a fresh Python 3.14 environment.

### Known Limitations

- **Python 3.14 ecosystem**: at acceptance time none of the team's
  pre-existing benches on UbuntuVM had been migrated to Python 3.14
  yet. v10.0.0-rc1 is the first release that requires it (per launch
  brief §1.4). A fresh-bench install verification is queued for once
  a 3.14 bench exists.
- **Customer-specific commands still in core**: see "Breaking changes"
  above. Not removed in v10; queued for v10.1.
