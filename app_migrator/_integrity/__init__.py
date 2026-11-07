"""Audit-derived integrity checks for app_migrator.

This family exists because two real audits of production apps
(``amb_w_tds`` @ 98e7d47 and ``rnd_warehouse_management`` @ 95a913a)
found a recurring class of defect that app_migrator did not detect:
records and code that look fine in one app but break when several apps
share a bench.

Every check is bench-free and pure — it reads the filesystem and parses
files, and never imports ``frappe`` at module import time.
"""

from .base import (
    DEFAULT_FINDING_LIMIT,
    SEVERITY_RANK,
    CheckResult,
    CheckSpec,
    Finding,
)
from .context import DEFAULT_APPS_ROOT, AppInfo, HookInfo, Inventory

__all__ = [
    "AppInfo",
    "CheckResult",
    "CheckSpec",
    "DEFAULT_APPS_ROOT",
    "DEFAULT_FINDING_LIMIT",
    "Finding",
    "HookInfo",
    "Inventory",
    "SEVERITY_RANK",
    "get_checks",
]


def get_checks() -> list:
    """Return the registry of available checks.

    Imported lazily so that a broken optional check module can never take
    down the whole package import (the lesson behind the P0 break).
    """
    from .checks import CHECKS

    return list(CHECKS)
