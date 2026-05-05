# Orphan scenario fixtures

Six minimal Frappe apps that reproduce the orphan failure modes documented
in the orphan_audit_report. These are red tests — Phase 2's `orphans --fix --apply`
command must turn each one green.

| # | Scenario | Detection | Fix |
|---|---|---|---|
| 01 | Class-name capitalization | `TdsSettings` ≠ `TDSSettings` | rename class, preserve acronym |
| 02 | NULL app field in tabDocType | `app IS NULL` query | set `app = '<name>'` from JSON |
| 03 | Missing .py controller | folder has .json, no .py | generate stub with correct PascalCase |
| 04 | Module rename mismatch | DocType.module ≠ modules.txt | reassign module; warn on data |
| 05 | Naming convention violation | `name` has uppercase+space+digit | rename via Frappe rename_doc |
| 06 | Alacran-mother (donor→receiver) | overlap detected, donor.modified < receiver.modified | merge into receiver, uninstall donor |

## Running locally

These fixtures are NOT auto-installed. To test scenario 01:

```bash
bench new-site test_orphan_01
bench --site test_orphan_01 install-app tests/fixtures/orphan_scenarios/01_classname_capitalization/orphan_classname_test
bench --site test_orphan_01 migrate
# observe: TDS Settings deleted (the bug)
bench app-migrator orphans --site test_orphan_01 --fix --apply
# Phase 2 expectation: class renamed, TDS Settings survives next migrate
```

## Sources
- frappe_orphan_deletion_audit_report.md (audit)
- Frappe issue #37799
- ERPNext Naming Guidelines wiki
