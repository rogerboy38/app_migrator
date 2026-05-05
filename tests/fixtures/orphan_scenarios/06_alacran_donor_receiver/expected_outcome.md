# Expected outcome — 06_alacran_donor_receiver

## Setup
Two apps both define "Payment Method" DocType. When donor is uninstalled and receiver installed, both want to own the same DocType. The receiver (later install) should win.

## Bug symptom (current)
Alacran pattern: donor's older DocType is deleted when receiver is installed due to name collision without proper merge.

## Expected behavior (after Phase 2)
`bench app-migrator orphans --fix --apply` should:
1. Detect cross-app DocType overlap (Payment Method in both donor_app and receiver_app)
2. Merge donor's fields into receiver's version
3. Uninstall donor_app after merge
4. Ensure receiver_app's Payment Method survives with all required fields

## Frappe issue reference
- https://github.com/frappe/frappe/issues/37799
