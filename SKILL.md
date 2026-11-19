---
name: app_migrator
description: Multi-bench Frappe app migration toolkit. Detect and fix module antipatterns (same-name-module, case-mismatch orphans). Move modules between apps with full cascade (filesystem + imports + DB + fixtures). Clean donor residue after migrations. Audit orphans across DocType module references. All commands gate on dry-run by default and snapshot before any destructive change.
---

# app_migrator — Fresh Agent Onboarding

You are looking at `app_migrator`, a Frappe bench command-line tool for safely moving modules between Frappe apps. This skill brings you up to speed in under 10 minutes so you can extend it without breaking it.

## What it actually does

Frappe's standard "one app per module" assumption breaks down in real benches: apps grow organically, modules end up in the wrong app, donor apps retain stale references after partial migrations, and naming conventions drift (`Real Time Monitoring` vs `real_time_monitoring` Module Defs both pointing at the same DocType). `app_migrator` is the tool that cleans this up surgically — with snapshots, dry-runs, and gated cleanup at every step.

The codebase has been hardened over multiple production migrations (amb_w_tds, payments_core, crm_host). Lessons learned are captured both as `intelligence_engine` patterns AND as explicit safety conventions in the command implementations.

## The two antipatterns it primarily fights

### 1. Same-name-module antipattern

A Frappe app named `payments` shouldn't have a module also called `Payments` (folder `payments/payments/payments/`). Frappe imports get ambiguous, scrub() collisions happen, and `bench migrate` produces unpredictable results. **Fix:** `denest-app` — moves the module folder out, updates DB rows, rewrites import paths.

### 2. Case-mismatch orphan

Two `tabModule Def` rows like `Real Time Monitoring` (canonical) and `real_time_monitoring` (variant) that both `scrub()` to the same key. DocTypes can end up pointing at either. Frappe's JSON-DB sync via MD5 comparison can flip references back and forth on each `bench migrate`. **Fix:** `audit-orphan-doctypes` finds them; `denest-app` v6+ collapses them; `migrate-module --auto-fix-orphans` cleans during migrations.

## Command surface (v10.1.1)

50+ registered commands. Grouped by intent:

### Audit / diagnostic (read-only)
| Command | What it does |
|---|---|
| `health` | Check App Migrator health and list available functions |
| `analyze` | Analyze app structure (modern pyproject.toml vs legacy setup.py) |
| `analyze-apps` | Analyze all apps in current bench |
| `audit-app-for-antipattern` | Audit installed apps for the same-name-module antipattern |
| `audit-orphan-doctypes` | Classify orphans into STRANDED / CASE_MISMATCH / FILESYSTEM |
| `conflicts` | Detect conflicts between apps |
| `diagnose` | Comprehensive app diagnosis for migration readiness |
| `module-diagnostic` | Quick diagnostic of module naming and structure |
| `orphans` | Intelligent orphaned DocType detection |
| `scan` | Scan site for apps, doctypes, custom fields |
| `scan-donor-residue` | Scan a donor app for vestiges of moved DocTypes (read-only) |
| `verify-donor-cleanup-readiness` | Per-entry SAFE_TO_REMOVE / MIGRATE_FIRST / RECEIVER_OK_VERIFIED verdicts |
| `inspect-module` | Preview what a migrate-module would do (no edits) |
| `predict-success` | Predict migration success probability |
| `apps` | List downloaded apps vs installed apps |
| `benches` | List all available benches and their apps |

### Migration / move (destructive — gated by --apply)
| Command | What it does |
|---|---|
| `migrate-module` | Cross-app module move with full cascade (filesystem + imports + DB + fixtures + bench migrate) |
| `denest-app` | Fix the same-name-module antipattern in an existing app |
| `new-fresh-app` | Create a new Frappe app without antipattern (uv pre-flight included) |
| `modernize` | Upgrade app from traditional setup.py to pyproject.toml |
| `plan` | Generate a migration plan |
| `generate-plan` | Generate an intelligent migration plan |
| `execute` | Execute a migration plan |
| `stage` | Stage doctypes from source app to host module |
| `unstage` | Unstage doctypes from host module to source app |
| `create-host` | Create a staging/host app for ping-pong migrations |

