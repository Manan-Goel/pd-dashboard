"""
Text Normalization and Numeric Parsing Utilities.
Adheres to strict mathematical and typing rules:
- Distinguishes missing/NA (None) from true zero (0.0).
- Strips serial number and operational prefixes without mangling names (e.g. preserves "2.5% Bonus").
- Handles Unicode minus, accounting parentheses, percentages, and trailing footnote symbols.
- Explicitly rejects bool (True/False) and NaN/Inf.
"""

import re
from typing import Optional, Union

def clean_particulars(text: Optional[str]) -> str:
    """
    Cleans row label / particulars without mangling descriptive titles.
    - Strips leading serial numbers: "1. ", "01. ", "(1) ", "1) ", "(a) ", "a. "
    - Strips accounting prefixes: "Direct - ", "Add: ", "Less: ", "Deduct: "
    - Strips trailing footnote symbols: "*", "**", "#", "$", "@", "~", "^"
    """
    if not text:
        return ""
    # Normalize internal whitespace
    t = " ".join(str(text).strip().split())
    # Strip leading serial numbers: "1. ", "01. ", "(1) ", "1) ", "(a) ", "a. ", "01 "
    # Note: ensures decimal percentages like "2.5% Guaranteed Bonus" are untouched because "." is immediately followed by a digit, not whitespace.
    t = re.sub(r"^\s*(?:\d{1,2}[\.\)]|\(\d{1,2}\)|\([a-zA-Z]\)|[a-zA-Z][\.\)]|\d{1,2})\s+", "", t)
    # Strip accounting operational prefixes
    t = re.sub(r"^(?:direct\s*[-–—]|add\s*:|less\s*:|deduct\s*:|[-–—])\s*", "", t, flags=re.I)
    # Strip trailing footnote markers
    t = re.sub(r"[\*\#\$\@\~\^]+$", "", t).strip()
    return t

def parse_numeric(val: Union[str, int, float, None]) -> Optional[float]:
    """
    Converts raw Excel values to clean float.
    Distinguishes true zero (0.0) from missing/unreported (None/NULL).
    """
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        # Check for NaN / Inf
        if val != val or val == float("inf") or val == float("-inf"):
            return None
        return float(val)

    s = str(val).strip().replace("\xa0", " ").replace(",", "")
    if not s:
        return None

    # Check for missing / not reported indicators -> NULL
    s_lower = s.lower()
    if s_lower in ("na", "n/a", "n.a.", ".", "none", "nan", "inf", "-inf", "null", "nil/na"):
        return None

    # Explicit zero representations -> 0.0
    if s in ("-", "--", "–", "—", "NIL", "Nil", "nil", "0", "0.0", "0.00"):
        return 0.0

    # Strip trailing footnote asterisks/symbols attached to numbers (e.g. "1,234*")
    s = re.sub(r"[\*\#\$\@\~]+$", "", s).strip()

    # Normalize Unicode minus signs (U+2212, U+2013, U+2014)
    s = s.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")

    # Percentage: e.g. "12.5%" -> 12.5
    is_pct = s.endswith("%")
    if is_pct:
        s = s[:-1].strip()

    # Accounting parentheses: (1234.50) -> -1234.50
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()

    try:
        f = float(s)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (ValueError, TypeError):
        return None
