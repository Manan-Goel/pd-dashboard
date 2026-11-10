"""
Unit Detection and Normalization Engine.
Supports parenthetical context detection, word boundaries, and Devanagari Nukta variants.
Exempts non-currency metrics and schedules from monetary multipliers.
"""

import re
from typing import List, Tuple, Optional

# Word-bounded unit detection rules
UNIT_RULES = [
    (r"\b(?:crores?|crs?\.?)\b|(?:\bकरोड\b)|करोड़", "CRORES", 100.0),
    (r"\b(?:lakhs?|lacs?)\b|(?:\bलाख\b)", "LAKHS", 1.0),
    (r"(?:'000|\bthousands?\b|हजार)", "THOUSANDS", 0.01),
    (r"\bmillions?\b", "MILLIONS", 10.0),
    (r"\bbillions?\b", "BILLIONS", 10000.0),
    (r"\b(?:actuals?|in\s+(?:rs\.?|₹|inr))\b", "ACTUAL_INR", 0.00001)
]

# Non-currency schedules where numbers represent counts, percentages, or ratios
NON_CURRENCY_SCHEDULES = {
    "L-22": "RATIO",              # Analytical Ratios
    "L-31": "COUNT",              # Board of Directors & KMP count
    "L-36": "COUNT_OR_CURRENCY",  # Mixed: Lives covered (count) vs Premium (currency)
    "L-38": "RATIO_OR_CURRENCY",  # Persistency is ratio, acquisition is currency
    "L-41": "COUNT",              # Grievance count
    "L-45": "COUNT",              # Office count
}

def detect_column_group_unit(header_cells: List[Optional[str]], schedule_code: str = "") -> Tuple[str, float, bool]:
    """
    Scans header cells within a specific column group / quarter block to identify the declared unit.
    Returns:
        (unit_id, multiplier_to_lakhs, is_confirmed)
    """
    # 1. Check schedule-level non-currency rules
    if schedule_code in ("L-22", "L-41", "L-45"):
        unit_type = NON_CURRENCY_SCHEDULES[schedule_code]
        return unit_type, 1.0, True

    # 2. Inspect cells for unit declarations
    for cell in header_cells:
        if not cell:
            continue
        text = str(cell).replace("\n", " ").strip()
        
        # Check inside parentheses first: (Amount in Rs. Lakhs), (Rs in '000), (₹ in Crores)
        m = re.search(r"\((?:amount\s+in\s+|rs\.?\s+in\s+|₹\s+in\s+|in\s+)?([^\)]+)\)", text, re.I)
        target_text = m.group(1) if m else text
        
        for pat, unit_id, multiplier in UNIT_RULES:
            if re.search(pat, target_text, re.I):
                return unit_id, multiplier, True

    # Default fallback: LAKHS (1.0) with is_confirmed=False so it can be audited
    return "LAKHS", 1.0, False

def apply_unit_scale(raw_amount: Optional[float], multiplier: float, is_monetary: bool = True) -> Optional[float]:
    """
    Applies the multiplier to convert monetary amounts to standard INR Lakhs.
    Exempts non-monetary items (counts, ratios, percentages).
    """
    if raw_amount is None:
        return None
    if not is_monetary:
        return raw_amount
    return round(raw_amount * multiplier, 4)

def normalize_ratio(val: Optional[float]) -> Optional[float]:
    """
    Normalizes ratios like Solvency Ratio (e.g. 196.67% or 196.67 -> 1.9667 decimal).
    """
    if val is None:
        return None
    if val > 10.0:  # Stated as percentage e.g. 196.67
        return round(val / 100.0, 4)
    return round(val, 4)
