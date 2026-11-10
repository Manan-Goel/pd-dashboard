import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

def clean_val(v):
    if v is None: return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', '-', 'NA', 'Nil', 'NIL', '.'): return 0.0
    try: return float(s)
    except: return 0.0

# Test Q11
sc = 201
ec = 226
part_col_1 = sc + 1 # 202
part_col_2 = sc + 2 # 203
p_col = 204
pol_col = 206
lives_col = 207
sa_col = 208

print("Testing Q11 with block-relative particulars columns:")
total_prem = 0.0
total_sa = 0.0
total_pol = 0
current_sec = None

for r in range(11, ws.max_row + 1):
    c2 = str(ws.cell(r, part_col_1).value or '').strip()
    c3 = str(ws.cell(r, part_col_2).value or '').strip()
    line_desc = f"{c2} {c3}".strip().lower()
    
    if 'individual single premium' in line_desc: current_sec = 'ind_single'
    elif 'group single premium' in line_desc: current_sec = 'group_single'
    elif 'individual non single' in line_desc: current_sec = 'ind_non_single'
    elif 'group non single' in line_desc: current_sec = 'group_non_single'
    elif 'renewal premium' in line_desc: current_sec = 'renewal_header'
    elif current_sec and 'renewal' in current_sec:
        if 'individual' in line_desc: current_sec = 'renewal_ind'
        elif 'group' in line_desc: current_sec = 'renewal_group'
    elif current_sec == 'renewal_header':
        if 'individual' in line_desc: current_sec = 'renewal_ind'
        elif 'group' in line_desc: current_sec = 'renewal_group'
        
    p_val = clean_val(ws.cell(r, p_col).value)
    pol_val = clean_val(ws.cell(r, pol_col).value)
    lives_val = clean_val(ws.cell(r, lives_col).value)
    sa_val = clean_val(ws.cell(r, sa_col).value)
    
    if p_val > 0 or pol_val > 0 or sa_val > 0:
        print(f"R{r:3d} [{current_sec}]: {line_desc[:35]} -> prem={p_val}, pol={pol_val}, lives={lives_val}, sa={sa_val}")
        total_prem += p_val
        total_pol += int(pol_val)
        total_sa += sa_val

print(f"\nQ11 Results -> Total Prem: {total_prem:.2f}, Total Pol: {total_pol}, Total SA: {total_sa:.2f}")

wb.close()
