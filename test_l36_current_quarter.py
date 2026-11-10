import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

blocks = []
current_fy = None
for c in range(1, ws.max_column + 1):
    v1 = ws.cell(1, c).value
    v2 = ws.cell(2, c).value
    if v1 and re.search(r'202[0-9]-[0-9]{2}', str(v1)):
        current_fy = "FY" + re.search(r'202[0-9]-[0-9]{2}', str(v1)).group(0)
    q_match = None
    for val in [v2, v1]:
        if val and re.search(r'\bQ[1-4]\b', str(val), re.I):
            q_match = re.search(r'\bQ[1-4]\b', str(val), re.I).group(0).upper()
            break
    if q_match:
        blocks.append({'fy': current_fy, 'q': q_match, 'col': c})

print(f"Total blocks in L-36: {len(blocks)}")

def get_current_quarter_measure_cols(ws, start_c, end_c):
    # Find column with "For the Quarter ended" that doesn't mention "previous" or "corresponding" or "up to"
    current_q_start_col = None
    for c in range(start_c, end_c + 1):
        for r in range(8, 11):
            txt = str(ws.cell(r, c).value or '').lower()
            if 'for the quarter ended' in txt or 'for the quarter' in txt:
                if 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                    current_q_start_col = c
                    break
        if current_q_start_col:
            break
            
    if not current_q_start_col:
        # fallback: find first numeric/measure column after particulars
        current_q_start_col = start_c + 3 # typically col 4 if block starts at 1
        
    # In the 4 columns starting at current_q_start_col, map premium, policies, lives, sum_insured
    cols = {'premium': None, 'policies': None, 'lives': None, 'sum_insured': None}
    for c in range(current_q_start_col, min(current_q_start_col + 5, end_c + 1)):
        for r in range(9, 12):
            txt = str(ws.cell(r, c).value or '').lower()
            if 'premium' in txt and cols['premium'] is None:
                cols['premium'] = c
            elif 'policies' in txt and cols['policies'] is None:
                cols['policies'] = c
            elif 'lives' in txt and cols['lives'] is None:
                cols['lives'] = c
            elif ('sum insured' in txt or 'sum assured' in txt or 'applicable' in txt) and cols['sum_insured'] is None:
                cols['sum_insured'] = c
                
    # If any is still None, fill by standard order (premium, policies, lives, sum_insured)
    expected_order = ['premium', 'policies', 'lives', 'sum_insured']
    for idx, name in enumerate(expected_order):
        if cols[name] is None and current_q_start_col + idx <= end_c:
            cols[name] = current_q_start_col + idx
            
    return current_q_start_col, cols

for b in blocks:
    start_c = b['col']
    next_blocks = [x['col'] for x in blocks if x['col'] > start_c]
    end_c = min(next_blocks) - 1 if next_blocks else ws.max_column
    q_start, m_cols = get_current_quarter_measure_cols(ws, start_c, end_c)
    print(f"Block {b['fy']} {b['q']} (cols {start_c}..{end_c}): current_q_start={q_start}, measures={m_cols}")

wb.close()
