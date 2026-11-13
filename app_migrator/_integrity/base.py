"""Shared types for the audit-derived integrity checks.

Design contract (inherited from W1 Phase 4 / W3):

- every check is a **pure function** over an ``Inventory`` and returns a
  ``CheckResult``;
- no check imports ``frappe`` at module import time — the package must stay
  importable without a bench (the lesson behind the P0 break);
- only the click wrapper touches the envelope / exit path.

The finding ``id`` is **stable across runs** because it is the diff key an
agent uses to tell "the same problem again" from "a new problem".
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .context import Inventory

# Worst-first ordering, used for deterministic sorting of findings.
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}

# Cap on findings carried in the envelope. The true count is always reported
# in the envelope evidence, so truncation never hides a number.
DEFAULT_FINDING_LIMIT = 200


@dataclass
class Finding:
    """One integrity problem.

    Attributes:
        id: stable identifier, e.g. ``integrity-shared-fixture-Item-substrate``.
        title: one-line human label.
        severity: one of ``high`` / ``medium`` / ``low`` / ``info``.
        description: what is wrong and why it matters.
        app: the app the finding is attributed to, when attributable.
        evidence: structured facts backing the finding (paths, counts, owners).
    """

    id: str
    title: str
    severity: str
    description: str
    app: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Envelope-shaped dict: ``id`` / ``title`` / ``severity`` / ``description``."""
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
        }
        if self.app:
            payload["app"] = self.app
        if self.evidence:
            payload["evidence"] = self.evidence
        return payload


@dataclass
class CheckResult:
    """Outcome of one check."""

    check_id: str
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def worst_severity(self) -> str:
        """Severity of the worst finding, or ``""`` when the check is clean."""
        if not self.findings:
            return ""
        return min(
            (f.severity for f in self.findings),
            key=lambda s: SEVERITY_RANK.get(s, 99),
        )

    def ordered_findings(self, limit: int = DEFAULT_FINDING_LIMIT) -> list[Finding]:
        """Findings sorted worst-first then by id, truncated to ``limit``."""
        ordered = sorted(
            self.findings,
            key=lambda f: (SEVERITY_RANK.get(f.severity, 99), f.id),
        )
        return ordered[:limit]

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats,
        }


# A check takes the inventory and returns its result. It must not mutate the
# inventory and must not touch the database or the network.
CheckFn = Callable[["Inventory"], CheckResult]


@dataclass
class CheckSpec:
    """Registry entry for one check."""

    check_id: str
    title: str
    fn: CheckFn
    description: str = ""

    def run(self, inventory: Inventory) -> CheckResult:
        return self.fn(inventory)