### Cleanup / remediation (destructive — gated by --apply)
| Command | What it does |
|---|---|
| `clean-donor-residue` | Remove stale donor hooks.py entries after a migration |
| `ensure-controllers` | Create missing .py controller files for DocTypes |
| `fix-app-field` | Fix DocTypes with NULL app field |
| `fix-json-app` | Fix JSON app field issues |
| `fix-modules` | Fix orphan modules by reassigning |
| `fix-module-names` | Fix inconsistent module naming patterns |
| `fix-structure` | Analyze + fix Frappe app folder structure |
| `promote-custom-doctype` | Promote Customize Form / Custom DocType to proper app |
| `resolve-duplicates` | Resolve duplicate doctypes between two apps |
| `standardize-modules` | Standardize all modules to a consistent layout |
| `fix-orphans` | [DEPRECATED] use `orphans` instead |
| `fix-alexa-orphan`, `fix-amb-w-tds2`, `fix-kpi-factors` | One-off legacy fixes for specific known orphans |

### Session / state management
| Command | What it does |
|---|---|
| `session-start` | Start a new migration session |
| `session-status` | Check migration session status |

### Git / version helpers
| Command | What it does |
|---|---|
| `git-info` | Show Git information for Frappe apps |
| `git-pull` | Git pull helper |
| `git-push` | Enhanced git push helper with safety checks |

### Frappe Cloud API key management
| Command | What it does |
|---|---|
| `api-key-setup` | Setup Frappe Cloud API Key session |
| `api-key-status` | Check Frappe Cloud API Key status |
| `api-key-cleanup` | Cleanup Frappe Cloud API Key session |
| `simple-api-setup` | Simple API key setup (no keyring) |
| `quick-setup` | Quick setup with fc_ key for development |
| `setup-wizard` | Interactive setup wizard for App Migrator |

## Typical workflows

## Typical workflows

### Workflow A — fix an antipattern app

```bash
bench app-migrator audit-orphan-doctypes --site <site> --app <suspect_app>
bench app-migrator denest-app --site <site> --app <app_name> --apply
bench --site <site> migrate
```

### Workflow B — move a module from one app to another

```bash
# 1. Audit involved apps first
bench app-migrator audit-orphan-doctypes --site <site> --app <source_app>

# 2. Dry-run the migration (no changes; shows plan + pre-flight orphan scan)
bench app-migrator migrate-module \
    --site <site> \
    --source-app <donor> \
    --source-module "<Module Name>" \
    --target-app <receiver>

# 3. If pre-flight reports CASE_MISMATCH orphans, re-run with auto-fix
bench app-migrator migrate-module \
    --site <site> \
    --source-app <donor> \
    --source-module "<Module Name>" \
    --target-app <receiver> \
    --apply --auto-fix-orphans

# 4. Clean donor's leftover hooks.py entries
bench app-migrator clean-donor-residue \
    --site <site> \
    --donor <donor_app> \
    --receiver <receiver_app> \
    --apply
```

### Workflow C — bootstrap a clean receiver app from scratch

```bash
bench app-migrator new-fresh-app --app-name <receiver_name>
# Then proceed with Workflow B using <receiver_name> as --target-app
```

## Architectural patterns baked into every command

These conventions matter — break them and you'll re-introduce bugs that took days to find.

### 1. Default --dry-run, --apply required for changes

Every destructive command is dry-run by default. The `--apply` flag is the explicit consent. This is non-negotiable; never invert the default.

### 2. Snapshot before destructive edits

Before any filesystem or DB write, snapshot the current state to `sites/snapshots/<command>_<scope>_<timestamp>.json`. The snapshot includes enough metadata to manually reconstruct the prior state. Restore on syntax/parse failure.

### 3. AST-locate + surgical text edit

For Python source modifications (e.g. donor hooks.py): `ast.parse` to find exact line/column positions, then text-edit those positions surgically. Never `ast.unparse` the whole file (loses comments, formatting). See `clean_donor_residue._find_dict_key_lines` and `_find_fixture_value_positions` for the reference implementation.

### 4. Pre-flight before plan

Orphan/residue scans run **before** plan computation, not after destructive ops. The migrate-module v3 pre-flight is the canonical example — placed before the dry-run/apply gate so it runs in both modes (warning in dry-run, aborting in apply).

### 5. frappe.init/connect must precede DB queries

Even in dry-run mode, if any code path queries the DB, `frappe.init(site=site)` and `frappe.connect()` must run first. migrate-module v3 moved these earlier in the function specifically so pre-flight has DB access in dry-run.

### 6. JSON-DB sync awareness (denest-app v7 lesson)

