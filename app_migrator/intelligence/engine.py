"""L419 + W2(e): pattern_database re-export for the new scaffold.

Per v0.5 spec Q7a: "engine.py wraps existing MigrationIntelligence as-is".
The real bench app at apps/app_migrator/app_migrator/commands/intelligence_engine.py
holds the full ~20-entry intelligence pattern map (keyed dict form). This scaffold
re-exports a curated, radar-flag-shaped subset of those patterns in the list form
the v0.5 radar layer consumes (each entry carries a stable ``id``, ``title``,
``description``, ``severity`` per L380, and a ``detect(content)`` callable).

W2 (e): grown from the 3 W1-alpha stub patterns to the full re-export
(10 patterns) by digesting the genuine migration/security patterns from the real
``intelligence_engine.py`` pattern_database (Q1 audit source). Severity is derived
from each source pattern's ``risk_score`` via the L380 4-layer mapping:

    risk_score >= 0.90 -> critical
    risk_score >= 0.70 -> high
    risk_score >= 0.40 -> warn
    else                -> info

Each pattern's ``detect(content: str) -> bool`` lets the data-quality / preflight
layers match a source blob against the pattern without re-deriving the signature.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List


def _regex_detector(patterns: List[str]) -> Callable[[str], bool]:
    """Build a case-insensitive ``detect(content) -> bool`` from regex fragments.

    Returns True if ANY fragment matches the content. Compiled once at build
    time so repeated scans over many files stay cheap.
    """
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    def _detect(content: str) -> bool:
        if not content:
            return False
        return any(rx.search(content) for rx in compiled)

    return _detect


def severity_for_risk(risk_score: float) -> str:
    """Map a 0..1 risk score to the L380 4-layer severity enum."""
    if risk_score >= 0.90:
        return "critical"
    if risk_score >= 0.70:
        return "high"
    if risk_score >= 0.40:
        return "warn"
    return "info"


class MigrationIntelligence:
    """Curated re-export of the bench-app intelligence pattern_database.

    The real implementation (commands/intelligence_engine.py) keeps patterns in
    a dict keyed by id with migration-tooling fields. This scaffold exposes the
    radar-relevant subset as a list of envelope-shaped dicts, each with a
    ``detect`` callable, for the v0.5 radar / preflight layers.
    """

    def __init__(self) -> None:
        self.pattern_database: List[Dict[str, Any]] = self._build_patterns()

    def _build_patterns(self) -> List[Dict[str, Any]]:
        """Build the full radar pattern list (W2(e) re-export).

        Layer 1 — L419 data-quality + L394 radar (original W1-alpha stubs):
          - flt_coercion_failure (info)
          - l394_fixture_drift (warn)
          - l394_symbol_collision (high)

        Layer 2 — migration/security patterns digested from the real
        intelligence_engine.py pattern_database (W2(e) re-export):
          - apps_txt_instability (high)
          - version_conflicts (high)
          - payment_gateway_dependency (warn)
          - hardcoded_secrets (critical)
          - webhook_dependency (warn)
          - encryption_compatibility (warn)
          - frappe_cloud_dependency (warn)
        """
        return [
            # ---- Layer 1: original W1-alpha radar/data-quality stubs ----
            {
                "id": "flt_coercion_failure",
                "title": "flt coercion collapses unit-suffixed strings",
                "description": (
                    "frappe.utils.flt() silently coerces values like '10kg' "
                    "or '5.5m' to 10 or 5.5 by stripping the unit, with no warning. "
                    "Detection: pattern_database contains a flt/unit-coercion "
                    "entry that the data-quality layer can match against."
                ),
                "triggers": ["frappe.utils.flt", "unit suffix", "value-parse"],
                "symptoms": ["off-by-magnitude readings", "missing units in reports"],
                "prevention": "validate_unit_before_flt",
                "risk_score": 0.6,
                "auto_fix_available": False,
                "severity": "info",
                "detect": _regex_detector([r"flt\s*\(", r"frappe\.utils\.flt"]),
            },
            {
                "id": "l394_fixture_drift",
                "title": "fleet-canonical-fixture drift across substrate",
                "description": (
                    "L394: When a canonical fixture (e.g., journal entry template, "
                    "tax category, payment method) diverges across vpp/vpt/vm2/vm3 "
                    "substrates, transport produces inconsistent migrations. "
                    "Detection: pattern_database contains a fixture-drift entry "
                    "that the cross-substrate sync layer can match against."
                ),
                "triggers": ["fixture hash mismatch", "substrate divergence"],
                "symptoms": ["inconsistent migrations", "post-transport validate failures"],
                "prevention": "fixture_hash_audit_pre_transport",
                "risk_score": 0.7,
                "auto_fix_available": False,
                "severity": "warn",
                "detect": _regex_detector([r"fixtures?", r"fixture.*hash"]),
            },
            {
                "id": "l394_symbol_collision",
                "title": "cross-app Python symbol collision",
                "description": (
                    "L394: Two installed apps (erpnext, hrms, custom_*) declaring "
                    "the same Python symbol (function, class, constant) at module "
                    "load time causes silent override and runtime ImportError. "
                    "Detection: pattern_database contains a symbol-collision entry "
                    "that the preflight module-collision layer can match against."
                ),
                "triggers": ["duplicate symbol across apps", "module load ImportError"],
                "symptoms": ["silent override", "intermittent ImportError", "wrong-version win"],
                "prevention": "module_collision_preflight",
                "risk_score": 0.8,
                "auto_fix_available": False,
                "severity": "high",
                "detect": _regex_detector([r"ImportError", r"duplicate.*symbol"]),
            },
            # ---- Layer 2: re-export from intelligence_engine.py (W2(e)) ----
            {
                "id": "apps_txt_instability",
                "title": "apps.txt instability across bench migrate/restart",
                "description": (
                    "apps.txt is regenerated by bench migrate/restart, silently "
                    "dropping app_migrator (or other non-standard apps) from the "
                    "install list. Detection: source references apps.txt mutation "
                    "or app-install hooks that can regenerate the manifest."
                ),
                "triggers": ["bench migrate", "bench restart", "app installation"],
                "symptoms": ["app_migrator missing from apps.txt", "regenerated apps.txt"],
                "prevention": "pre_migration_hook_implementation",
                "risk_score": 0.7,
                "auto_fix_available": True,
                "severity": severity_for_risk(0.7),
                "detect": _regex_detector([r"apps\.txt", r"bench\s+migrate"]),
            },
            {
                "id": "version_conflicts",
                "title": "multiple __version__ definitions conflict",
                "description": (
                    "Multiple __version__ definitions across an app's modules "
                    "produce NameError / import conflicts at load time. Detection: "
                    "source declares __version__ in more than one place."
                ),
                "triggers": ["multiple __version__ definitions", "import errors"],
                "symptoms": ["NameError: __version__ not defined", "import conflicts"],
                "prevention": "single_source_version_management",
                "risk_score": 0.8,
                "auto_fix_available": True,
                "severity": severity_for_risk(0.8),
                "detect": _regex_detector([r"__version__"]),
            },
            {
                "id": "payment_gateway_dependency",
                "title": "payment-gateway processing dependency",
                "description": (
                    "App contains payment-processing code (stripe/razorpay/paypal/"
                    "mpesa/braintree) requiring webhook re-registration and key "
                    "rotation on migration. Detection: gateway-indicator regexes "
                    "match the source."
                ),
                "triggers": ["app contains payment processing code"],
                "symptoms": [
                    "stripe/razorpay/paypal/mpesa/braintree references",
                    "gateway configuration files",
                    "webhook/endpoint configuration",
                ],
                "prevention": "document_gateway_dependencies_and_plan_webhook_reregistration",
                "risk_score": 0.6,
                "auto_fix_available": False,
                "severity": severity_for_risk(0.6),
                "detect": _regex_detector([
                    r"payment.*gateway", r"gateway.*payment",
                    r"stripe", r"razorpay", r"paypal", r"mpesa", r"braintree",
                ]),
            },
            {
                "id": "hardcoded_secrets",
                "title": "hardcoded API keys/secrets in source",
                "description": (
                    "Vendor-format secret keys (Stripe sk_*, Razorpay rzp_*, AWS "
                    "AKIA*) committed to source are a high-severity migration "
                    "blocker. Detection: vendor secret-shape regexes match the "
                    "source."
                ),
                "triggers": ["hardcoded API keys/secrets in source code"],
                "symptoms": [
                    "stripe sk_* keys in .py/.js files",
                    "razorpay rzp_* keys in source",
                    "AWS access keys (AKIA*) in source",
                ],
                "prevention": "move_secrets_to_environment_variables_or_secure_config",
                "risk_score": 0.95,
                "auto_fix_available": False,
                "severity": severity_for_risk(0.95),
                "detect": _regex_detector([
                    r"sk_[\w]+", r"rzp_[\w]+", r"AKIA[0-9A-Z]{16}",
                ]),
            },
            {
                "id": "webhook_dependency",
                "title": "webhook/callback URL dependency",
                "description": (
                    "App uses webhook/callback URLs that become invalid when the "
                    "host changes post-migration; gateway dashboards must be "
                    "updated. Detection: webhook/callback URL assignments in source."
                ),
                "triggers": ["app uses webhook/callback URLs"],
                "symptoms": ["webhook_url/callback_url/endpoint config in source"],
                "prevention": "document_webhooks_and_update_gateway_dashboards_post_migration",
                "risk_score": 0.5,
                "auto_fix_available": False,
                "severity": severity_for_risk(0.5),
                "detect": _regex_detector([
                    r"webhook_url", r"callback_url", r"webhook",
                ]),
            },
            {
                "id": "encryption_compatibility",
                "title": "custom encryption compatibility risk",
                "description": (
                    "App uses cryptography/AES/RSA/Fernet that can fail to decrypt "
                    "in the target environment if key material isn't migrated. "
                    "Detection: encrypt/decrypt calls or crypto imports in source."
                ),
                "triggers": ["app uses cryptography/AES/RSA/Fernet"],
                "symptoms": ["encrypt(/decrypt( calls", "cryptography/fernet imports"],
                "prevention": "verify_encryption_in_target_before_cutover",
                "risk_score": 0.5,
                "auto_fix_available": False,
                "severity": severity_for_risk(0.5),
                "detect": _regex_detector([
                    r"encrypt\(", r"decrypt\(", r"cryptography", r"fernet",
                ]),
            },
            {
                "id": "frappe_cloud_dependency",
                "title": "Frappe Cloud credential/auth dependency",
                "description": (
                    "App depends on Frappe Cloud-specific auth (FRAPPE_CLOUD_API_KEY "
                    "env var, .frappe_cloud_session, press.api.* endpoints) that the "
                    "target environment must reproduce or the app fails silently. "
                    "Detection: Frappe Cloud signatures in source."
                ),
                "triggers": [
                    "app references FRAPPE_CLOUD_API_KEY env var",
                    "app reads from .frappe_cloud_session",
                    "app calls press.api.* endpoints",
                ],
                "symptoms": [
                    "fc_test_key_/fc_dev_key_ prefixed keys in source",
                    "cloud.frappe.io dashboard URL references",
                ],
                "prevention": "reproduce_frappe_cloud_credentials_in_target_environment",
                "risk_score": 0.55,
                "auto_fix_available": False,
                "severity": severity_for_risk(0.55),
                "detect": _regex_detector([
                    r"FRAPPE_CLOUD_API_KEY", r"frappe_cloud_session",
                    r"press\.api", r"fc_(test|dev)_key_",
                ]),
            },
        ]
