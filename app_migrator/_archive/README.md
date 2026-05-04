# `_archive/` — historical record of digested non-migration modules

This directory holds modules that were originally part of `app_migrator`
but were either non-migration concerns or have been digested into
`app_migrator/commands/intelligence_engine.py`'s pattern database.

Modules here are **not loaded at runtime**. They are kept for historical
attribution: when an intelligence pattern in the engine cites a source,
the original implementation lives here.

Per Hugh's launch brief §1.1 (V10.0.0 cleanup, T1.5b): extract first,
archive — do not delete. The intelligence (heuristics, error patterns,
detection regexes, risk-assessment rules) was extracted into
`intelligence_engine.py`'s `pattern_database` and `risk_assessment_rules`
with comments citing each source module.

## Contents

### Group 1 — payment modules (T1.5b, archived 2026-05-03)

- **`payment_gateway_migrator.py`** — gateway detection (regex catalog
  for stripe/razorpay/paypal/mpesa/braintree/etc, file/directory name
  indicators, supported-gateway list).
  Digested into: `intelligence_engine.py` →
  `pattern_database['payment_gateway_dependency']`.

- **`payment_security_migrator.py`** — security analysis (hardcoded-secret
  vendor regexes for sk_*, rzp_*, AKIA*; generic credential regexes;
  webhook URL detection; encryption method detection; severity-action
  mapping).
  Digested into: `intelligence_engine.py` →
  `pattern_database['hardcoded_secrets']`,
  `pattern_database['webhook_dependency']`,
  `pattern_database['encryption_compatibility']`,
  `risk_assessment_rules['severity_actions']`.

- **`test_payment_migration_suite.py`** — test driver for the two
  migrators above. Archived alongside its subjects.

- **`test_payment_security.py`** — second test driver (was in
  `tests/legacy_command_tests/`); Minimax relocated to keep tests
  beside the modules they exercise.

### Group 2 — frappe-cloud helpers (T1.5b, archived 2026-05-03)

Group 2 followed an E-style audit (verdict-by-module) before any edits.
Two modules in the original target list were KEPT after audit because
they have live consumers (api_key_manager.py: 3 live CLIs + git_pull.py
uses APISessionManager; simple_api_setup.py: live `simple-api-setup`
CLI). The audit also surfaced an orphan-cluster (4 files) whose only
callers were each other — they were archived as a closed subgraph.

Two pure orphan duplicates (api_keys.py, api_key_setup.py) were
**deleted outright** rather than archived — they have no unique
intelligence vs api_key_manager.py and no historical value.

Files archived:

- **`analyze_main.py`** — defined the unregistered `analyze-all` CLI.
  Two-tier site inventory flow (FC Dashboard API + per-site REST +
  versions fallback). Output formats table/json/csv.
  Digested into: `intelligence_engine.py` →
  `analysis_workflows['site_inventory_analysis_flow']` (NEW namespace
  introduced in this group).

- **`setup_FILE.py`** (renamed from `setup.py` to disambiguate from the
  `setup/` package directory that holds the canonical `setup-wizard`).
  Defined an unregistered `setup-frappe-cloud`, `setup-site-api`, and a
  COLLIDING `setup-wizard`. The collision was the 4th-wizard footgun
  flagged in T1.7. Onboarding UX content (where to click in FC
  Dashboard / Frappe site UI) and the credential validation
  flow were digested into:
  `pattern_database['frappe_cloud_dependency']` (fc_data schema).

- **`site_api.py`** — `SiteAPIClient` for per-site Frappe REST API
  (frappe.* endpoints). Unregistered `test-connection` and
  `get-installed-apps` CLIs. Digested into:
  `pattern_database['frappe_site_rest_endpoints']` (URL pattern, lowercase
  `token` auth header — distinct from FC Dashboard's `Token`,
  endpoint catalog, fallback chain, URL normalization).

- **`cloud_api.py`** (was `app_migrator/utils/cloud_api.py`) —
  `FrappeCloudAPIClient` for FC Dashboard API (press.api.* endpoints).
  Unregistered `list-sites` and `get-account-info` CLIs.
  Digested into: `pattern_database['frappe_cloud_api_endpoints']`
  (base URL `https://frappecloud.com/api/method` ≠ dashboard URL,
  capital `Token` auth, X-Press-Team headers, response wrapper,
  endpoint catalog).

Files DELETED (not archived — pure orphan duplicates):

- **`api_keys.py`** — defined a colliding `api-key-status` CLI (never
  registered) plus thin `load_keys`/`save_keys` helpers. Orphan-cluster
  callers only (analyze_main, setup.py FILE, site_api, cloud_api). All
  three of those callers were themselves orphans, now archived.
  Intelligence already covered by api_key_manager.py (kept).

- **`api_key_setup.py`** — defined unregistered duplicates of
  `api-key-setup`, `api-key-status`, `api-key-remove`. No external
  consumers. Pure orphan; api_key_manager.py is the live equivalent.

Files KEPT IN PLACE (in `app_migrator/commands/`):

- **`api_key_manager.py`** — live; registers api-key-{setup,status,cleanup};
  `APISessionManager` class is used by `git_pull.py`.
- **`simple_api_setup.py`** — live; registers `simple-api-setup`. Per
  Hugh's mental model (agentic FC auth = real value), kept for now.
  May move to a future `app_frappe_cloud_helper` companion app.