After `UPDATE`ing `tabDocType.module` in the DB, you must also rewrite the corresponding doctype JSON files' `"module"` field. Otherwise Frappe's MD5-based JSON-DB sync overwrites the DB UPDATE on the next `bench migrate`. denest-app v7 made this automatic; remember it for any new command that touches DocType ownership.

### 7. safe_append_line for any text append

`_shared.safe_append_line` handles missing trailing newlines and dedupes. Use it instead of raw `open(..., 'a').write(...)` or `echo ... >>` for any structural text append. The gitignore commit (211512a) is a cautionary tale: we shipped the helper in v10.1.0-A, didn't use it for the gitignore append, and immediately got a concatenated-line bug.

### 8. Bench-wide pycache clear

When clearing `__pycache__` after edits, recurse from `bench_root` (not from `apps/<app>/`). Stale `.pyc` files in unrelated apps can shadow updated source. denest-app v5 learned this the hard way.

### 9. Retry-once on cache miss for bench migrate

After `bench migrate`, if return code is non-zero AND combined stdout+stderr contains `ModuleNotFoundError`, clear pycache bench-wide and retry once. This pattern is in migrate-module and denest-app — copy it for any new command that runs `bench migrate` as a final step.

## intelligence_engine

`app_migrator/commands/intelligence_engine.py` holds the accumulated pattern knowledge. Five namespaces:

- `pattern_database` (~16 entries) — atomic facts about specific bug patterns: detection, prevention, auto_fix algorithms, related patterns
- `analysis_workflows` — multi-step analysis pipelines
- `ai_prompts` — prompt templates for LLM-assisted diagnosis
- `risk_assessment_rules` — high_risk_factors, medium_risk_factors, severity_actions for migration scoring
- `success_patterns` — known-good migration patterns

Key patterns currently registered include `same_name_module_antipattern`, `orphan_module_case_mismatch`, `custom_flag_blocks_controller_import`, `fixtures_regenerate_drift_after_db_cleanup`, `frappe_cloud_dependency`, `api_key_storage_strategy`.

To register a new pattern, add the dict entry in `_load_pattern_database` AND wire any new risk factor into `_load_risk_assessment_rules` if relevant.

## How to extend

### Adding a new command

1. Create `app_migrator/commands/<your_command>.py`. Reference clean_donor_residue.py as the template — it shows the click decorator stack, `@pass_context` (Frappe-specific), validation phase, plan display, dry-run gate, snapshot, edit, verify pattern.
2. Function name convention: `app_migrator_<your_command>`. Click command name: `app-migrator-<your-command>`.
3. Register in `__init__.py`: add an `from .your_command import app_migrator_your_command` line near the other audit/clean imports, and an `app_migrator.add_command(...)` line near other registrations.
4. Default to `--dry-run`. Snapshot before any destructive action. Restore on parse/syntax failure.
5. Run ruff + ast.parse to verify cleanliness before commit.

### Adding a new pattern to intelligence_engine

Each pattern dict needs at minimum: `triggers` (4-ish observable signals), `symptoms` (what the user sees), `prevention` (how to avoid), `risk_score` (0-1.0), `detection_method`, `detection_query` (raw SQL or filesystem probe), `auto_fix_available` (bool), `auto_fix_algorithm`, `related_patterns` (list of pattern names).

Reference `orphan_module_case_mismatch` in intelligence_engine.py — it's the most recent pattern and shows the full shape.

## Testing strategies

### Smoke test (file-only)

```bash
EXT=py
F=app_migrator/commands/<your_command>.$EXT
python3 -c "import ast; ast.parse(open('$F').read()); print('syntax OK')"
ruff check "$F"
bench app-migrator <your-command> --help
```

### Real-data validation pattern (clean-donor-residue model)

1. **Find a real overlap** between donor and receiver apps:
```bash
   comm -12 \
     <(find apps/<donor>/<donor> -path "*/doctype/*/*.json" -printf "%f\n" | sort -u) \
     <(find apps/<receiver>/<receiver> -path "*/doctype/*/*.json" -printf "%f\n" | sort -u)
```
2. **Tag for safe revert:** `git tag pre-test-<scenario>`
3. **If no real residue, plant a controlled scenario** in donor's hooks.py with phantom targets
4. **Run --dry-run first**, validate the plan output
5. **Run --apply**, inspect git diff for surgical correctness
6. **Revert with one command:** `git reset --hard pre-test-<scenario>`

This pattern is the rigor we used for clean-donor-residue v1.0 + v1.1 against rogerboy38/crm_host (donor) vs frappe/crm (receiver).

## Common pitfalls

