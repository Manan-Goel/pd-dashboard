import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

def clean_val(v):
    if v is None:
        return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', '-', 'NA', 'Nil', 'NIL', '.'):
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

# Scan blocks
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

# Define section categories by row ranges or regex
# In L-36:
# ISP: Individual Single Premium
# ISPA: Individual Single Premium Annuity
# GSP: Group Single Premium
# GSPA: Group Single Premium Annuity
# INSP: Individual Non Single Premium
# INSPA: Individual Non Single Premium Annuity
# GNSP: Group Non Single Premium
# GNSPA: Group Non Single Premium Annuity
# Renewal Ind: Renewal Individual
# Renewal Ind Annuity: Renewal Individual Annuity
# Renewal Group: Renewal Group
# Renewal Group Annuity: Renewal Group Annuity

for b in blocks:
    start_c = b['col']
    next_blocks = [x['col'] for x in blocks if x['col'] > start_c]
    end_c = min(next_blocks) - 1 if next_blocks else ws.max_column
    
    # find measure columns
    # find header row
    q_start = None
    for c in range(start_c, end_c + 1):
        for r in range(8, 11):
            txt = str(ws.cell(r, c).value or '').lower()
            if 'for the quarter ended' in txt or 'for the quarter' in txt:
                if 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                    q_start = c
                    break
        if q_start:
            break
    if not q_start:
        q_start = start_c + 3
        
    p_col = q_start
    pol_col = q_start + 1
    lives_col = q_start + 2
    sa_col = q_start + 3
    
    # Refine if headers are present
    for c in range(q_start, min(q_start + 5, end_c + 1)):
        for r in range(9, 12):
            txt = str(ws.cell(r, c).value or '').lower()
            if 'premium' in txt: p_col = c
            elif 'policies' in txt: pol_col = c
            elif 'lives' in txt: lives_col = c
            elif 'sum insured' in txt or 'sum assured' in txt or 'applicable' in txt: sa_col = c

    # Extract all rows
    ind_single_prem = 0.0
    group_single_prem = 0.0
    ind_non_single_prem = 0.0
    group_non_single_prem = 0.0
    ind_renewal_prem = 0.0
    group_renewal_prem = 0.0
    
    total_sa = 0.0
    total_pol = 0.0
    group_lives = 0.0
    
    current_sec = None
    for r in range(11, ws.max_row + 1):
        c2 = str(ws.cell(r, 2).value or '').strip()
        c3 = str(ws.cell(r, 3).value or '').strip()
        line_desc = f"{c2} {c3}".strip().lower()
        
        if 'individual single premium' in line_desc:
            current_sec = 'ind_single'
        elif 'group single premium' in line_desc:
            current_sec = 'group_single'
        elif 'individual non single' in line_desc:
            current_sec = 'ind_non_single'
        elif 'group non single' in line_desc:
            current_sec = 'group_non_single'
        elif 'renewal premium' in line_desc:
            current_sec = 'renewal_header'
        elif current_sec and 'renewal' in current_sec:
            if 'individual' in line_desc:
                current_sec = 'renewal_ind'
            elif 'group' in line_desc:
                current_sec = 'renewal_group'
        elif current_sec == 'renewal_header':
            if 'individual' in line_desc:
                current_sec = 'renewal_ind'
            elif 'group' in line_desc:
                current_sec = 'renewal_group'
                
        # Check if this row is a slab row (e.g. "from 0-10000", "above rs...")
        if 'from ' in line_desc or 'above ' in line_desc:
            p_val = clean_val(ws.cell(r, p_col).value)
            pol_val = clean_val(ws.cell(r, pol_col).value)
            lives_val = clean_val(ws.cell(r, lives_col).value)
            sa_val = clean_val(ws.cell(r, sa_col).value)
            
            total_sa += sa_val
            total_pol += pol_val
            
            if current_sec == 'ind_single':
                ind_single_prem += p_val
            elif current_sec == 'group_single':
                group_single_prem += p_val
                group_lives += lives_val
            elif current_sec == 'ind_non_single':
                ind_non_single_prem += p_val
            elif current_sec == 'group_non_single':
                group_non_single_prem += p_val
                group_lives += lives_val
            elif current_sec == 'renewal_ind':
                ind_renewal_prem += p_val
            elif current_sec == 'renewal_group':
                group_renewal_prem += p_val
                group_lives += lives_val

    total_ind = ind_single_prem + ind_non_single_prem + ind_renewal_prem
    total_grp = group_single_prem + group_non_single_prem + group_renewal_prem
    total_p = total_ind + total_grp
    total_single = ind_single_prem + group_single_prem
    total_non_single = ind_non_single_prem + group_non_single_prem + ind_renewal_prem + group_renewal_prem
    fy_prem = ind_single_prem + ind_non_single_prem + group_single_prem + group_non_single_prem
    renewal_prem = ind_renewal_prem + group_renewal_prem
    
    print(f"\n{b['fy']} {b['q']}:")
    print(f"  Total Prem: {total_p:.2f} (Ind: {total_ind:.2f}, Grp: {total_grp:.2f})")
    print(f"  First Year Prem: {fy_prem:.2f}, Single: {total_single:.2f}, Renewal: {renewal_prem:.2f}")
    print(f"  Ind Single: {ind_single_prem:.2f}, Ind Non-Single: {ind_non_single_prem:.2f}, Ind Renewal: {ind_renewal_prem:.2f}")
    print(f"  Grp Single: {group_single_prem:.2f}, Grp Non-Single: {group_non_single_prem:.2f}, Grp Renewal: {group_renewal_prem:.2f}")
    print(f"  Total Policies: {total_pol:g}, Group Lives: {group_lives:g}, Total Sum Assured: {total_sa:.2f}")

wb.close()
