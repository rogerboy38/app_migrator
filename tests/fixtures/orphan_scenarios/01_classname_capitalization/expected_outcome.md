# Expected outcome — 01_classname_capitalization

## Setup
The DocType "TDS Settings" has a Python controller class named `TdsSettings` instead of the correct `TDSSettings`. Frappe's orphan detection uses case-insensitive comparison and deletes the DocType.

## Reproducer
bench --site test_orphan_01 new-site 2>/dev/null || true
bench --site local install-app tests/fixtures/orphan_scenarios/01_classname_capitalization/orphan_classname_test 2>/dev/null || true
bench --site local migrate

## Bug symptom (current)
TDS Settings DocType is deleted during migrate because TdsSettings ≠ TDSSettings.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect class name mismatch (TdsSettings vs expected TDSSettings)
2. Rename class to TDSSettings preserving TDS acronym
3. TDS Settings survives next migrate

## Frappe issue reference
- https://github.com/frappe/frappe/issues/37799
- https://github.com/frappe/erpnext/wiki/Naming-Guidelines
