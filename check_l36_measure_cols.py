import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

# Scan row 1 and 2 to find block start columns
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
for i, b in enumerate(blocks):
    start_c = b['col']
    end_c = blocks[i+1]['col'] - 1 if i+1 < len(blocks) else ws.max_column
    
    # check row 9, 10, 11 for measure headers (Premium, Policies, Lives, Sum Insured)
    measure_cols = {}
    for c in range(start_c, end_c + 1):
        for r in [9, 10, 11]:
            txt = str(ws.cell(r, c).value or '').lower()
            if 'premium' in txt and 'first year' not in txt and 'single' not in txt:
                measure_cols['premium'] = c
            elif 'no. of' in txt and 'policies' in txt:
                measure_cols['policies'] = c
            elif 'no. of' in txt and 'lives' in txt:
                measure_cols['lives'] = c
            elif 'sum' in txt and ('insured' in txt or 'assured' in txt):
                measure_cols['sum_insured'] = c
                
    print(f"Block {b['fy']} {b['q']} (cols {start_c}..{end_c}): {measure_cols}")

wb.close()
