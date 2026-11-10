"""
Comprehensive Test Extractor for Acko Life Insurance 64 Standardized Metrics.
Extracts data across all 12 quarters:
FY2023-24 Q1..Q4, FY2024-25 Q1..Q4, FY2025-26 Q1..Q4.
"""

import openpyxl
import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

FILE_PATH = "ACKO_LIFE_INSURANCE_Consolidated.xlsx"
COMPANY_ID = "ACKO_LIFE"

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

def clean_int(v):
    return int(round(clean_val(v)))

def clean_str(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in ('-', 'NA', 'Nil', 'NIL') else s

def scan_quarter_blocks(ws):
    """Detects all quarter blocks across row 1 & 2."""
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
            period_id = f"{current_fy}_{q_match}" if current_fy else f"UNKNOWN_{q_match}"
            blocks.append({
                'fy': current_fy,
                'quarter': q_match,
                'period_id': period_id,
                'start_col': c
            })
            
    # Assign end_col
    for i, b in enumerate(blocks):
        b['end_col'] = blocks[i+1]['start_col'] - 1 if i+1 < len(blocks) else ws.max_column
    return blocks

print("Loading workbook...")
wb = openpyxl.load_workbook(FILE_PATH, data_only=True)
print("Workbook loaded successfully.")

# We will collect quarterly metrics in a dictionary keyed by period_id
quarters = [
    'FY2023-24_Q1', 'FY2023-24_Q2', 'FY2023-24_Q3', 'FY2023-24_Q4',
    'FY2024-25_Q1', 'FY2024-25_Q2', 'FY2024-25_Q3', 'FY2024-25_Q4',
    'FY2025-26_Q1', 'FY2025-26_Q2', 'FY2025-26_Q3', 'FY2025-26_Q4'
]

metrics = {q: {} for q in quarters}
geographical_records = []
persistency_records = []
channel_records = []

# ==========================================
# 1. PARSE L-4 (Statutory Premium Schedule)
# ==========================================
print("\nParsing L-4...")
ws_l4 = wb['L-4']
l4_blocks = scan_quarter_blocks(ws_l4)
for b in l4_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    
    # In block [start_col..end_col], find particulars_col and current_quarter_col
    sc, ec = b['start_col'], b['end_col']
    part_col = None
    quarter_col = None
    for c in range(sc, ec + 1):
        for r in range(8, 14):
            txt = str(ws_l4.cell(r, c).value or '').lower()
            if 'particular' in txt:
                part_col = c
            if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                quarter_col = c
    if not part_col: part_col = sc + 1
    if not quarter_col: quarter_col = part_col + 1
    
    # Extract line items
    for r in range(10, ws_l4.max_row + 1):
        line = str(ws_l4.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l4.cell(r, quarter_col).value)
        if 'first year' in line:
            metrics[pid]['l4_first_year_premium'] = val
        elif 'renewal' in line:
            metrics[pid]['l4_renewal_premium'] = val
        elif 'single' in line:
            metrics[pid]['l4_single_premium'] = val
        elif 'total premium' in line:
            metrics[pid]['l4_total_premium'] = val

# ==========================================
# 2. PARSE L-36 (Business Details, Slabs, SA, Policies, Lives)
# ==========================================
print("Parsing L-36...")
ws_l36 = wb['L-36']
l36_blocks = scan_quarter_blocks(ws_l36)
for b in l36_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    
    # Find current quarter measure columns
    # Look for header "For the Quarter ended"
    q_start = None
    for c in range(sc, ec + 1):
        for r in range(8, 11):
            txt = str(ws_l36.cell(r, c).value or '').lower()
            if 'for the quarter ended' in txt or 'for the quarter' in txt:
                if 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                    q_start = c
                    break
        if q_start: break
    if not q_start: q_start = sc + 3
    
    # Search for measure columns up until the next section header
    p_col, pol_col, lives_col, sa_col = None, None, None, None
    for c in range(q_start, min(q_start + 6, ec + 1)):
        for r in range(9, 13):
            txt = str(ws_l36.cell(r, c).value or '').lower()
            if 'premium' in txt and p_col is None: p_col = c
            elif 'policies' in txt and pol_col is None: pol_col = c
            elif 'lives' in txt and lives_col is None: lives_col = c
            elif ('sum insured' in txt or 'sum assured' in txt or 'applicable' in txt) and sa_col is None: sa_col = c
            
    # Fallback default offset if missing
    if p_col is None: p_col = q_start
    if pol_col is None: pol_col = q_start + 1
    if lives_col is None: lives_col = q_start + 2
    if sa_col is None: sa_col = q_start + 3

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
    for r in range(11, ws_l36.max_row + 1):
        c2 = str(ws_l36.cell(r, 2).value or '').strip()
        c3 = str(ws_l36.cell(r, 3).value or '').strip()
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
                
        if 'from ' in line_desc or 'above ' in line_desc:
            p_val = clean_val(ws_l36.cell(r, p_col).value)
            pol_val = clean_val(ws_l36.cell(r, pol_col).value)
            lives_val = clean_val(ws_l36.cell(r, lives_col).value)
            sa_val = clean_val(ws_l36.cell(r, sa_col).value)
            
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

    # Also check if section header rows have roll-ups
    # (If slab lines were zero or NA, roll-up headers hold the reported total)
    for r in range(11, ws_l36.max_row + 1):
        c2 = str(ws_l36.cell(r, 2).value or '').strip()
        c3 = str(ws_l36.cell(r, 3).value or '').strip()
        line_desc = f"{c2} {c3}".strip().lower()
        
        p_val = clean_val(ws_l36.cell(r, p_col).value)
        pol_val = clean_val(ws_l36.cell(r, pol_col).value)
        lives_val = clean_val(ws_l36.cell(r, lives_col).value)
        sa_val = clean_val(ws_l36.cell(r, sa_col).value)
        
        if p_val > 0 or pol_val > 0:
            if 'group single premium (gsp)' in line_desc and group_single_prem == 0:
                group_single_prem = p_val
                if total_pol == 0: total_pol += pol_val
                if group_lives == 0: group_lives += lives_val
                if total_sa == 0: total_sa += sa_val
            elif 'group single premium- annuity' in line_desc and group_single_prem == 0:
                group_single_prem += p_val
            elif 'individual single premium- (isp)' in line_desc and ind_single_prem == 0:
                ind_single_prem = p_val
            elif 'individual non single premium' in line_desc and ind_non_single_prem == 0:
                ind_non_single_prem = p_val
            elif 'group non single premium' in line_desc and group_non_single_prem == 0:
                group_non_single_prem = p_val

    metrics[pid]['individual_single_premium'] = ind_single_prem
    metrics[pid]['individual_non_single_premium'] = ind_non_single_prem
    metrics[pid]['group_single_premium'] = group_single_prem
    metrics[pid]['group_non_single_premium'] = group_non_single_prem
    metrics[pid]['group_yearly_renewal_premium'] = group_renewal_prem
    metrics[pid]['total_individual_premium'] = ind_single_prem + ind_non_single_prem + ind_renewal_prem
    metrics[pid]['total_group_premium'] = group_single_prem + group_non_single_prem + group_renewal_prem
    metrics[pid]['total_sum_assured'] = total_sa
    metrics[pid]['total_policies'] = int(total_pol)
    metrics[pid]['group_lives_covered'] = int(group_lives)

# ==========================================
# 3. PARSE L-1 (Revenue Account)
# ==========================================
print("Parsing L-1...")
ws_l1 = wb['L-1']
l1_blocks = scan_quarter_blocks(ws_l1)
for b in l1_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    
    # Grand Total column is the last column or labeled GRAND TOTAL
    gt_col = ec
    for c in range(sc, ec + 1):
        for r in range(10, 14):
            txt = str(ws_l1.cell(r, c).value or '').lower()
            if 'grand total' in txt:
                gt_col = c
                break
                
    for r in range(12, ws_l1.max_row + 1):
        line = str(ws_l1.cell(r, sc).value or '').strip().lower()
        val = clean_val(ws_l1.cell(r, gt_col).value)
        if 'commission' in line and 'gross' not in line:
            metrics[pid]['comm_expense'] = val
        elif 'operating expenses' in line:
            metrics[pid]['opex_expense'] = val
        elif 'surrenders' in line:
            metrics[pid]['surrenders'] = val
        elif 'surplus' in line or 'deficit' in line or 'transferred to shareholders' in line:
            if 'business_profit' not in metrics[pid]:
                metrics[pid]['business_profit'] = val

# ==========================================
# 4. PARSE L-2 (Profit & Loss Account)
# ==========================================
print("Parsing L-2...")
ws_l2 = wb['L-2']
l2_blocks = scan_quarter_blocks(ws_l2)
for b in l2_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    
    # Col 1 is Particulars, Col 3 is current quarter
    part_col = sc
    q_col = sc + 2
    for c in range(sc, ec + 1):
        for r in range(11, 14):
            txt = str(ws_l2.cell(r, c).value or '').lower()
            if 'particular' in txt: part_col = c
            if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                q_col = c
                
    for r in range(13, ws_l2.max_row + 1):
        line = str(ws_l2.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l2.cell(r, q_col).value)
        if 'profit before tax' in line:
            metrics[pid]['profit_before_tax'] = val
        elif 'profit after tax' in line or 'profit / (loss) after tax' in line or 'loss after tax' in line:
            metrics[pid]['profit_after_tax'] = val
        elif 'balance' in line and ('brought forward' in line or 'carried forward' in line or 'carried to balance' in line):
            metrics[pid]['profit_loss_carried_forward'] = val

# ==========================================
# 5. PARSE L-7 (Benefits Paid / Claims)
# ==========================================
print("Parsing L-7...")
ws_l7 = wb['L-7']
l7_blocks = scan_quarter_blocks(ws_l7)
for b in l7_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    q_col = sc + 2
    for c in range(sc, ec + 1):
        for r in range(9, 13):
            txt = str(ws_l7.cell(r, c).value or '').lower()
            if 'particular' in txt: part_col = c
            if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                q_col = c
                
    for r in range(10, ws_l7.max_row + 1):
        line = str(ws_l7.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l7.cell(r, q_col).value)
        if 'claims by death' in line or 'death claims' in line:
            metrics[pid]['death_claims_amount'] = val
        elif 'by maturity' in line or 'maturity' in line:
            metrics[pid]['maturity_amount'] = val
        elif 'total' in line and ('benefits' in line or 'claims' in line):
            metrics[pid]['total_claim_amount_reported'] = val

# ==========================================
# 6. PARSE L-8 & L-9 (Capital, Reserves, Share Premium)
# ==========================================
print("Parsing L-8 & L-9...")
ws_l8 = wb['L-8']
l8_blocks = scan_quarter_blocks(ws_l8)
for b in l8_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    q_col = sc + 2
    for r in range(10, ws_l8.max_row + 1):
        line = str(ws_l8.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l8.cell(r, q_col).value)
        if 'total' in line:
            metrics[pid]['share_capital'] = val
            break

ws_l9 = wb['L-9']
l9_blocks = scan_quarter_blocks(ws_l9)
for b in l9_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    q_col = sc + 2
    reserves_total = 0.0
    for r in range(10, ws_l9.max_row + 1):
        line = str(ws_l9.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l9.cell(r, q_col).value)
        if 'share premium' in line:
            metrics[pid]['share_premium'] = val
        elif 'profit' in line and 'loss' in line:
            metrics[pid]['profit_loss_carried_forward'] = val
        elif 'total' in line:
            reserves_total = val
    metrics[pid]['reserves_and_surplus'] = reserves_total

# ==========================================
# 7. PARSE L-22 (Analytical Ratios: Persistency, Conservation, ROE)
# ==========================================
print("Parsing L-22...")
ws_l22 = wb['L-22']
l22_blocks = scan_quarter_blocks(ws_l22)
for b in l22_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    q_col = sc + 2
    for c in range(sc, ec + 1):
        for r in range(8, 12):
            txt = str(ws_l22.cell(r, c).value or '').lower()
            if 'particular' in txt: part_col = c
            if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                q_col = c
                
    current_persistency_type = None
    for r in range(10, ws_l22.max_row + 1):
        line = str(ws_l22.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l22.cell(r, q_col).value)
        
        if 'conservation ratio' in line:
            metrics[pid]['conservation_ratio'] = val
        elif 'return on equity' in line or 'roe' in line:
            metrics[pid]['roe_pct'] = val
        elif 'solvency ratio' in line and 'solvency_ratio' not in metrics[pid]:
            metrics[pid]['solvency_ratio'] = val
            
        # Persistency detection
        if 'persistency ratio - premium basis ( regular' in line:
            current_persistency_type = 'regular_prem'
        elif 'persistency ratio - premium basis ( single' in line:
            current_persistency_type = 'single_prem'
        elif 'persistency ratio - number of policy basis ( regular' in line:
            current_persistency_type = 'regular_count'
        elif 'persistency ratio - number of policy basis ( single' in line:
            current_persistency_type = 'single_count'
        elif '13th month' in line:
            if current_persistency_type == 'regular_prem':
                metrics[pid]['persistency_13m_prem'] = val
            elif current_persistency_type == 'regular_count':
                metrics[pid]['persistency_13m_count'] = val
        elif '25th month' in line:
            if current_persistency_type == 'regular_prem':
                metrics[pid]['persistency_25m_prem'] = val
            elif current_persistency_type == 'regular_count':
                metrics[pid]['persistency_25m_count'] = val
        elif '37th month' in line:
            if current_persistency_type == 'regular_prem':
                metrics[pid]['persistency_37m_prem'] = val
            elif current_persistency_type == 'regular_count':
                metrics[pid]['persistency_37m_count'] = val
        elif '49th month' in line:
            if current_persistency_type == 'regular_prem':
                metrics[pid]['persistency_49m_prem'] = val
            elif current_persistency_type == 'regular_count':
                metrics[pid]['persistency_49m_count'] = val
        elif '61st month' in line:
            if current_persistency_type == 'regular_prem':
                metrics[pid]['persistency_61m_prem'] = val
            elif current_persistency_type == 'regular_count':
                metrics[pid]['persistency_61m_count'] = val

# ==========================================
# 8. PARSE L-32 (Solvency Margin & Solvency Ratio)
# ==========================================
print("Parsing L-32...")
ws_l32 = wb['L-32']
l32_blocks = scan_quarter_blocks(ws_l32)
for b in l32_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    val_col = sc + 3 # Col 4 in block
    for r in range(10, ws_l32.max_row + 1):
        line = str(ws_l32.cell(r, part_col).value or '').strip().lower()
        val = clean_val(ws_l32.cell(r, val_col).value)
        if 'solvency ratio' in line:
            metrics[pid]['solvency_ratio'] = val

# ==========================================
# 9. PARSE L-38 (Intermediaries & Channel Productivity)
# ==========================================
print("Parsing L-38...")
ws_l38 = wb['L-38']
l38_blocks = scan_quarter_blocks(ws_l38)
for b in l38_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    pol_col = sc + 2
    prem_col = sc + 3
    
    banca_prem, banca_pol = 0.0, 0
    agent_prem, agent_pol = 0.0, 0
    broker_prem, broker_pol = 0.0, 0
    direct_prem, direct_pol = 0.0, 0
    web_prem, web_pol = 0.0, 0
    
    for r in range(10, ws_l38.max_row + 1):
        line = str(ws_l38.cell(r, part_col).value or '').strip().lower()
        pol_val = clean_int(ws_l38.cell(r, pol_col).value)
        prem_val = clean_val(ws_l38.cell(r, prem_col).value)
        
        if 'individual agents' in line:
            agent_prem = prem_val; agent_pol = pol_val
        elif 'corporate agents-banks' in line:
            banca_prem = prem_val; banca_pol = pol_val
        elif 'brokers' in line:
            broker_prem = prem_val; broker_pol = pol_val
        elif 'direct business' in line:
            direct_prem = prem_val; direct_pol = pol_val
        elif 'web aggregators' in line:
            web_prem = prem_val; web_pol = pol_val
            
    metrics[pid]['channel_banca_prem'] = banca_prem
    metrics[pid]['channel_agency_prem'] = agent_prem
    metrics[pid]['channel_broker_prem'] = broker_prem
    metrics[pid]['channel_direct_prem'] = direct_prem
    metrics[pid]['channel_web_aggregator_prem'] = web_prem

# ==========================================
# 10. PARSE L-41 (Complaints / Grievances)
# ==========================================
print("Parsing L-41...")
ws_l41 = wb['L-41']
l41_blocks = scan_quarter_blocks(ws_l41)
for b in l41_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    reg_col = sc + 3 # Additions during quarter
    for r in range(10, ws_l41.max_row + 1):
        line = str(ws_l41.cell(r, part_col).value or '').strip().lower()
        val = clean_int(ws_l41.cell(r, reg_col).value)
        if 'total number of complaints' in line:
            metrics[pid]['total_complaints'] = val
            break

# ==========================================
# 11. PARSE L-45 (Offices & Branches)
# ==========================================
print("Parsing L-45...")
ws_l45 = wb['L-45']
l45_blocks = scan_quarter_blocks(ws_l45)
for b in l45_blocks:
    pid = b['period_id']
    if pid not in metrics: continue
    sc, ec = b['start_col'], b['end_col']
    part_col = sc + 1
    num_col = sc + 3
    for r in range(9, ws_l45.max_row + 1):
        line = str(ws_l45.cell(r, part_col).value or '').strip().lower()
        val = clean_int(ws_l45.cell(r, num_col).value)
        if 'no of branches at the end of' in line or 'no. of offices at the end' in line:
            metrics[pid]['number_offices_branches'] = val
        elif 'no. of insurance agents' in line:
            metrics[pid]['number_individual_agents'] = val

# ==========================================
# 12. DERIVED METRICS & CONSOLIDATION
# ==========================================
print("\nCalculating Derived Metrics...")
for i, pid in enumerate(quarters):
    m = metrics[pid]
    
    # Financial year premium (First Year Premium)
    fy_p = m.get('l4_first_year_premium', 0.0)
    single_p = m.get('l4_single_premium', 0.0)
    renewal_p = m.get('l4_renewal_premium', 0.0)
    
    # If L-4 was 0 or incomplete, fallback to L-36
    if fy_p == 0.0 and (m.get('individual_non_single_premium', 0.0) > 0 or m.get('group_single_premium', 0.0) > 0):
        fy_p = m.get('individual_non_single_premium', 0.0) + m.get('group_non_single_premium', 0.0)
    if single_p == 0.0 and (m.get('individual_single_premium', 0.0) > 0 or m.get('group_single_premium', 0.0) > 0):
        single_p = m.get('individual_single_premium', 0.0) + m.get('group_single_premium', 0.0)
    if renewal_p == 0.0 and m.get('group_yearly_renewal_premium', 0.0) > 0:
        renewal_p = m.get('group_yearly_renewal_premium', 0.0)
        
    m['financial_year_premium'] = fy_p
    m['total_single_premium'] = single_p
    m['renewal_premium'] = renewal_p
    
    # Gross written premium (derived: FY + Single + Renewal)
    gwp = m.get('l4_total_premium', 0.0)
    if gwp == 0.0:
        gwp = fy_p + single_p + renewal_p
    m['gross_written_premium'] = gwp
    m['total_premium'] = gwp
    m['total_non_single_premium'] = fy_p + renewal_p
    
    # Total claim amount = Death claims + Maturity amount
    death_c = m.get('death_claims_amount', 0.0)
    maturity_c = m.get('maturity_amount', 0.0)
    m['total_claim_amount'] = death_c + maturity_c
    
    # Total expense = Commission + Opex
    comm = m.get('comm_expense', 0.0)
    opex = m.get('opex_expense', 0.0)
    m['total_expense'] = comm + opex
    
    # Net Worth = Share Capital + Reserves & Surplus
    scap = m.get('share_capital', 0.0)
    res = m.get('reserves_and_surplus', 0.0)
    m['net_worth'] = scap + res
    
    # NOP
    m['total_nop'] = m.get('total_policies', 0)
    
    # ATS (Average Ticket Size = Premium in lakhs * 100,000 / Policies)
    pol = m.get('total_policies', 0)
    if pol > 0 and gwp > 0:
        m['avg_ticket_size_inr'] = round((gwp * 100000.0) / pol, 2)
    else:
        m['avg_ticket_size_inr'] = 0.0
        
    # Growth metrics vs Prior Year Corresponding Quarter (i - 4)
    if i >= 4:
        prior_pid = quarters[i - 4]
        prior_m = metrics[prior_pid]
        
        prior_gwp = prior_m.get('gross_written_premium', 0.0)
        if prior_gwp > 0:
            m['avg_premium_growth_pct'] = round(((gwp - prior_gwp) / prior_gwp) * 100.0, 2)
        else:
            m['avg_premium_growth_pct'] = None
            
        prior_pol = prior_m.get('total_policies', 0)
        if prior_pol > 0:
            m['policy_sales_growth_pct'] = round(((pol - prior_pol) / prior_pol) * 100.0, 2)
        else:
            m['policy_sales_growth_pct'] = None
            
        prior_sa = prior_m.get('total_sum_assured', 0.0)
        cur_sa = m.get('total_sum_assured', 0.0)
        if prior_sa > 0:
            m['avg_sum_assured_growth_pct'] = round(((cur_sa - prior_sa) / prior_sa) * 100.0, 2)
        else:
            m['avg_sum_assured_growth_pct'] = None
    else:
        m['avg_premium_growth_pct'] = None
        m['policy_sales_growth_pct'] = None
        m['avg_sum_assured_growth_pct'] = None

    # Static company attributes
    m['company_website_link'] = "https://www.acko.com"

# Display Summary Table for all 12 Quarters
print("\n" + "="*110)
print(f"{'Period':<14} | {'GWP (Lakhs)':<12} | {'FY Prem':<10} | {'Single':<10} | {'Renewal':<10} | {'Policies':<8} | {'Lives':<8} | {'Solvency':<8} | {'PAT':<10}")
print("="*110)
for pid in quarters:
    m = metrics[pid]
    print(f"{pid:<14} | {m.get('gross_written_premium', 0.0):<12.2f} | {m.get('financial_year_premium', 0.0):<10.2f} | {m.get('total_single_premium', 0.0):<10.2f} | {m.get('renewal_premium', 0.0):<10.2f} | {m.get('total_policies', 0):<8d} | {m.get('group_lives_covered', 0):<8d} | {m.get('solvency_ratio', 0.0):<8.2f} | {m.get('profit_after_tax', 0.0):<10.2f}")
print("="*110)

wb.close()
