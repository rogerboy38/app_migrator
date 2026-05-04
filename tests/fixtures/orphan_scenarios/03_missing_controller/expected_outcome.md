# Expected outcome — 03_missing_controller

## Setup
The doctype folder has `test_doctype.json` but NO `test_doctype.py` controller file. Frappe treats this as an orphan and deletes the DocType during migrate.

## Bug symptom (current)
Missing controller class causes Frappe orphan detection to flag this DocType.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect missing .py file for existing .json
2. Generate stub controller: `class TestDocType(Document): pass`
3. DocType has valid controller and survives migrate

## Frappe issue reference
- https://github.com/frappe/frappe/issues/37799
