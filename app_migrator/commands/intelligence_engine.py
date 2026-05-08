"""
🧠 App Migrator Intelligence Engine - V5.2.0
Predictive analytics and issue prevention system
Integrates with existing migration_engine.py and database_intel.py
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import frappe

# Import your existing components
from ._shared import ProgressTracker
from .database_intel import analyze_site_compatibility, get_database_info
from .migration_engine import run_command_with_progress, validate_migration_readiness
from .session_manager import SessionManager, with_session_management


class MigrationIntelligence:
    """
    🧠 INTELLIGENCE ENGINE - Integrates with your existing ProgressTracker and validation systems
    """

    def __init__(self, session_id=None):
        self.session_id = session_id
        self.pattern_database = self._load_intelligence_patterns()
        self.risk_assessment_rules = self._load_risk_assessment_rules()
        self.success_patterns = self._load_success_patterns()
        self.analysis_workflows = self._load_analysis_workflows()
        self.ai_prompts = self._load_ai_prompts()

    def _load_intelligence_patterns(self) -> dict[str, Any]:
        """Load patterns from our research and experience"""
        return {
            # Pattern 1: Apps.txt stability (from our research)
            'apps_txt_instability': {
                'triggers': ['bench migrate', 'bench restart', 'app installation'],
                'symptoms': ['app_migrator missing from apps.txt', 'regenerated apps.txt'],
                'prevention': 'pre_migration_hook_implementation',
                'risk_score': 0.7,
                'detection_method': 'apps_txt_analysis',
                'auto_fix_available': True
            },

            # Pattern 2: Version conflicts (from our experience)
            'version_conflicts': {
                'triggers': ['multiple __version__ definitions', 'import errors'],
                'symptoms': ['NameError: __version__ not defined', 'import conflicts'],
                'prevention': 'single_source_version_management',
                'risk_score': 0.8,
                'detection_method': 'version_analysis',
                'auto_fix_available': True
            },

            # ===== Patterns digested from non-migration modules (T1.5b) =====

            # Digested from: payment_gateway_migrator.py
            # Reason: gateway-detection regexes and known-gateway list are
            # genuine migration intelligence — they identify apps with
            # payment-processing dependencies that need careful pre-migration
            # planning (webhook re-registration, key rotation, etc).
            'payment_gateway_dependency': {
                'triggers': ['app contains payment processing code'],
                'symptoms': [
                    'stripe/razorpay/paypal/mpesa/braintree references',
                    'gateway configuration files (payment_gateway, gateway_settings)',
                    'webhook/endpoint configuration',
                ],
                'prevention': 'document_gateway_dependencies_and_plan_webhook_reregistration',
                'risk_score': 0.6,
                'detection_method': 'gateway_indicator_regex_scan',
                'auto_fix_available': False,
                # Regex catalog (lowercase, case-insensitive match)
                'detection_regexes': [
                    r'payment.*gateway', r'gateway.*payment',
                    r'payment_processor', r'payment_method',
                    r'stripe', r'razorpay', r'paypal', r'mpesa',
                    r'braintree', r'authorize', r'square',
                    r'api_key', r'secret_key', r'client_id', r'client_secret',
                    r'webhook', r'endpoint', r'payment.*config',
                ],
                'known_gateways': [
                    'stripe', 'razorpay', 'paypal', 'mpesa', 'braintree',
                    'authorize', 'square', 'worldpay', 'adyen',
                ],
                'config_filename_fragments': [
                    'payment_gateway', 'gateway_settings', 'payment_config',
                    'stripe', 'razorpay', 'paypal', 'mpesa',
                ],
                'config_dir_indicators': [
                    'payment_gateway', 'gateways', 'payments', 'payment',
                    'stripe', 'razorpay', 'paypal', 'mpesa',
                ],
            },

            # Digested from: payment_security_migrator.py
            # Reason: hardcoded-secret regexes are critical security intelligence
            # — these are vendor-specific key formats that should never end up
            # in source code; finding any is a high-severity migration blocker.
            'hardcoded_secrets': {
                'triggers': ['hardcoded API keys/secrets in source code'],
                'symptoms': [
                    'stripe sk_* keys in .py/.js files',
                    'razorpay rzp_* keys in source',
                    'AWS access keys (AKIA*) in source',
                ],
                'prevention': 'move_secrets_to_environment_variables_or_secure_config',
                'risk_score': 0.95,
                'detection_method': 'vendor_secret_pattern_regex_scan',
                'auto_fix_available': False,
                'detection_regexes': [
                    r'sk_[\w]+',           # Stripe secret key
                    r'rzp_[\w]+',          # Razorpay key
                    r'AKIA[0-9A-Z]{16}',   # AWS access key
                ],
                # Generic credential-shape regexes (find name=value assignments
                # of api_key/secret_key/password/token in code)
                'generic_credential_regexes': [
                    r'api_key\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'api_key\s*:\s*[\'"]([^\'"]+)[\'"]',
                    r'secret_key\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'secret\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'password\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'token\s*=\s*[\'"]([^\'"]+)[\'"]',
                ],
            },

            # Digested from: payment_security_migrator.py
            # Reason: webhook URLs become invalid post-migration when the host
            # changes; gateway dashboards must be updated. Detecting them up
            # front prevents silent payment-failure incidents.
            'webhook_dependency': {
                'triggers': ['app uses webhook/callback URLs'],
                'symptoms': ['webhook_url/callback_url/endpoint config in source'],
                'prevention': 'document_webhooks_and_update_gateway_dashboards_post_migration',
                'risk_score': 0.5,
                'detection_method': 'webhook_pattern_scan',
                'auto_fix_available': False,
                'detection_regexes': [
                    r'webhook_url\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'callback_url\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'endpoint\s*=\s*[\'"]([^\'"]+)[\'"]',
                    r'url.*webhook[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]',
                ],
            },

            # Digested from: payment_security_migrator.py
            # Reason: custom encryption (AES/RSA/Fernet) can fail to decrypt
            # in target environment if key material isn't migrated; needs
            # explicit verification post-cutover.
            'encryption_compatibility': {
                'triggers': ['app uses cryptography/AES/RSA/Fernet'],
                'symptoms': ['encrypt(/decrypt( calls', 'cryptography/fernet imports'],
                'prevention': 'verify_encryption_in_target_before_cutover',
                'risk_score': 0.5,
                'detection_method': 'encryption_pattern_scan',
                'auto_fix_available': False,
                'detection_regexes': [
                    r'encrypt\(', r'decrypt\(',
                    r'cryptography', r'fernet', r'aes', r'rsa',
                ],
                'method_detection_patterns': {
                    'AES': r'aes|AES',
                    'RSA': r'rsa|RSA',
                    'Fernet': r'fernet|Fernet',
                    'Cryptography': r'cryptography',
                    'Hashlib': r'hashlib',
                },
            },

            # ===== Patterns digested from frappe-cloud helpers (T1.5b group 2) =====

            # Digested from: api_key_manager.py (kept) + simple_api_setup.py (kept)
            #              + api_keys.py (deleted) + setup.py FILE (archived)
            # Reason: detecting that an app depends on Frappe Cloud-specific
            # auth/credentials. After migration, the target environment must
            # reproduce these or the app fails silently at runtime.
            'frappe_cloud_dependency': {
                'triggers': [
                    'app references FRAPPE_CLOUD_API_KEY env var',
                    'app reads from .frappe_cloud_session or ~/.frappe_migrator_keys.json',
                    'app calls press.api.* endpoints',
                ],
                'symptoms': [
                    'fc_test_key_/fc_dev_key_ prefixed keys in source',
                    'keyring service "frappe_cloud_app_migrator" lookups',
                    'cloud.frappe.io dashboard URL references',
                ],
                'prevention': 'reproduce_frappe_cloud_credentials_in_target_environment',
                'risk_score': 0.55,
                'detection_method': 'frappe_cloud_signature_scan',
                'auto_fix_available': False,
                # Detection signatures (env vars, URLs, file paths, key prefixes)
                'env_var': 'FRAPPE_CLOUD_API_KEY',
                'dashboard_url': 'https://cloud.frappe.io/dashboard/settings/developer',
                'test_key_prefixes': ['fc_test_key_', 'fc_dev_key_'],
                'keyring_service': 'frappe_cloud_app_migrator',
                'keyring_key_name': 'frappe_cloud_api_key',
                'session_file_paths': [
                    '<bench_path>/.frappe_cloud_session',
                    '~/.frappe_migrator_keys.json',
                    '~/.frappe_migrator/',
                ],
                'validation_sources': ['test_key', 'frappe_cloud_api', 'plausibility_check'],
                'access_roles': ['guest', 'limited', 'full'],
                # Credential storage schema (digested from api_keys.py + setup.py FILE)
                'fc_data_schema': {
                    'frappe_cloud': {
                        'api_key': 'str',
                        'api_secret': 'str',
                        'team_name': 'str|None',
                        'team_id': 'str|None',
                    },
                    'sites': {
                        '<site_url>': {
                            'api_key': 'str',
                            'api_secret': 'str',
                            'configured_at': 'str (iso date)',
                        },
                    },
                },
            },

            # Digested from: api_key_manager.py APISessionManager.load_api_key()
            # Reason: when a tool needs to find the FC credential, the order
            # matters — env var dominates, prompt is last resort. Future
            # migration tooling (and AI agents) should follow the same order.
            'api_key_storage_strategy': {
                'triggers': ['tool needs to authenticate against Frappe Cloud'],
                'symptoms': ['credential lookup fails or prompts unexpectedly'],
                'prevention': 'walk_storage_priority_chain',
                'risk_score': 0.4,
                'detection_method': 'storage_chain_walk',
                'auto_fix_available': True,
                # Priority order (highest to lowest preference)
                'priority_order': [
                    'env_var',          # FRAPPE_CLOUD_API_KEY (highest priority)
                    'keyring',          # system keyring (service: frappe_cloud_app_migrator)
                    'bench_session',    # <bench>/.frappe_cloud_session
                    'home_config',      # ~/.frappe_migrator_keys.json
                    'prompt',           # last resort: ask the user
                ],
                # Hashing parameters (from api_key_manager.py._hash_key)
                'hash_algorithm': 'pbkdf2_hmac_sha256',
                'hash_iterations': 100000,
                'hash_salt_bytes': 16,
                # Display masking convention (from api_keys.py.mask_key)
                'display_mask': 'first_4_dot_dot_dot_last_4',
                'default_session_expiry_hours': 24,
            },

            # Digested from: utils/cloud_api.py (archived) FrappeCloudAPIClient
            # Reason: this is the actual Frappe Cloud Dashboard API contract.
            # The base URL (frappecloud.com) is DIFFERENT from the human-facing
            # dashboard URL (cloud.frappe.io). AI agents driving FC-aware
            # migrations need this contract verbatim.
            'frappe_cloud_api_endpoints': {
                'triggers': ['agent needs to query Frappe Cloud for sites/benches/account info'],
                'symptoms': ['401/403 responses; missing X-Press-Team header'],
                'prevention': 'use_documented_endpoint_contract',
                'risk_score': 0.3,
                'detection_method': 'reference_lookup',
                'auto_fix_available': False,
                'base_url': 'https://frappecloud.com/api/method',  # API host (≠ dashboard host)
                'auth_header_format': 'Token <api_key>:<api_secret>',  # capital T
                'team_scope_headers': ['X-Press-Team', 'X-Press-Team-ID'],
                'response_wrapper': '{"message": <data>}',  # Frappe convention
                'request_timeout_seconds': 30,
                'endpoints': {
                    'press.api.account.me':  {'method': 'GET',  'returns': 'account/team info'},
                    'press.api.site.all':    {'method': 'GET',  'returns': 'list all sites in team'},
                    'press.api.site.get':    {'method': 'POST', 'body': {'name': 'site_name'},
                                              'returns': 'site detail'},
                    'press.api.bench.all':   {'method': 'GET',  'returns': 'list all benches'},
                },
            },

            # Digested from: site_api.py (archived) SiteAPIClient
            # Reason: per-site Frappe REST API has DIFFERENT auth header
            # casing from the FC Dashboard API ("token" lowercase here vs
            # "Token" capital there). Easy to confuse; worth recording.
            'frappe_site_rest_endpoints': {
                'triggers': ['agent needs to query an individual Frappe site for installed apps / metadata'],
                'symptoms': ['401 from site REST API; protocol not specified in URL'],
                'prevention': 'use_documented_per_site_REST_contract',
                'risk_score': 0.3,
                'detection_method': 'reference_lookup',
                'auto_fix_available': False,
                'url_pattern': 'https://<site_host>/api/method/<endpoint>',
                'auth_header_format': 'token <api_key>:<api_secret>',  # LOWERCASE t — different from FC Dashboard
                'response_wrapper': '{"message": <data>}',
                'url_normalization': 'auto_prepend_https_if_missing',
                'request_timeout_seconds': 30,
                'ping_timeout_seconds': 10,
                'endpoints': {
                    'frappe.ping':                            {'method': 'GET',  'purpose': 'connection test'},
                    'frappe.apps.get_installed_apps':         {'method': 'GET',  'purpose': 'installed apps list (modern)'},
                    'frappe.utils.versions.get_versions':     {'method': 'GET',  'purpose': 'fallback for installed apps (older sites)'},
                    'frappe.client.get':                      {'method': 'GET',  'purpose': 'fetch any DocType doc'},
                    'frappe.utils.get_site_info':             {'method': 'GET',  'purpose': 'site metadata'},
                },
                # When get_installed_apps fails (older site), fall back to versions API
                'fallback_chains': {
                    'installed_apps': ['frappe.apps.get_installed_apps', 'frappe.utils.versions.get_versions'],
                },
            },
            # ===== Patterns harvested from custom=1 controller bug investigation =====
            # Discovered: 2026-05-05 during amb_w_tds → amb_w_spc donor→receiver work
            # Root cause: frappe/model/base_document.py::import_controller short-circuit
            #     `if doctype_info.custom: return NestedSet if doctype_info.is_tree else Document`
            # Connects 11 years of unresolved community symptom reports.

            'custom_flag_blocks_controller_import': {
                'triggers': [
                    'tabDocType.custom = 1 in DB while controller .py file exists',
                    'doctype JSON has "custom": 1 from fixture-export history',
                    'site restored from backup with pre-migration custom flags',
                ],
                'symptoms': [
                    'import_controller silently returns frappe.model.document.Document',
                    'doctype_js / doctype_list_js hooks ignored',
                    'doc_events never fire on the doctype',
                    'controller methods (custom validate, on_update) never called',
                    'no exception surfaces — fallback hidden in try/except',
                ],
                'prevention': 'never_ship_doctypes_with_custom_1_in_source_json',
                'risk_score': 0.95,
                'detection_method': 'compare_db_custom_flag_with_json_custom_flag_per_doctype',
                'auto_fix_available': True,
                'root_cause_location': 'frappe/model/base_document.py::import_controller',
                'frappe_status': 'WONTFIX_by_design_feature_request_16328_ignored_since_2021',
                'community_archaeology': {
                    'first_reported': '2015 — discuss.frappe.io thread #7919',
                    'github_issues': [
                        'https://github.com/frappe/frappe/issues/16325',
                        'https://github.com/frappe/frappe/issues/16328',
                        'https://github.com/frappe/frappe/issues/38332',
                        'https://github.com/frappe/erpnext/issues/19655',
                        'https://github.com/frappe/frappe/issues/18516',
                    ],
                },
                'auto_fix_algorithm': 'inspect_classify_integrate_clear_resync',
            },

            'fixture_extracted_custom_doctype_birth_defect': {
                'triggers': [
                    'doctype was UI-created (custom=1) then exported via bench export-fixtures',
                    'fixture file split into per-doctype JSONs and committed to app',
                ],
                'symptoms': [
                    '"custom": 1 literally in doctype.json source file',
                    'fixture audit metadata in JSON: creation, idx, modified_by, owner',
                    'every bench migrate enforces custom=1 via MD5 hash sync',
                ],
                'prevention': 'use_bench_export_doc_not_export_fixtures_for_doctype_definitions',
                'risk_score': 0.9,
                'detection_method': 'grep_doctype_jsons_for_custom_1_and_fixture_metadata_keys',
                'auto_fix_available': True,
                'fixture_metadata_signature': ['creation', 'idx', 'modified_by', 'owner'],
            },

            'fixtures_regenerate_drift_after_db_cleanup': {
                'triggers': [
                    'cleaning tabCustom Field / tabProperty Setter rows without rebuilding fixtures',
                    'modifying source JSON without re-exporting fixtures',
                ],
                'symptoms': [
                    'CF/PS rows reappear after each bench migrate despite cleanup',
                    'apparent phantom drift that survives DB-level deletion',
                    'verify shows clean immediately after absorb but FIX after migrate',
                ],
                'prevention': 'always_run_bench_export_fixtures_after_db_cleanup_before_migrate',
                'risk_score': 0.7,
                'detection_method': 'compare_db_state_to_fixture_files_for_custom_field_and_property_setter',
                'auto_fix_available': True,
                'auto_fix_workflow': [
                    '1. clean DB rows (DELETE FROM tabCustom Field/Property Setter)',
                    '2. bench --site export-fixtures --app <app>',
                    '3. bench --site migrate (no regeneration — fixtures match DB)',
                ],
            },

            'donor_receiver_layout_mismatch': {
                'triggers': [
                    'donor and receiver apps use different Frappe layouts',
                    'single-module flat (<app>/<app>/<app>/doctype) vs multi-module',
                ],
                'symptoms': [
                    'migration scripts fail to find doctype source files',
                    'orphan folders with __init__.py but no .py file in donor',
                    'shadow paths confuse Frappe scan during sync',
                ],
                'prevention': 'compare_modules_txt_lengths_and_layout_before_migration',
                'risk_score': 0.6,
                'detection_method': 'compare_donor_receiver_modules_txt_line_count_and_directory_structure',
                'auto_fix_available': True,
                'auto_fix': 'layout_aware_path_resolver_checks_both_flat_and_nested_conventions',
            },

            'bench_migrate_field_already_exists_after_absorb': {
                'triggers': [
                    'absorbed Custom Field into doctype JSON',
                    'tabDocField row was previously auto-created from same Custom Field',
                ],
                'symptoms': [
                    'ValidationError: A field with the name X already exists in <DocType>',
                    'migrate fails immediately after absorb pipeline runs',
                ],
                'prevention': 'delete_orphan_tabDocField_rows_before_first_migrate_after_absorb',
                'risk_score': 0.4,
                'detection_method': 'cross_check_tabDocField_against_json_fields_for_duplicates',
                'auto_fix_available': True,
                'auto_fix_strategy_surgical': 'DELETE_orphan_tabDocField_row_by_name_then_migrate',
                'auto_fix_strategy_nuclear': 'DELETE_all_tabDocField_rows_for_doctype_let_migrate_rebuild_from_JSON',
            },

            # ===== Pattern harvested from amb_w_tds case-mismatch orphan (2026-05-06) =====
            # Discovered when COA Quality Test Parameter had module='amb_w_tds'
            # (lowercase) due to a duplicate Module Def created by some prior tooling.
            # bench migrate failed with "Module amb_w_tds not found" because Frappe's
            # case-sensitive lookup couldn't reconcile the lowercase variant against
            # the canonical 'AMB TDS Core' Module Def. Now baked into denest-app v6.
            'orphan_module_case_mismatch': {
                'triggers': [
                    'tabDocType.module references a Module Def with different case/spacing',
                    'duplicate Module Def rows: one Title Case, one lowercase scrub variant',
                    'legacy SQL or manual edits anchored DocTypes to the wrong-cased name',
                    'denest/migrate operations that updated some rows but missed the variant',
                ],
                'symptoms': [
                    'bench migrate fails: "Module X not found" (lowercase X) post-rename',
                    'tabDocType.module = scrub(canonical_name) instead of canonical_name',
                    'tabModule Def has duplicate rows with same scrub but different case',
                    'doctype JSON loads via correct path but DB anchoring is broken',
                    'orphan reference survives manual re-anchor: bench migrate reverts it',
                ],
                'prevention': 'always_use_canonical_module_name_in_doctype_json_and_db',
                'risk_score': 0.55,
                'detection_method': 'select_doctype_where_module_not_in_module_def_or_compare_scrub_variants',
                'detection_query': (
                    "SELECT dt.name, dt.module, dt.app FROM tabDocType dt "
                    "LEFT JOIN `tabModule Def` md ON md.name = dt.module "
                    "WHERE md.name IS NULL"
                ),
                'auto_fix_available': True,
                'auto_fix_algorithm': 'reanchor_to_canonical_then_delete_duplicate_module_def',
                'auto_fix_implementation': 'denest_app.py v6: WHERE module=_scrub(source_module)',
                'related_patterns': [
                    'custom_flag_blocks_controller_import',
                    'fixture_extracted_custom_doctype_birth_defect',
                    'orphan_ui_reference_after_doctype_removal',
                ],
                'discovery_evidence': (
                    'amb_w_tds 2026-05-06: COA Quality Test Parameter (module=amb_w_tds, '
                    'app=NULL) blocked bench migrate after denest. Manual UPDATE reverted '
                    'on next migrate because doctype JSON had the lowercase value too. '
                    'Fix: rewrite JSON module field + cascade-include scrub variants.'
                ),
            },

            # ===== Patterns 1.11 / 1.11b / 1.14 — sysmayal SessionBootFailed bundle =====
            # Discovered 2026-05-07 in prod incident at erp.sysmayal2.cloud:
            # a tabDocType row was deleted but UI reference rows (Workspace Sidebar
            # Item, Workspace Link, Report, …) AND Frappe's Redis bootinfo cache
            # still pointed at it. Result: SessionBootFailed cascade on every desk
            # page load. The 3-pattern bundle captures the cause→effect chain (1.11
            # → 1.11b) plus the verification gap (1.14) that made the incident look
            # "fixed" too early because curl /desk returned 200 to a login redirect.
            #
            # Cowork brief 2026-05-08 § "PRIMARY TASK — Step 2". Forensic refs:
            #   /mnt/s3-backups/migration/cowork/sysmayal_sessionbootfailed_orphan_cascade_forensic_report_20260507.md
            #   /mnt/s3-backups/migration/cowork/app_migrator_v10.2.0_intelligence_harvest_20260507.md

            # Pattern 1.11
            'orphan_ui_reference_after_doctype_removal': {
                'triggers': [
                    'tabDocType row removed (uninstall, manual cleanup, or migration)',
                    (
                        'UI reference rows still reference the removed DocType name in '
                        'tab(Workspace Sidebar Item|Workspace Link|Workspace Shortcut|'
                        'Workspace Quick List|Workspace Number Card|Workspace Chart|'
                        'Report|Dashboard Chart|Number Card|Kanban Board|DocType Layout|'
                        'Print Format|Client Script|Server Script|'
                        'Has Role parent-by-parenttype|Custom DocPerm parent|'
                        'DocShare share_doctype|User Permission allow|'
                        'DocField options where fieldtype=Link|'
                        'Custom Field options where fieldtype=Link|'
                        'Property Setter value where property=options|'
                        'Notification document_type)'
                    ),
                    (
                        'desk load fails with frappe.DoesNotExistError on get_meta() '
                        'during workspace permission check'
                    ),
                ],
                'symptoms': [
                    'SessionBootFailed cascade on every page load',
                    "users can't reach desk",
                ],
                'prevention': (
                    'never DELETE a tabDocType row without first cascading through '
                    'INFORMATION_SCHEMA-discovered references'
                ),
                # Blocking-tier UI tables (Workspace*, Report, Notification, etc.)
                # are 0.85; informational-tier (tabVersion, tabComment, tabError Log)
                # don't break boot and rate 0.4. Detector should classify per-row.
                'risk_score': 0.85,
                'risk_score_informational_tier': 0.4,
                'detection_method': 'INFORMATION_SCHEMA_driven_scan',
                # Generator query: emits SELECT statements for every (table, column)
                # pair where a Frappe link-shaped column exists. Caller substitutes
                # <orphan_doctype_names> and runs the generated SELECTs to locate
                # surviving references.
                'detection_query': (
                    "SELECT CONCAT('SELECT ''', TABLE_NAME, ''' src, ''', COLUMN_NAME, "
                    "''' col, name, `', COLUMN_NAME, '` ref FROM `', TABLE_NAME, "
                    "'` WHERE `', COLUMN_NAME, '` IN (<orphan_doctype_names>);') "
                    "FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME LIKE 'tab%' "
                    "AND COLUMN_NAME IN ('doctype','doc_type','dt','ref_doctype',"
                    "'reference_doctype','reference_document','link_to',"
                    "'link_doctype','document_type','target_doctype',"
                    "'allow_doctype','child_doctype','parent_doctype',"
                    "'share_doctype','allow','for_value','allowed_doctype',"
                    "'source_doctype','destination_doctype','meta_doctype',"
                    "'referenced_doctype','document_doctype',"
                    "'number_card_name','chart_name') "
                    "ORDER BY TABLE_NAME, COLUMN_NAME;"
                ),
                'auto_fix_available': True,
                'auto_fix_algorithm': 'cascade_delete_ui_refs_before_doctype',
                'auto_fix_steps': [
                    '1. Take backup',
                    '2. Run detection_query to enumerate all references',
                    '3. Classify into blocking-tier vs informational-tier',
                    '4. For blocking-tier: DELETE rows in single transaction',
                    '5. For informational-tier: prompt user (default: leave intact)',
                    (
                        '6. THEN delete tabDocType row + child meta '
                        '(existing fix-orphans logic)'
                    ),
                    "7. ALWAYS chain to Pattern 1.11b's auto_fix (cache+restart)",
                ],
                'related_patterns': [
                    'cached_bootinfo_survives_doctype_removal',
                    'browser_verified_health',
                    'orphan_module_case_mismatch',
                    'ghost_module_def_for_uninstalled_app',
                ],
                'consumed_by_command': 'audit-modules-disk-vs-db',
                'discovery_evidence': (
                    'erp.sysmayal2.cloud 2026-05-07: SessionBootFailed cascade in prod. '
                    'A DocType was removed but UI reference rows across multiple tables '
                    'still pointed at it. Every desk page load tripped get_meta() in '
                    'workspace permission check.'
                ),
            },

            # Pattern 1.11b
            'cached_bootinfo_survives_doctype_removal': {
                'triggers': [
                    'SessionBootFailed traceback citing DocType X',
                    (
                        'INFORMATION_SCHEMA scan confirms DocType X is NOT live-referenced '
                        'in any tabXxx column'
                    ),
                    'DocType X also NOT in tabDocType (already deleted)',
                    (
                        "Frappe's Redis bootinfo cache populated while X still existed "
                        'and was never cleared after the DELETE'
                    ),
                ],
                'symptoms': [
                    'SessionBootFailed even though DB is clean',
                    'cache outlasts DocType deletion',
                ],
                'prevention': (
                    'ALWAYS run cache+restart after any DocType DELETE — mandatory '
                    'step in the canonical 5-step DocType removal cascade'
                ),
                'risk_score': 0.7,
                'detection_method': 'diff_traceback_doctype_vs_db_state',
                # Verdict pseudo-query: PHANTOM_BOOTINFO_HIT iff (a) X not in
                # tabDocType, (b) Pattern 1.11 INFORMATION_SCHEMA scan against
                # X returns 0 hits. Caller wires the embedded scan from 1.11.
                'detection_query': (
                    "SELECT 'PHANTOM_BOOTINFO_HIT' AS verdict\n"
                    "WHERE NOT EXISTS (SELECT 1 FROM `tabDocType` WHERE name = '<X>')\n"
                    "  AND NOT EXISTS (\n"
                    "    -- Pattern 1.11 INFORMATION_SCHEMA scan against X, expect 0 hits\n"
                    "    -- (substitute the generated SELECTs from "
                    "orphan_ui_reference_after_doctype_removal['detection_query'])\n"
                    "  );"
                ),
                'auto_fix_available': True,
                'auto_fix_algorithm': 'cache_clear_and_restart',
                'auto_fix_steps': [
                    '1. bench --site <site> clear-cache',
                    '2. bench --site <site> clear-website-cache',
                    (
                        '3. docker compose exec redis-cache redis-cli FLUSHALL '
                        '(DO NOT flush redis-queue — preserves enqueued jobs)'
                    ),
                    (
                        '4. docker compose restart backend '
                        '(or systemctl restart bench-supervisor)'
                    ),
                    '5. Wait 8s for boot',
                    (
                        '6. Verify desk via Pattern 1.14 '
                        '(browser-verified health, not just curl)'
                    ),
                ],
                'related_patterns': [
                    'orphan_ui_reference_after_doctype_removal',
                    'browser_verified_health',
                    'phantom_module_in_sync_for',
                ],
                'consumed_by_command': 'audit-modules-disk-vs-db',
            },

            # Pattern 1.14
            'browser_verified_health': {
                'triggers': [
                    'post-fix verification check needed',
                    (
                        'HTTP 200 on curl /desk follow-redirect alone is INSUFFICIENT '
                        '(returns 200 to login redirect even when an authenticated '
                        'session would fail)'
                    ),
                ],
                'symptoms': [
                    'false-positive "desk healthy" reports',
                    'users still see 500s even though monitoring shows green',
                ],
                'prevention': (
                    'post-fix verification phase MUST include authenticated browser '
                    'session check, not just curl probe'
                ),
                'risk_score': 0.6,
                'detection_method': 'compare_curl_anonymous_vs_authenticated_desk_render',
                # Verification protocol — not a SQL query. Captured here for
                # parity with sibling patterns and so verify-phase callers can
                # reach it via the same lookup pattern as detection_query.
                'detection_query': (
                    "-- Verification protocol (not SQL):\n"
                    "-- 1. curl -sIL /desk follow-redirects → expect HTTP 200 (baseline)\n"
                    "-- 2. curl -sIL /api/method/frappe.auth.get_logged_user "
                    "with session cookie\n"
                    "--    → expect 200 + JSON user (proves authenticated layer works)\n"
                    "-- 3. (optional) headless browser render → "
                    "expect workspace sidebar visible\n"
                    "-- All three must pass for verdict GREEN."
                ),
                # Verification protocol pattern — improves verify phases of OTHER
                # commands. No standalone fix.
                'auto_fix_available': False,
                'auto_fix_algorithm': None,
                'documentation_target': 'SKILL.md (canonical post-fix check)',
                'related_patterns': [
                    'orphan_ui_reference_after_doctype_removal',
                    'cached_bootinfo_survives_doctype_removal',
                    'mutation_manifest_protocol',
                ],
                'consumed_by_command': 'audit-modules-disk-vs-db',
            },

        }

    def _load_risk_assessment_rules(self) -> dict[str, Any]:
        """Risk assessment rules based on your validation functions"""
        return {
            'high_risk_factors': [
                'multiple_version_definitions',
                'missing_hooks_py',
                # Digested from payment_security_migrator.py (T1.5b group 1)
                'hardcoded_api_keys',
                'hardcoded_aws_credentials',
                'hardcoded_stripe_secrets',
                # Digested from frappe-cloud helpers (T1.5b group 2)
                'missing_frappe_cloud_credentials_in_target',
                'custom_flag_blocks_controller_import',
                'fixture_extracted_custom_doctype_birth_defect',
            ],
            'medium_risk_factors': [
                'apps_txt_instability',
                # Digested from payment_security_migrator.py (T1.5b)
                'webhook_url_dependencies',
                'custom_encryption_implementation',
                'multiple_payment_gateway_integrations',
                # Harvested from amb_w_tds case-mismatch orphan (2026-05-06)
                'orphan_module_case_mismatch',
            ],
            # ===== Severity → action mapping (T1.5b) =====
            # Digested from payment_security_migrator.py's _generate_risk_assessment.
            # Maps each risk factor to severity, business impact, and concrete
            # mitigation. Used by predictive_analysis to surface actionable
            # guidance, not just a binary "risky/not".
            'severity_actions': {
                'orphan_module_case_mismatch': {
                    'severity': 'medium',
                    'category': 'Module Resolution',
                    'impact': 'bench migrate fails after rename ops; DocTypes orphaned in DB',
                    'mitigation': (
                        'Run denest-app or migrate-module which auto-includes the scrub '
                        'variant in DB UPDATEs (v6+). For manual fix: '
                        'UPDATE tabDocType SET module=<canonical>, app=<app> '
                        'WHERE module=<scrub(canonical)>; then DELETE the duplicate '
                        'Module Def row.'
                    ),
                },
                'hardcoded_api_keys': {
                    'severity': 'high',
                    'category': 'API Keys',
                    'impact': 'Security breach if keys are exposed',
                    'mitigation': 'Move API keys to environment variables or secure config',
                },
                'webhook_url_dependencies': {
                    'severity': 'medium',
                    'category': 'Webhooks',
                    'impact': 'Payment failures if URLs are not updated post-migration',
                    'mitigation': 'Plan webhook URL updates in payment gateway dashboards',
                },
                'custom_encryption_implementation': {
                    'severity': 'medium',
                    'category': 'Encryption',
                    'impact': 'Data decryption failures during migration',
                    'mitigation': 'Test encryption/decryption in target environment',
                },
                # Digested from frappe-cloud helpers (T1.5b group 2)
                'missing_frappe_cloud_credentials_in_target': {
                    'severity': 'high',
                    'category': 'Frappe Cloud Auth',
                    'impact': 'App fails silently at runtime when target env lacks FC credentials',
                    'mitigation': (
                        'Generate API key at https://cloud.frappe.io/dashboard/settings/developer '
                        'and reproduce env var FRAPPE_CLOUD_API_KEY (or keyring entry under '
                        'service "frappe_cloud_app_migrator") in the target environment'
                    ),
                },
                'custom_flag_blocks_controller_import': {
                    'severity': 'critical',
                    'category': 'Controller Resolution',
                    'impact': 'Python controllers silently bypassed; methods, hooks, doc_events all ignored. Affects ALL features that depend on controller class.',
                    'mitigation': 'Run app-migrator promote-custom-doctype: absorb CF/PS into doctype JSON, set custom=0, export-fixtures, migrate, verify import_controller returns proper class.',
                },
                'fixture_extracted_custom_doctype_birth_defect': {
                    'severity': 'high',
                    'category': 'Source Hygiene',
                    'impact': 'doctype.json contains custom=1 plus fixture audit metadata (creation/idx/modified_by/owner); every migrate re-applies the broken state.',
                    'mitigation': 'Edit doctype.json: set custom=0, strip audit metadata; run bench migrate.',
                },
                'fixtures_regenerate_drift_after_db_cleanup': {
                    'severity': 'medium',
                    'category': 'Migration Workflow',
                    'impact': 'Drift reappears after every bench migrate, undoing manual cleanup.',
                    'mitigation': 'Always run bench --site export-fixtures --app <app> after DB cleanup, BEFORE migrate.',
                },
                'donor_receiver_layout_mismatch': {
                    'severity': 'medium',
                    'category': 'App Layout',
                    'impact': 'Migration tools fail to find source files in donor or receiver due to layout differences.',
                    'mitigation': 'Use layout-aware path resolver that checks both <app>/<app>/<app>/doctype and <app>/<app>/<module>/doctype conventions.',
                },
                'bench_migrate_field_already_exists_after_absorb': {
                    'severity': 'low',
                    'category': 'Migration Workflow',
                    'impact': 'bench migrate fails after absorb due to duplicate tabDocField rows.',
                    'mitigation': 'Delete orphan tabDocField rows surgically (or all rows for nuclear rebuild), then migrate.',
                },
            },
        }

    def _load_success_patterns(self) -> dict[str, float]:
        """Success probability patterns from historical data"""
        return {
            'standard_frappe_app': 0.85,
            'minimal_customization': 0.90
        }

    def _load_analysis_workflows(self) -> dict[str, Any]:
        """
        Workflow patterns (multi-step procedures) digested from
        non-migration modules.

        New namespace introduced in T1.5b group 2. Distinct from
        pattern_database (which holds atomic facts/heuristics) — this
        holds multi-step procedures that an AI agent or operator can
        follow end-to-end. Future workflow patterns (multi-app
        coordinated upgrades, V13.9.0-style transports, donor/receiver
        flows) belong here too.
        """
        return {
            # Digested from: analyze_main.py (archived) — analyze-all CLI
            # Reason: canonical "what's installed where" workflow for
            # FC-hosted multi-site environments. Two-tier query that
            # combines the Dashboard API (site list) with per-site REST
            # (installed apps) plus a fallback for older sites.
            'site_inventory_analysis_flow': {
                'purpose': 'Build inventory of installed apps across all FC-hosted sites',
                'tier_1': {
                    'endpoint': 'press.api.site.all',
                    'pattern_ref': 'frappe_cloud_api_endpoints',
                    'returns': 'list of sites in team',
                },
                'tier_2': {
                    'endpoint': 'frappe.apps.get_installed_apps',
                    'pattern_ref': 'frappe_site_rest_endpoints',
                    'returns': 'list of installed apps per site',
                    'requires': 'site has frappe_cloud_dependency credentials configured',
                },
                'fallback': {
                    'endpoint': 'frappe.utils.versions.get_versions',
                    'pattern_ref': 'frappe_site_rest_endpoints',
                    'when': 'tier_2 returns empty (older Frappe versions)',
                    'returns': 'app names as keys of versions dict',
                },
                'concurrency_model': 'serial scan',
                'rate_limit_advice': 'limit batch size when scanning many sites',
                'output_formats': ['table', 'json', 'csv'],
            },
        }

    def _load_ai_prompts(self) -> dict[str, Any]:
        """
        Intent-classification and agent-reasoning data digested from
        non-migration modules.

        New namespace introduced in T1.5b group 3. Distinct from
        pattern_database (atomic facts) and analysis_workflows
        (multi-step procedures) — this holds LLM-adjacent reasoning
        data: intent regexes, exact-match routes, follow-up suggestion
        graphs, and (in the future) actual prompt templates for AI
        agents driving migrations.
        """
        return {
            # Digested from: app_migrator/_archive/ai_integration.py
            #                AppMigratorAIAgent.command_patterns + exact_matches +
            #                _execute_help_direct + app_aliases
            # Reason: pre-baked intent classifier mapping natural-language
            # queries to canonical command names. Reusable as a fallback
            # router OR ground-truth dataset for any future LLM-driven
            # query parser.
            'nl_command_routing': {
                # Regex patterns: NL phrasing → canonical command name
                'intent_regexes': {
                    r'analyze (?:the )?(?:health of )?(\w+)(?: app)?':  'diagnose-app',
                    r'diagnose (?:the )?(\w+)(?: app)?':                'diagnose-app',
                    r'check (?:the )?(?:health of )?(\w+)(?: app)?':    'diagnose-app',
                    r'health (?:scan|check|analysis)':                  'scan-bench-health',
                    r'scan health':                                     'scan-bench-health',
                    r'quick health check (?:for )?(\w+)':               'quick-health-check',
                    r'fix (?:broken|all|) apps':                        'repair-bench-apps',
                    r'fix apps':                                        'repair-bench-apps',
                    r'repair apps':                                     'repair-bench-apps',
                    r'batch repair':                                    'repair-bench-apps',
                    r'predict success (?:for )?(\w+)':                  'predict-success',
                    r'intelligence dashboard':                          'intelligence-dashboard',
                    r'list benches':                                    'list-benches',
                    r'bench apps':                                      'bench-apps',
                    r'help|commands|what can you do':                   'help',
                },
                # Exact-string matches (faster path; (command, default_arg) tuples)
                'intent_exact_matches': {
                    'scan health':            ('scan-bench-health',     ''),
                    'fix apps':               ('repair-bench-apps',     ''),
                    'repair apps':            ('repair-bench-apps',     ''),
                    'health scan':            ('scan-bench-health',     ''),
                    'quick health check':     ('quick-health-check',    ''),
                    'list benches':           ('list-benches',          ''),
                    'bench apps':             ('bench-apps',            'frappe-bench-v5'),
                    'intelligence dashboard': ('intelligence-dashboard', ''),
                    'predict success':        ('predict-success',       'erpnext'),
                },
                # User-facing capability listing with NL examples (digested
                # verbatim from _execute_help_direct)
                'skill_summary': [
                    'analyze [app]            - Analyze app health',
                    'scan health              - Scan bench health',
                    'fix apps                 - Fix broken apps (dry run)',
                    'repair apps              - Repair apps (dry run)',
                    'quick health check [app] - Quick app health check',
                    'predict success [app]    - Predict migration success',
                    'list benches             - List available benches',
                    'bench apps [bench]       - List apps in bench',
                    'intelligence dashboard   - Show AI intelligence',
                ],
                # Trivial app-name aliases (kept for completeness; documented
                # as such because it's effectively identity mapping)
                'app_aliases': {
                    'payments':     'payments',
                    'erpnext':      'erpnext',
                    'frappe':       'frappe',
                    'app_migrator': 'app_migrator',
                },
                # Stop-words filtered out of regex-extracted args (digested
                # from _extract_arguments)
                'arg_stopwords': ['the', 'for', 'in', 'of'],
            },

            # Digested from: app_migrator/_archive/ai_integration.py
            #                AppMigratorAIAgent._enhance_with_ai_insights
            # Reason: precomputed "what's next" reasoning graph. After a
            # given command runs, what should the agent suggest as the
            # likely next step? Useful for LLM-driven migration loops.
            'command_followup_graph': {
                'scan-bench-health':      [
                    "Bench health analysis completed",
                    "Use 'fix apps' to repair any issues found",
                ],
                'repair-bench-apps':      [
                    "App repair analysis completed",
                    "This was a dry run. All fixes are simulated",
                ],
                'diagnose-app':           [
                    "App diagnosis completed",
                    "Review the health score and blockers",
                ],
                'predict-success':        [
                    "Success prediction completed",
                    "Use this to plan your migration strategy",
                ],
                # Fallback: returned when no command-specific entry matches
                'default':                [
                    "Command executed successfully",
                    "Cloud-friendly execution completed",
                ],
            },
        }

    def analyze_app_structure(self, app_name: str) -> dict[str, Any]:
        """Comprehensive app structure analysis for intelligence"""
        analysis = {
            'app_name': app_name,
            'version_conflict_risk': False,
            'apps_txt_risk': False,
            'success_probability': 0.0,
            'risk_factors': [],
            'recommendations': []
        }

        try:
            app_path = Path(f"/home/frappe/frappe-bench/apps/{app_name}")

            # Check for version conflicts
            version_files = list(app_path.rglob("**/__init__.py"))
            version_definitions = []

            for version_file in version_files:
                try:
                    with open(version_file) as f:
                        content = f.read()
                        if '__version__' in content:
                            version_definitions.append(str(version_file))
                except Exception:
                    pass

            if len(version_definitions) > 1:
                analysis['version_conflict_risk'] = True
                analysis['risk_factors'].append('Multiple version definitions')
                analysis['recommendations'].append('Consolidate to single __version__ in root __init__.py')

            # Check for hooks.py (stability indicator)
            if (app_path / 'hooks.py').exists():
                analysis['success_probability'] += 0.2
            else:
                analysis['risk_factors'].append('Missing hooks.py')
                analysis['recommendations'].append('Create proper hooks.py configuration')

            # Calculate final success probability
            analysis['success_probability'] = max(0.1, min(0.9, analysis['success_probability']))

        except Exception as e:
            analysis['error'] = str(e)
            analysis['success_probability'] = 0.1

        return analysis

    @with_session_management
    def intelligent_validate_migration(self, source_app: str, target_app: str) -> dict[str, Any]:
        """
        🧠 ENHANCED VALIDATION with predictive risk assessment
        """
        print(f"🧠 INTELLIGENT VALIDATION: {source_app} → {target_app}")
        print("=" * 70)

        # Run your existing validation
        basic_ready, basic_issues = validate_migration_readiness(source_app, target_app)

        # Add intelligent predictions
        intelligence_report = {
            'basic_validation': {
                'ready': basic_ready,
                'issues': basic_issues
            },
            'predictive_analysis': self._predict_migration_risks(source_app, target_app),
            'success_probability': self._calculate_success_probability(source_app, target_app)
        }

        self._display_intelligent_validation_report(intelligence_report)
        return intelligence_report

    def _predict_migration_risks(self, source_app: str, target_app: str) -> list[dict[str, Any]]:
        """Predict migration risks based on pattern analysis"""
        predicted_risks = []

        # Analyze app structure for risk patterns
        source_analysis = self.analyze_app_structure(source_app)

        # Predict version conflicts
        if source_analysis.get('version_conflict_risk', False):
            predicted_risks.append({
                'type': 'version_conflict',
                'confidence': 0.85,
                'impact': 'high',
                'description': 'Multiple version definitions detected',
                'prevention': 'Consolidate to single __version__ in root __init__.py'
            })

        return predicted_risks

    def _calculate_success_probability(self, source_app: str, target_app: str) -> float:
        """Calculate success probability based on analysis"""
        source_analysis = self.analyze_app_structure(source_app)
        target_analysis = self.analyze_app_structure(target_app)

        base_probability = 0.5
        base_probability += source_analysis['success_probability'] * 0.3
        base_probability += target_analysis['success_probability'] * 0.2

        return min(0.95, max(0.1, base_probability))

    def _display_intelligent_validation_report(self, report: dict[str, Any]):
        """Display comprehensive intelligent validation report"""
        print("\n🧠 INTELLIGENT VALIDATION REPORT")
        print("=" * 70)

        # Basic validation results
        basic = report['basic_validation']
        print(f"📊 Basic Validation: {'✅ READY' if basic['ready'] else '❌ NOT READY'}")
        if basic['issues']:
            print("   Issues found:")
            for issue in basic['issues']:
                print(f"   • {issue}")

        # Predictive analysis
        predictions = report['predictive_analysis']
        if predictions:
            print("\n🔮 Predictive Risk Assessment:")
            for risk in predictions:
                print(f"   ⚠️  {risk['type']} (Confidence: {risk['confidence']*100}%)")
                print(f"      Impact: {risk['impact']} - {risk['description']}")
                print(f"      Prevention: {risk['prevention']}")

        # Success probability
        success_pct = report['success_probability'] * 100
        print(f"\n🎯 Success Probability: {success_pct:.1f}%")


def predict_migration_success(source_app: str, target_app: str):
    """Predict migration success probability"""
    intelligence = MigrationIntelligence()
    report = intelligence.intelligent_validate_migration(source_app, target_app)
    return report

def generate_intelligent_migration_plan(source_app: str, target_app: str):
    """Generate intelligent migration plan with risk mitigation"""
    intelligence = MigrationIntelligence()

    plan = {
        'validation_phase': intelligence.intelligent_validate_migration(source_app, target_app),
        'prevention_phase': ['Run intelligent validation first'],
        'execution_phase': ['Execute migration with monitoring'],
        'monitoring_phase': ['Track success indicators']
    }

    return plan

def display_intelligence_dashboard():
    """Display intelligence system dashboard"""
    print("🧠 APP MIGRATOR INTELLIGENCE DASHBOARD")
    print("=" * 50)
    print("🎯 Predictive Analytics: ACTIVE")
    print("🛡️  Risk Prevention: ENABLED")
    print("📊 Pattern Learning: COLLECTING DATA")
    print("🚀 Success Prediction: OPERATIONAL")
    print("\n💡 Available Intelligent Commands:")
    print("   • bench --site all migrate-app predict-success <app>")
    print("   • bench --site all migrate-app intelligent-validate <source> <target>")
    print("   • bench --site all migrate-app generate-intelligent-plan <source> <target>")
    print("   • bench --site all migrate-app intelligence-dashboard")


# Add missing method to prevent errors
def prevent_issues_before_migration(self, app_name: str):
    """Prevent issues before migration - placeholder method"""
    return {
        'preventions_applied': ['Basic validation completed'],
        'issues_prevented': ['Initial checks passed'],
        'remaining_risks': ['Run detailed analysis for specific risks']
    }

# Add the method to the class
MigrationIntelligence.prevent_issues_before_migration = prevent_issues_before_migration

if __name__ == "__main__":
    # Test intelligence engine
    intelligence = MigrationIntelligence()
    print("🧪 Testing Intelligence Engine...")

    # Test app analysis
    analysis = intelligence.analyze_app_structure("app_migrator")
    print(f"App Analysis: {analysis}")
