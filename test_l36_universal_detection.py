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

def scan_quarter_blocks(ws):
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
        if q_match and current_fy:
            period_id = f"{current_fy}_{q_match}"
            blocks.append({
                'fy': current_fy, 'q': q_match, 'period_id': period_id, 'start_col': c
            })
    for i, b in enumerate(blocks):
        b['end_col'] = blocks[i+1]['start_col'] - 1 if i+1 < len(blocks) else ws.max_column
    return blocks

blocks = scan_quarter_blocks(ws)

for b in blocks:
    sc, ec = b['start_col'], b['end_col']
    
    # 1. Find the current quarter header column
    q_start = None
    q_next = ec + 1
    for c in range(sc, ec + 1):
        for r in range(8, 11):
            txt = str(ws.cell(r, c).value or '').lower()
            if 'for the quarter ended' in txt or 'for the quarter' in txt:
                if 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                    if q_start is None:
                        q_start = c
                elif q_start is not None and c > q_start:
                    q_next = min(q_next, c)
                    break
            elif 'up to the' in txt and q_start is not None and c > q_start:
                q_next = min(q_next, c)
                break
                
    if not q_start: q_start = sc + 3
    current_q_end = q_next - 1
    
    # 2. Find particulars columns in [sc .. q_start - 1]
    part_cols = []
    for c in range(sc, q_start):
        # check if it contains text in rows 11 to 20
        has_text = any(len(str(ws.cell(r, c).value or '').strip()) > 3 for r in range(11, 20))
        if has_text:
            part_cols.append(c)
    if not part_cols:
        part_cols = [sc + 1, sc + 2] if sc + 2 < q_start else [sc + 1]
        
    # 3. Find the 4 numeric columns in [q_start .. current_q_end]
    # Check rows 25 to 50 for cells with numbers or '-'
    num_cols = []
    for c in range(q_start, current_q_end + 1):
        for r in range(12, ws.max_row + 1):
            val = ws.cell(r, c).value
            if val is not None and (isinstance(val, (int, float)) or (isinstance(val, str) and val.strip().replace(',', '').isdigit())):
                num_cols.append(c)
                break
                
    # If num_cols has >= 4 columns, take first 4: [premium, policies, lives, sum_insured]
    # If fewer than 4 found, fill by offset
    while len(num_cols) < 4:
        next_c = (num_cols[-1] + 1) if num_cols else q_start
        num_cols.append(next_c)
        
    p_col, pol_col, lives_col, sa_col = num_cols[0], num_cols[1], num_cols[2], num_cols[3]
    
    # Now extract all rows
    ind_single = 0.0
    ind_non_single = 0.0
    group_single = 0.0
    group_non_single = 0.0
    ind_renewal = 0.0
    group_renewal = 0.0
    tot_sa = 0.0
    tot_pol = 0
    tot_lives = 0
    
    current_sec = None
    for r in range(11, ws.max_row + 1):
        part_text = " ".join(str(ws.cell(r, pc).value or '').strip() for pc in part_cols).lower()
        
        if 'individual single premium' in part_text: current_sec = 'ind_single'
        elif 'group single premium' in part_text: current_sec = 'group_single'
        elif 'individual non single' in part_text: current_sec = 'ind_non_single'
        elif 'group non single' in part_text: current_sec = 'group_non_single'
        elif 'renewal premium' in part_text: current_sec = 'renewal_header'
        elif current_sec and 'renewal' in current_sec:
            if 'individual' in part_text: current_sec = 'renewal_ind'
            elif 'group' in part_text: current_sec = 'renewal_group'
        elif current_sec == 'renewal_header':
            if 'individual' in part_text: current_sec = 'renewal_ind'
            elif 'group' in part_text: current_sec = 'renewal_group'
            
        p_val = clean_val(ws.cell(r, p_col).value)
        pol_val = clean_val(ws.cell(r, pol_col).value)
        lives_val = clean_val(ws.cell(r, lives_col).value)
        sa_val = clean_val(ws.cell(r, sa_col).value)
        
        if p_val > 100000.0: p_val /= 100000.0
        if sa_val > 1000000.0: sa_val /= 100000.0
        
        if 'from ' in part_text or 'above ' in part_text:
            tot_sa += sa_val
            tot_pol += int(pol_val)
            
            if current_sec == 'ind_single': ind_single += p_val
            elif current_sec == 'group_single':
                group_single += p_val
                tot_lives += int(lives_val)
            elif current_sec == 'ind_non_single': ind_non_single += p_val
            elif current_sec == 'group_non_single':
                group_non_single += p_val
                tot_lives += int(lives_val)
            elif current_sec == 'renewal_ind': ind_renewal += p_val
            elif current_sec == 'renewal_group':
                group_renewal += p_val
                tot_lives += int(lives_val)

    tot_p = ind_single + ind_non_single + group_single + group_non_single + ind_renewal + group_renewal
    print(f"{b['period_id']:<14} | Prem: {tot_p:<10.2f} (Ind: {ind_single+ind_non_single+ind_renewal:<8.2f}, Grp: {group_single+group_non_single+group_renewal:<8.2f}) | Pol: {tot_pol:<6d} | Lives: {tot_lives:<8d} | SA: {tot_sa:<12.2f} | Cols: P={p_col}, Pol={pol_col}, Lives={lives_col}, SA={sa_col}")

wb.close()
