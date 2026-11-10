"""
Zero-Text Tabular Filter.
Enforces the strict Zero-Text Tabular Policy:
- Discards narrative prose, disclaimers, signatures, and footnotes without numbers.
- Rejects rows spanning across data columns with purely non-numeric text.
- Never drops legitimate line items with valid numerical values.
"""

import re
from typing import List, Optional

FOOTNOTE_PATTERNS = [
    r"^\s*[\*\#\$\@\~]",
    r"^\s*note\s*:\s*",
    r"^\s*notes\s*:\s*",
    r"^\s*refer\s+to\s+note",
    r"^\s*disclaimer\b",
    r"^\s*source\s*:",
    r"^\s*auditors?\s+report",
    r"^\s*schedules?\s+forming\s+part\s+of",
    r"^\s*name\s+of\s+the\s+insurer",
    r"^\s*registration\s+no",
]

def is_narrative_footnote(text: str, has_numeric_data: bool) -> bool:
    """
    Checks if a row is a footnote or narrative disclaimer.
    If the row has valid numeric metrics in data columns, it is NEVER dropped by this rule.
    """
    if has_numeric_data:
        return False
    if not text or not str(text).strip():
        return True
    t = str(text).strip().lower()
    for pat in FOOTNOTE_PATTERNS:
        if re.search(pat, t):
            return True
    # If text is long commentary paragraph (>120 chars with >15 words) and has no numbers
    if len(t) > 120 and len(t.split()) > 15:
        return True
    return False

def is_valid_tabular_row(label: str, numeric_cells: List[Optional[float]]) -> bool:
    """
    Evaluates whether a row qualifies as a valid tabular row:
    1. Must have a non-empty descriptive label.
    2. Must contain at least one valid numeric metric (or explicit 0.0) in its data columns.
    """
    if not label or not str(label).strip():
        return False
    # Check if there's at least one numeric value
    has_number = any(v is not None for v in numeric_cells)
    if not has_number:
        return False
    return True
