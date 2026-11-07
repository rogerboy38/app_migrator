"""Registry of audit-derived integrity checks.

Checks are **auto-discovered**: every module in this package that exposes a
``CHECK_SPEC`` (a :class:`~app_migrator.commands._integrity.base.CheckSpec`)
is registered automatically, so adding a check is one file and no wiring.

Each module is imported inside a guard. A broken optional check must never
take down the whole package import — that is the lesson behind the P0 break
where a single stray import made every ``bench app-migrator`` command fail.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import List

from ..base import CheckSpec

logger = logging.getLogger("app_migrator")

CHECKS: List[CheckSpec] = []


def _register_module(module_name: str) -> None:
    """Import one check module and register its ``CHECK_SPEC`` if present."""
    try:
        module = importlib.import_module(f"{__name__}.{module_name}")
    except Exception:  # pragma: no cover - defensive
        logger.exception("integrity check module %s failed to import; skipping it", module_name)
        return
    spec = getattr(module, "CHECK_SPEC", None)
    if isinstance(spec, CheckSpec):
        CHECKS.append(spec)
        return
    logger.warning("integrity check module %s exposes no CHECK_SPEC; skipping it", module_name)


for _module_info in sorted(
    m.name for m in pkgutil.iter_modules(__path__) if not m.name.startswith("_")
):
    _register_module(_module_info)

# Stable, deterministic order for humans and for the envelope.
CHECKS.sort(key=lambda spec: spec.check_id)

__all__ = ["CHECKS"]
