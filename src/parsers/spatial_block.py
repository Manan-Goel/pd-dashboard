"""
2D Spatial Table Bounding Box Parser (SpatialTableBlock).
Fast, vectorized in-memory extraction using openpyxl iter_rows:
- Reads all sheet rows in a single batch (<0.1s per sheet).
- Dynamically discovers horizontal quarter blocks from Row 1 & 2.
- Resolves anchor rows (PARTICULARS / ITEM / DESCRIPTION).
- Block-scoped unit declarations with word boundaries.
- Coordinates derived cleanly using get_column_letter(c) + str(r).
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter
from .cleaners import clean_particulars, parse_numeric
from .unit_detector import detect_column_group_unit, apply_unit_scale
from .zero_text_filter import is_narrative_footnote, is_valid_tabular_row

class SpatialTableBlock:
    def __init__(
        self,
        sheet_name: str,
        period_id: str,
        financial_year: str,
        quarter: str,
        start_col: int,
        end_col: int,
        unit_id: str,
        multiplier: float,
        is_unit_confirmed: bool,
        anchor_row: int,
        particulars_col: int,
        col_mappings: Dict[str, int]
    ):
        self.sheet_name = sheet_name
        self.period_id = period_id
        self.financial_year = financial_year
        self.quarter = quarter
        self.start_col = start_col
        self.end_col = end_col
        self.unit_id = unit_id
        self.multiplier = multiplier
        self.is_unit_confirmed = is_unit_confirmed
        self.anchor_row = anchor_row
        self.particulars_col = particulars_col
        self.col_mappings = col_mappings  # e.g. {"quarter": col_idx, "ytd": col_idx, ...}
        self.rows: List[Dict[str, Any]] = []

def parse_worksheet_blocks(ws: Worksheet, schedule_code: str) -> List[SpatialTableBlock]:
    """
    Parses a worksheet and extracts all horizontal SpatialTableBlock objects.
    Uses 1-based indexing for row and column coordinates.
    """
    # 1. Read sheet into in-memory 2D array (<0.1s in read_only mode)
    raw_rows = [list(r) for r in ws.iter_rows(max_row=120, values_only=True)]
    if len(raw_rows) < 2:
        return []

    r1 = raw_rows[0]
    r2 = raw_rows[1]
    max_col = max(len(r) for r in raw_rows)
    total_rows = len(raw_rows)

    def get_cell(row_1b: int, col_1b: int) -> Any:
        r_idx = row_1b - 1
        c_idx = col_1b - 1
        if 0 <= r_idx < len(raw_rows) and 0 <= c_idx < len(raw_rows[r_idx]):
            return raw_rows[r_idx][c_idx]
        return None

    # 2. Discover Quarter column bounds from Row 1 and Row 2
    quarter_markers = []
    current_fy = ""
    for c_idx in range(len(r2)):
        val_r1 = r1[c_idx] if c_idx < len(r1) else None
        val_r2 = r2[c_idx] if c_idx < len(r2) else None

        if val_r1 and "FY" in str(val_r1):
            m_fy = re.search(r"FY\s*(\d{4}[-–]\d{2,4})", str(val_r1))
            if m_fy:
                current_fy = f"FY{m_fy.group(1)}"

        if val_r2 and re.match(r"^Q[1-4]\b", str(val_r2).strip(), re.I):
            q_str = str(val_r2).strip().upper()[:2]
            quarter_markers.append((c_idx + 1, current_fy, q_str))

    if not quarter_markers:
        return []

    blocks = []
    for i, (start_col, fy, qtr) in enumerate(quarter_markers):
        end_col = quarter_markers[i + 1][0] - 1 if i + 1 < len(quarter_markers) else max_col
        period_id = f"{fy}_{qtr}" if fy else f"UNKNOWN_{qtr}"

        # 3. Scan column block for unit declarations in rows 1 to 15
        block_header_cells = []
        for r in range(1, min(16, total_rows + 1)):
            for c in range(start_col, end_col + 1):
                v = get_cell(r, c)
                if v:
                    block_header_cells.append(str(v))

        unit_id, multiplier, is_confirmed = detect_column_group_unit(block_header_cells, schedule_code)

        # 4. Find anchor row and particulars column in this block
        anchor_row = None
        part_col = None

        # Priority 1: Check for explicit "PARTICULARS" or "DESCRIPTION" in block columns
        for r in range(1, min(25, total_rows + 1)):
            for c in range(start_col, end_col + 1):
                v = str(get_cell(r, c) or "").strip().upper()
                if "PARTICULARS" in v or "DESCRIPTION" in v:
                    anchor_row = r
                    part_col = c
                    break
            if anchor_row is not None:
                break

        # Priority 2: Check global columns 1-3 if block doesn't repeat description header
        if anchor_row is None:
            for r in range(1, min(20, total_rows + 1)):
                for c in range(1, min(4, max_col + 1)):
                    v = str(get_cell(r, c) or "").strip().upper()
                    if "PARTICULARS" in v or "DESCRIPTION" in v:
                        anchor_row = r
                        part_col = c
                        break
                if anchor_row is not None:
                    break

        # Priority 3: Check for "ITEM" in block columns
        if anchor_row is None:
            for r in range(1, min(20, total_rows + 1)):
                for c in range(start_col, end_col + 1):
                    v = str(get_cell(r, c) or "").strip().upper()
                    if "ITEM" in v:
                        anchor_row = r
                        # If adjacent column to the right exists, that's likely the text description
                        part_col = c + 1 if c + 1 <= end_col else c
                        break
                if anchor_row is not None:
                    break

        if anchor_row is None:
            anchor_row = 10
            part_col = start_col

        # 5. Map column sub-headers within the quarter block
        col_mappings = {}
        notes_cols = set()
        item_cols = set()

        for c in range(start_col, end_col + 1):
            combined_header = ""
            # Only scan immediate header rows right above and at the anchor row
            for r in range(max(1, anchor_row - 1), anchor_row + 1):
                cell_v = get_cell(r, c)
                if cell_v:
                    combined_header += " " + str(cell_v).strip().lower()

            combined_header = " ".join(combined_header.split())
            if any(w in combined_header for w in ("note", "notes", "schedule ref", "schedule no", "sch.")):
                notes_cols.add(c)
                continue
            if any(w in combined_header for w in ("item", "sl.", "sl no", "sr no", "no.", "sr. no.", "(1)")) and "description" not in combined_header:
                item_cols.add(c)
                continue

            if any(w in combined_header for w in ("up to the quarter", "upto the quarter", "up to the period", "upto the period")):
                if "previous" in combined_header or "prior" in combined_header or "corresponding" in combined_header:
                    col_mappings["prior_ytd"] = c
                else:
                    col_mappings["ytd"] = c
            elif any(w in combined_header for w in ("for the quarter", "quarter ended")):
                if "previous" in combined_header or "prior" in combined_header or "corresponding" in combined_header:
                    col_mappings["prior_quarter"] = c
                else:
                    col_mappings["quarter"] = c
            elif any(w in combined_header for w in ("adjusted value", "amount", "current period", "current quarter")):
                if "previous" in combined_header or "prior" in combined_header or "corresponding" in combined_header:
                    col_mappings["prior_quarter"] = c
                else:
                    col_mappings["quarter"] = c
            elif any(w in combined_header for w in ("grand total", "total")) and "business" not in combined_header:
                col_mappings["total"] = c

        # If no specific quarter column was tagged, find the column to the right of particulars
        # with the highest density of numeric values
        if "quarter" not in col_mappings and "total" not in col_mappings:
            candidate_cols = [c for c in range(start_col, end_col + 1) if c != part_col and c not in notes_cols and c not in item_cols]
            best_col = None
            max_num_count = -1
            for c in candidate_cols:
                num_count = 0
                for r in range(anchor_row + 1, min(anchor_row + 25, total_rows + 1)):
                    if parse_numeric(get_cell(r, c)) is not None:
                        num_count += 1
                if num_count > max_num_count:
                    max_num_count = num_count
                    best_col = c
            if best_col and max_num_count > 0:
                col_mappings["quarter"] = best_col

        block = SpatialTableBlock(
            sheet_name=ws.title,
            period_id=period_id,
            financial_year=fy,
            quarter=qtr,
            start_col=start_col,
            end_col=end_col,
            unit_id=unit_id,
            multiplier=multiplier,
            is_unit_confirmed=is_confirmed,
            anchor_row=anchor_row,
            particulars_col=part_col or start_col,
            col_mappings=col_mappings
        )

        # 6. Extract data rows
        empty_count = 0
        ordinal = 1
        for r in range(anchor_row + 1, total_rows + 1):
            raw_val = get_cell(r, block.particulars_col)
            raw_label = str(raw_val or "").strip()

            # Fallback if label is empty but particulars column is not column 1/2
            if not raw_label and block.particulars_col > 2:
                raw_label = str(get_cell(r, 2) or get_cell(r, 1) or "").strip()

            # Read numerical cells across block columns
            numeric_vals = {}
            raw_cells = {}
            for col_name, c_idx in block.col_mappings.items():
                c_val = get_cell(r, c_idx)
                actual_c = c_idx
                # Check for merged cell offset where numeric value is in adjacent column
                if c_val is None and (c_idx + 1) <= block.end_col and (c_idx + 1) not in block.col_mappings.values() and (c_idx + 1) != block.particulars_col:
                    adj_val = get_cell(r, c_idx + 1)
                    if adj_val is not None and parse_numeric(adj_val) is not None:
                        c_val = adj_val
                        actual_c = c_idx + 1

                numeric_vals[col_name] = parse_numeric(c_val)
                c_coord = get_column_letter(actual_c) + str(r)
                raw_cells[col_name] = (c_coord, str(c_val or ""))

            # Blank row tracking
            if not raw_label:
                empty_count += 1
                if empty_count >= 3:
                    break
                continue
            empty_count = 0

            # Data filter: ignore purely narrative headers without any numbers
            has_num = any(v is not None for v in numeric_vals.values())
            if not has_num:
                continue
            if is_narrative_footnote(raw_label, has_num):
                continue

            cleaned_lbl = clean_particulars(raw_label)
            if not cleaned_lbl:
                continue

            is_tot = 1 if re.search(r"\btotals?\b", cleaned_lbl, re.I) else 0
            is_sub = 1 if re.search(r"\bsub[- ]?totals?\b", cleaned_lbl, re.I) else 0
            part_coord = get_column_letter(block.particulars_col) + str(r)

            block.rows.append({
                "ordinal": ordinal,
                "row_idx": r,
                "raw_particulars": raw_label,
                "cleaned_particulars": cleaned_lbl,
                "is_total": is_tot,
                "is_subtotal": is_sub,
                "numeric_values": numeric_vals,
                "raw_cells": raw_cells,
                "particulars_cell_address": part_coord
            })
            ordinal += 1

        blocks.append(block)

    return blocks
