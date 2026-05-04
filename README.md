# app_migrator

**Version:** 10.0.0-rc1  
**Python:** 3.14+  
**Frappe:** v16+

---

## What it does

You have N parallel Frappe apps and want to consolidate to M ≤ N — possibly one receiver app that absorbs DocTypes from multiple donor apps. app_migrator is the CLI tool that gets you there.

The core problem it solves is the "alacran-mother" pattern: when you uninstall a donor app (e.g., an abandoned module), Frappe deletes its DocTypes — even the ones you spent years customizing. app_migrator detects this and lets you migrate DocTypes to a receiver app before uninstalling the donor. Beyond that, it handles multi-bench discovery (so you don't hardcode `~/frappe-bench`), conflict analysis between overlapping apps, and AI-driven migration planning.

Phase 1 (this release) cleaned up a 2,134-line monolith into 39 per-command modules, added proper bench discovery, modernized to Python 3.14 + Frappe v16, and established a lint-clean codebase.

---

## Quick start

```bash
# Install
bench get-app app_migrator https://github.com/rogerboy38/app_migrator
bench --site mysite install-app app_migrator

# Scan for orphans before doing anything
bench --site mysite app-migrator orphans

# Full site scan
bench --site mysite app-migrator scan

# Health check
bench --site mysite app-migrator health
```

Bench discovery is automatic — it walks `~/` for benches, respects `FRAPPE_BENCH` env var.

---

## Commands

Run `bench app-migrator --help` for the full list with descriptions. Grouped by category:

### Analysis

| Command | Description |
|---|---|
| `analyze` | Analyze app structure (pyproject.toml vs setup.py) |
| `analyze-apps` | Analyze all apps in current bench |
| `apps` | List downloaded apps vs installed apps |
| `benches` | List all available benches and their apps |
| `conflicts` | Detect conflicts between apps |
| `diagnose` | Comprehensive app diagnosis for migration readiness |
| `module-diagnostic` | Quick diagnostic of module naming and orphan issues |
| `scan` | Scan site for apps, DocTypes, custom fields |

### Migration workflow

| Command | Description |
|---|---|
| `create-host` | Create a staging/host app for ping-pong migration |
| `execute` | Execute a migration plan |
| `plan` | Generate a migration plan |
| `stage` | Stage DocTypes from source app to host app |
| `unstage` | Unstage DocTypes from host to target module |
| `resolve-duplicates` | Resolve duplicate DocTypes between two apps |

### Orphan handling

| Command | Description |
|---|---|
| `orphans` | Intelligent orphaned DocType detection and repair |
| `fix-orphans` | **[DEPRECATED]** Use `orphans --fix --apply` |
| `fix-modules` | Fix orphan modules by reassigning DocTypes |
| `fix-app-field` | Fix DocTypes with NULL app field |
| `fix-json-app` | Fix JSON app field issues |
| `fix-module-names` | Fix inconsistent module naming patterns |
| `standardize-modules` | Standardize all modules to consistent naming |
| `ensure-controllers` | Create missing .py controller files for DocTypes |

### Git utilities

| Command | Description |
|---|---|
| `git-push` | Enhanced Git push with multi-remote support |
| `git-pull` | Git pull helper for Frappe apps |
| `git-info` | Show Git info for Frappe apps |

### Setup and maintenance

| Command | Description |
|---|---|
| `modernize` | Upgrade app from setup.py to pyproject.toml |
| `fix-structure` | Analyze Frappe app folder structure |
| `setup-wizard` | Interactive setup wizard |
| `quick-setup` | Quick setup with fc_ key for development |
| `api-key-setup` | Setup Frappe Cloud API key |
| `api-key-status` | Check API key status |
| `api-key-cleanup` | Cleanup API key session |
| `simple-api-setup` | Simple API key setup (no keyring) |

### Session and AI

| Command | Description |
|---|---|
| `session-start` | Start a new migration session |
| `session-status` | Check migration session status |
| `generate-plan` | Generate an intelligent migration plan |
| `predict-success` | Predict migration success probability |
| `health` | Check App Migrator health |

---

## Architecture

Bench discovery follows a priority chain: `FRAPPE_BENCH` env var → `BENCH_PATH` env var → cwd resolution (walk up looking for `apps/apps.txt` + `sites/` + `Procfile`) → fallback to `~/frappe-bench` with deprecation warning. All discovery logic lives in `commands/_shared.py`.

The CLI is click-based. `commands/__init__.py` registers all subcommands via `add_command()`. After Phase 1 cleanup it is ~261 lines (was 2,134). Each command lives in its own module.

`_shared.py` exports cross-command utilities: `ProgressTracker`, `MigrationSession`, `find_bench_root`, `discover_all_benches`, `get_current_site`, `detect_available_benches`, `get_bench_apps`.

The intelligence engine is encapsulated in the `MigrationIntelligence` class with five attribute namespaces:

- `pattern_database` — 10 risk patterns for migration failure modes
- `analysis_workflows` — 1 site-inventory analysis workflow
- `ai_prompts` — 2 NL→command routing prompts
- `risk_assessment_rules` — severity→action map (4 severity levels)
- `success_patterns` — 2 known-good migration sequences

Access via `MigrationIntelligence.pattern_database` or via an instance attribute.

Non-migration modules (payment gateway, payment security, API key managers) are archived to `_archive/` with full attribution — they are not deleted but are no longer in the active command surface.

---

## Migration target

App lives in dev sandbox. Migration target is Frappe Cloud via git transport: `git push` from the sandbox bench to the Frappe Cloud remote. The migration workflow (`plan` → `stage` → `execute` → `git-push`) is designed around this pattern. No database export/import — the app and its DocTypes move as code.

---

## Agentic use

Claude Code, Minimax, DeepSeek, and similar agents can drive full migrations via the CLI. The intelligence engine namespaces are designed to be reasoned about by AI agents — risk patterns have severity levels, success patterns have known-good sequences, and the `generate-plan` command produces structured output that agents can parse and act on.

Example agent loop:
```
bench app-migrator scan --site prod
bench app-migrator conflicts --app1 payments --app2 erpnext --all-apps
bench app-migrator generate-plan --source payments --target erpnext
bench app-migrator stage --source payments --target erpnext --doctype "Payment Method"
bench app-migrator execute --dry-run
bench app-migrator git-push
```

---

## Status

app_migrator 10.0.0-rc1 on branch `release/v10.0.0-cleanup`. Python 3.14, Frappe v16. Lint-clean (ruff reports 0 errors). 6 orphan scenario test fixtures in `tests/fixtures/orphan_scenarios/` — these are red tests Phase 2 will turn green. Base commit for this README: `951d60a`.

---

## Roadmap

- **v10.1** — Extract customer-specific commands to `app_migrator_amb_overlay` companion repo
- **v10.2** — Three-layer orphan protection (class-name correction, custom=1 flag, before_migrate cache-priming)
- **v10.3** — Cross-app field overlap detection (lessons from V13.9.0 transport)
- **v11** — Agent-driven NL command routing via intelligence engine
- **v12** — Multi-app coordinated upgrade (donor→receiver in single transaction)
- **Phase 5** — Pi/IoT fleet config sync over Raven AI agent channels (deferred)

---

## Contributing

Branch from `main`. Commit messages follow the existing convention (see `git log`). `ruff check` must pass before pushing — the full CI lint workflow is at `.github/workflows/lint.yml`. All Phase 1 cleanup commits use the pattern `type(v10): description` with `type` in `{feat, chore, refactor, test, ci, docs}`.

---

## References

- [Frappe Issue #37799](https://github.com/frappe/frappe/issues/37799) — Orphan deletion bug
- [ERPNext Naming Guidelines](https://github.com/frappe/erpnext/wiki/Naming-Guidelines)
- [Frappe v16 Migration Guide](https://github.com/frappe/frappe/blob/develop/python36/pyproject_toml_migration.md)

