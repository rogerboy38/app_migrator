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
