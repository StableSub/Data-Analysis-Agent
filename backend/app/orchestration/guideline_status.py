from __future__ import annotations

from typing import Final

NO_ACTIVE_GUIDELINE: Final = "no_active_guideline"
NO_SELECTED_GUIDELINE: Final = "no_selected_guideline"
GUIDELINE_MISSING: Final = "guideline_missing"
NO_GUIDELINE_EVIDENCE: Final = "no_evidence"

GUIDELINE_ABSENCE_STATUSES: Final = frozenset(
    {
        NO_ACTIVE_GUIDELINE,
        NO_SELECTED_GUIDELINE,
        GUIDELINE_MISSING,
        NO_GUIDELINE_EVIDENCE,
    }
)


def is_guideline_absence_status(status: str) -> bool:
    return status in GUIDELINE_ABSENCE_STATUSES
