import openpyxl
import re

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def find_quarter_blocks(ws):
    """
    Scans row 1-5 for FY and Q mentions, or finds block headers across columns.
    Returns list of dicts: {'fy': ..., 'quarter': ..., 'start_col': ..., 'end_col': ...}
    """
    # Check row 1, 2, 3, 4, 7, 8 for quarter signatures
    quarter_cols = []
    # Let's inspect rows 1 to 5 across all columns
    max_c = ws.max_column
    for c in range(1, max_c + 1):
        c1 = ws.cell(1, c).value
        c2 = ws.cell(2, c).value
        c7 = ws.cell(7, c).value
        c9 = ws.cell(9, c).value
        c10 = ws.cell(10, c).value
        c11 = ws.cell(11, c).value
        
        # Check if row 2 or 1 has Q1/Q2/Q3/Q4
        q_match = None
        for val in [c2, c1]:
            if val and re.search(r'\bQ[1-4]\b', str(val), re.I):
                q_match = re.search(r'\bQ[1-4]\b', str(val), re.I).group(0).upper()
                break
        
        # Check FY
        fy_match = None
        for val in [c1, c2]:
            if val and re.search(r'202[0-9]-[0-9]{2}', str(val)):
                fy_match = "FY" + re.search(r'202[0-9]-[0-9]{2}', str(val)).group(0)
                break
                
        if q_match:
            quarter_cols.append((c, fy_match, q_match, c1, c2))
            
    return quarter_cols

sheets_to_check = ['L-1', 'L-2', 'L-3', 'L-4', 'L-7', 'L-8', 'L-9', 'L-22', 'L-25 (i)', 'L-32', 'L-36', 'L-37', 'L-38', 'L-41', 'L-45']
for s in sheets_to_check:
    ws = wb[s]
    blocks = find_quarter_blocks(ws)
    print(f"Sheet {s}: found {len(blocks)} quarter headers: {blocks[:6]}")

wb.close()
