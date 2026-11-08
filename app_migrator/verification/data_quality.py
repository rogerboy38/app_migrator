"""L398: reject blanket `inspection_required_before_delivery` enables.

Per L398: blanket-enabling the same field on ALL doctypes is an anti-pattern
(field becomes meaningless). Selective enabling (some=1, some=0) is allowed.

Positive case (all=1): flag each as having `inspection_required_before_delivery`
reason. Negative case (selective): flag the ones with=1 with same reason but
no BLANKET keyword.
"""
from __future__ import annotations

from typing import Any, Dict, List


def verify_data_integrity(app: str, doctypes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify data integrity for the given app's doctypes.

    Returns a dict with:
      - app: the app name
      - flagged: list of {name, reason} dicts
      - doctype_count: number of doctypes inspected
    """
    flagged: List[Dict[str, Any]] = []

    if doctypes:
        blanket_count = sum(
            1 for d in doctypes
            if d.get("inspection_required_before_delivery") == 1
        )
        is_blanket = blanket_count == len(doctypes) and len(doctypes) > 1

        if is_blanket:
            for d in doctypes:
                flagged.append({
                    "name": d.get("name"),
                    "reason": (
                        "L398: BLANKET inspection_required_before_delivery "
                        "enable on ALL DOCTYPES - field becomes meaningless"
                    ),
                })
        else:
            for d in doctypes:
                if d.get("inspection_required_before_delivery") == 1:
                    flagged.append({
                        "name": d.get("name"),
                        "reason": "inspection_required_before_delivery",
                    })

    return {
        "app": app,
        "flagged": flagged,
        "doctype_count": len(doctypes),
    }