### Chat-client mangling of dotted Python paths

If you're editing files via terminal paste from a chat interface, paths like `obj.method()` and `module.py` may render as markdown auto-links and corrupt your paste. Workarounds:
- Construct paths via shell variables: `EXT=py; F=path/to/file.$EXT`
- Use heredocs with `<< 'EOF'` (single-quoted to disable variable expansion AND markdown rendering in some clients)
- Use base64 transfer for large multi-line code

### Anchor-based regex edits with multi-line click options

Click options with help strings containing `)` or `(` defeat naive `[^)]*` regexes. Use `ast.parse` for structural identification, paren-counting walkers for signature edits. See migrate-module v3 patch evolution for the canonical example (4 iterations to land cleanly).

### Frappe command name conventions

Frappe's bench helper looks for `commands = [...]` list at module level for command discovery. The `add_command` calls on a click group are for nesting under `app-migrator`. Both are typically needed for a command to be properly registered.

### Bench branches across machines

If app_migrator is checked out on multiple machines (e.g. UbuntuVM dev + sysmayal production), branches can diverge with unique work on each side. **UbuntuVM is the source of truth for v10.1.x development.** Sysmayal main has unique intelligence patterns (transport-arc, risk_assessment_rules) that need eventual merge — that's its own focused work, not casual cherry-pick territory.

## Quick reference

### File map
app_migrator/
├── CHANGELOG.md
├── SKILL.md
├── app_migrator/
│   └── commands/
│       ├── init.py                          # registration of all commands
│       ├── _shared.py                           # safe_append_line, MigrationSession, helpers
│       ├── audit_orphan_doctypes.py             # diagnostic
│       ├── clean_donor_residue.py               # donor cleanup
│       ├── denest_app.py                        # antipattern fix
│       ├── inspect_module.py                    # preview before migration
│       ├── intelligence_engine.py               # pattern_database + 4 other namespaces
│       ├── migrate_module.py                    # cross-app module move
│       ├── new_fresh_app.py                     # antipattern-free app creation
│       ├── verify_donor_cleanup_readiness.py    # SAFE_TO_REMOVE detection
│       └── ... (50+ commands total — see Command surface above)
└── tests/fixtures/orphan_scenarios/             # test cases for orphan detection
### Key constants

- `DICT_HOOK_SECTIONS` (in `verify_donor_cleanup_readiness.py`): list of hook section names that hold dict-style entries (doctype_class, override_doctype_class, doctype_js, etc.)
- `MODULE_REF_TABLES` (in `migrate_module.py`): list of `tabXxx` tables holding module references that need updating during a migration
- `SKIP_PATH_PATTERNS` (in `migrate_module.py` and `denest_app.py`): paths to skip when scanning for imports (`__pycache__`, `.bak`, `/archived/`, etc.)

### Snapshot location

`/home/frappe/frappe-bench/sites/snapshots/<command>_<scope>_<YYYYMMDD_HHMMSS>.json`

Each snapshot contains:
- Original file contents (for restore)
- Metadata about what was about to be changed
- Timestamp + scope identifiers

Snapshots are NOT cleaned automatically; manual housekeeping when they accumulate.

### Git conventions

- Release branches: `release/v<X>.<Y>.<Z>-<phase>` (e.g. `release/v10.0.0-cleanup`)
- Tags: `v<X>.<Y>.<Z>` (annotated tag with full release notes)
- Commit message format: `<type>(<scope>): <subject>` followed by detailed body. See v10.1.0-A through v10.1.1 commits for examples.
- The `*.bak_*` and `*.bak.*` patterns are gitignored — generated by in-place patch scripts.

## Where to get help

- The `intelligence_engine.pattern_database` entries are self-documenting — `python3 -c "from app_migrator.commands.intelligence_engine import MigrationIntelligence; mi = MigrationIntelligence(); print(list(mi.pattern_database.keys()))"`
- Each command's `--help` describes its options
- Each command's docstring (top of its `.py` file) describes intent + safety + edit strategy
- CHANGELOG.md captures the lesson trail across releases
- Snapshot files in `sites/snapshots/` are forensic data when a migration goes sideways

## Closing note

This codebase has accumulated real-world wisdom from migrations that went wrong. The safety conventions (dry-run defaults, snapshots, AST-locate edits, pre-flight before plan) exist because their absence cost engineering hours. When extending: respect the conventions, add new lessons to intelligence_engine when you find them, document validation in CHANGELOG.md, and never compromise on the snapshot-before-edit rule.
