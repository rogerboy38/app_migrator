# Expected outcome — 05_naming_convention_violation

## Setup
DocType named "COA AMB2" (uppercase + space + digit pattern). This violates Frappe naming guidelines which expect PascalCase without spaces or embedded digits.

## Bug symptom (current)
The name causes class naming issues and potential orphan detection false positives.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect naming convention violation (uppercase + space + digit)
2. Use Frappe rename_doc to rename to "COAAMB2" or similar compliant form
3. Update all references and permissions

## Frappe issue reference
- https://github.com/frappe/erpnext/wiki/Naming-Guidelines
