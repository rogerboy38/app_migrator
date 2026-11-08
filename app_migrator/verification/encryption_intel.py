"""L381: encryption-key drift detector.

Per L381: detect when site_config.encryption_key_hash differs from
site_local_db.encryption_key_hash, indicating a stale encryption key
after a site restore. This is a frequent bug pattern that leaves
restored sites with broken encrypted credentials.
"""
from __future__ import annotations

from typing import Any, Dict


def get_database_info(site: str) -> Dict[str, Any]:
    """Stub - returns the two encryption_key_hash values for a site.

    Production version reads from `site_config.json` and the local DB.
    The L381 test monkeypatches this function; the contract is that it
    returns a dict with `site_config.encryption_key_hash` and
    `site_local_db.encryption_key_hash` strings.
    """
    return {"site_config": {}, "site_local_db": {}}


def detect_encryption_key_drift(site: str) -> Dict[str, Any]:
    """Detect encryption-key drift between site_config and site_local_db.

    Returns a dict with:
      - drift_detected: bool (True iff the two hashes differ)
      - site_config_hash: the config-side hash (or None)
      - site_local_db_hash: the local-db-side hash (or None)
      - site: the site name passed in
    """
    db_info = get_database_info(site)
    site_config = db_info.get("site_config", {}) or {}
    site_local_db = db_info.get("site_local_db", {}) or {}

    config_hash = site_config.get("encryption_key_hash")
    local_hash = site_local_db.get("encryption_key_hash")

    drift_detected = config_hash != local_hash
    return {
        "drift_detected": drift_detected,
        "site_config_hash": config_hash,
        "site_local_db_hash": local_hash,
        "site": site,
    }
