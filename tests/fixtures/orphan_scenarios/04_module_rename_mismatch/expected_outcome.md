# Expected outcome — 04_module_rename_mismatch

## Setup
modules.txt was renamed to "New Module Name" but the DocType JSON still has `module: "Old Module Name"`. The mismatch causes orphan detection to fail.

## Bug symptom (current)
DocType.module does not match any declared module in modules.txt, flagging it as orphan.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect module name mismatch (DocType.module vs modules.txt)
2. Update DocType.module to "New Module Name" (from modules.txt)
3. Warn about any existing data that needs migration

## Frappe issue reference
- https://github.com/frappe/frappe/issues/37799
