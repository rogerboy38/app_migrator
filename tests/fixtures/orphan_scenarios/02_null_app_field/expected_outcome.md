# Expected outcome — 02_null_app_field

## Setup
The DocType JSON has `"app": null` instead of `"app": "orphan_null_app_test"`. This causes tabDocType.app to be NULL, making the DocType appear as an orphan.

## Bug symptom (current)
Orphan detection query `WHERE app IS NULL` flags this DocType for deletion.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect `app IS NULL` in tabDocType
2. Set `app = 'orphan_null_app_test'` from JSON
3. DocType is properly owned and survives migrate

## Frappe issue reference
- https://github.com/frappe/frappe/issues/37799
