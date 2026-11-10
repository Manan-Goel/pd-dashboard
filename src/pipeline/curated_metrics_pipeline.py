"""
Production Ingestion Pipeline for Curated Life Insurance Quarterly Metrics (64 Standardized Fields).
Extracts, scales, reconciles, and stores statutory and derived metrics across:
- fact_company_quarterly_metrics (Master wide table, 64 fields)
- fact_geographical_distribution (State/UT/NRI policies, premium, sum assured)
- fact_persistency_cohorts (13m - 61m persistency ratios)
- fact_intermediary_channel_metrics (Channels & productivity)
"""

import os
import re
import json
import sqlite3
import openpyxl
from typing import Dict, Any, List, Optional, Tuple

COMPANY_METADATA = {
    'ACKO_LIFE': {
        'name': 'Acko Life Insurance Limited',
        'reg_no': '164',
        'website': 'https://www.acko.com',
        'top_products': 'Group Term Life, Credit Life, Group Single'
    }
}

VALID_FY_PREFIXES = ('FY2021-22', 'FY2022-23', 'FY2023-24', 'FY2024-25', 'FY2025-26')

def clean_val(v) -> float:
    if v is None:
        return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', '-', 'NA', 'Nil', 'NIL', '.', 'None'):
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def clean_int(v) -> int:
    return int(round(clean_val(v)))

def clean_str(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in ('-', 'NA', 'Nil', 'NIL', 'None') else s

def scan_quarter_blocks(ws) -> List[Dict[str, Any]]:
    """Detects all quarter blocks across row 1 & 2, respecting valid FY range."""
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
            if any(current_fy.startswith(prefix) for prefix in VALID_FY_PREFIXES):
                period_id = f"{current_fy}_{q_match}"
                blocks.append({
                    'fy': current_fy,
                    'quarter': q_match,
                    'period_id': period_id,
                    'start_col': c
                })
                
    for i, b in enumerate(blocks):
        b['end_col'] = blocks[i+1]['start_col'] - 1 if i+1 < len(blocks) else ws.max_column
    return blocks

class CuratedMetricsPipeline:
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def ingest_company_workbook(self, file_path: str, company_id: str) -> Dict[str, Any]:
        """
        Executes end-to-end extraction and ingestion of 64 standardized metrics
        for the given company workbook.
        """
        print(f"\n[Curated Pipeline] Loading workbook: {file_path}")
        wb = openpyxl.load_workbook(file_path, data_only=True)
        
        # 1. Discover all unique available periods across statutory sheets
        available_periods = set()
        for sched in ['L-1', 'L-2', 'L-3', 'L-4', 'L-36']:
            if sched in wb.sheetnames:
                blocks = scan_quarter_blocks(wb[sched])
                for b in blocks:
                    available_periods.add(b['period_id'])
                    
        ordered_periods = sorted(list(available_periods))
        print(f"[Curated Pipeline] Discovered {len(ordered_periods)} active periods for {company_id}: {ordered_periods}")
        
        metrics = {pid: {'company_id': company_id, 'period_id': pid, 'financial_year': pid.split('_')[0], 'quarter': pid.split('_')[1]} for pid in ordered_periods}
        geo_records = []
        persistency_records = []
        channel_records = []

        # ----------------------------------------------------
        # SCHEDULE L-4: Statutory Premium Ingestion
        # ----------------------------------------------------
        if 'L-4' in wb.sheetnames:
            ws_l4 = wb['L-4']
            for b in scan_quarter_blocks(ws_l4):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, quarter_col = None, None
                for c in range(sc, ec + 1):
                    for r in range(8, 14):
                        txt = str(ws_l4.cell(r, c).value or '').lower()
                        if 'particular' in txt and not part_col: part_col = c
                        if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                            if not quarter_col: quarter_col = c
                if not part_col: part_col = sc + 1
                if not quarter_col: quarter_col = part_col + 1
                
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

        # ----------------------------------------------------
        # SCHEDULE L-36: Universal Dynamic Ingestion (Slabs, SA, Policies, Lives)
        # ----------------------------------------------------
        if 'L-36' in wb.sheetnames:
            ws_l36 = wb['L-36']
            for b in scan_quarter_blocks(ws_l36):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                
                # 1. Find the current quarter header column and next section
                q_start = None
                q_next = ec + 1
                for c in range(sc, ec + 1):
                    for r in range(8, 11):
                        txt = str(ws_l36.cell(r, c).value or '').lower()
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
                
                # 2. Particulars columns in [sc .. q_start - 1]
                part_cols = []
                for c in range(sc, q_start):
                    has_text = any(len(str(ws_l36.cell(r, c).value or '').strip()) > 3 for r in range(11, 20))
                    if has_text:
                        part_cols.append(c)
                if not part_cols:
                    part_cols = [sc + 1, sc + 2] if sc + 2 < q_start else [sc + 1]
                    
                # 3. Numeric columns in [q_start .. current_q_end]
                num_cols = []
                for c in range(q_start, current_q_end + 1):
                    for r in range(12, ws_l36.max_row + 1):
                        val = ws_l36.cell(r, c).value
                        if val is not None and (isinstance(val, (int, float)) or (isinstance(val, str) and val.strip().replace(',', '').isdigit())):
                            num_cols.append(c)
                            break
                            
                while len(num_cols) < 4:
                    next_c = (num_cols[-1] + 1) if num_cols else q_start
                    num_cols.append(next_c)
                    
                p_col, pol_col, lives_col, sa_col = num_cols[0], num_cols[1], num_cols[2], num_cols[3]

                ind_single_prem = 0.0
                group_single_prem = 0.0
                ind_non_single_prem = 0.0
                group_non_single_prem = 0.0
                ind_renewal_prem = 0.0
                group_renewal_prem = 0.0
                total_sa = 0.0
                total_pol = 0
                group_lives = 0
                
                current_sec = None
                for r in range(11, ws_l36.max_row + 1):
                    part_text = " ".join(str(ws_l36.cell(r, pc).value or '').strip() for pc in part_cols).lower()
                    
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
                        
                    p_val = clean_val(ws_l36.cell(r, p_col).value)
                    pol_val = clean_val(ws_l36.cell(r, pol_col).value)
                    lives_val = clean_val(ws_l36.cell(r, lives_col).value)
                    sa_val = clean_val(ws_l36.cell(r, sa_col).value)
                    
                    if p_val > 100000.0: p_val /= 100000.0
                    if sa_val > 1000000.0: sa_val /= 100000.0
                    
                    if 'from ' in part_text or 'above ' in part_text:
                        total_sa += sa_val
                        total_pol += int(pol_val)
                        
                        if current_sec == 'ind_single': ind_single_prem += p_val
                        elif current_sec == 'group_single':
                            group_single_prem += p_val
                            group_lives += int(lives_val)
                        elif current_sec == 'ind_non_single': ind_non_single_prem += p_val
                        elif current_sec == 'group_non_single':
                            group_non_single_prem += p_val
                            group_lives += int(lives_val)
                        elif current_sec == 'renewal_ind': ind_renewal_prem += p_val
                        elif current_sec == 'renewal_group':
                            group_renewal_prem += p_val
                            group_lives += int(lives_val)

                metrics[pid]['individual_single_premium'] = round(ind_single_prem, 4)
                metrics[pid]['individual_non_single_premium'] = round(ind_non_single_prem, 4)
                metrics[pid]['group_single_premium'] = round(group_single_prem, 4)
                metrics[pid]['group_non_single_premium'] = round(group_non_single_prem, 4)
                metrics[pid]['group_yearly_renewal_premium'] = round(group_renewal_prem, 4)
                metrics[pid]['total_individual_premium'] = round(ind_single_prem + ind_non_single_prem + ind_renewal_prem, 4)
                metrics[pid]['total_group_premium'] = round(group_single_prem + group_non_single_prem + group_renewal_prem, 4)
                metrics[pid]['total_sum_assured'] = round(total_sa, 4)
                metrics[pid]['total_policies'] = int(total_pol)
                metrics[pid]['group_lives_covered'] = int(group_lives)

        # ----------------------------------------------------
        # SCHEDULE L-1: Revenue Account (Operating Profit, Commission, Opex, Surrenders)
        # ----------------------------------------------------
        if 'L-1' in wb.sheetnames:
            ws_l1 = wb['L-1']
            for b in scan_quarter_blocks(ws_l1):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
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

        # ----------------------------------------------------
        # SCHEDULE L-2: Profit & Loss Account (PBT, PAT, Carried Forward)
        # ----------------------------------------------------
        if 'L-2' in wb.sheetnames:
            ws_l2 = wb['L-2']
            for b in scan_quarter_blocks(ws_l2):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, q_col = None, None
                for c in range(sc, ec + 1):
                    for r in range(11, 14):
                        txt = str(ws_l2.cell(r, c).value or '').lower()
                        if 'particular' in txt and not part_col: part_col = c
                        if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                            if not q_col: q_col = c
                if not part_col: part_col = sc
                if not q_col: q_col = sc + 2
                            
                for r in range(13, ws_l2.max_row + 1):
                    line = str(ws_l2.cell(r, part_col).value or '').strip().lower()
                    val = clean_val(ws_l2.cell(r, q_col).value)
                    if 'profit before tax' in line:
                        metrics[pid]['profit_before_tax'] = val
                    elif 'profit after tax' in line or 'profit / (loss) after tax' in line or 'loss after tax' in line:
                        metrics[pid]['profit_after_tax'] = val
                    elif 'balance' in line and ('brought forward' in line or 'carried forward' in line or 'carried to balance' in line):
                        metrics[pid]['profit_loss_carried_forward'] = val

        # ----------------------------------------------------
        # SCHEDULE L-7: Benefits Paid / Claims (Death, Maturity, Total)
        # ----------------------------------------------------
        if 'L-7' in wb.sheetnames:
            ws_l7 = wb['L-7']
            for b in scan_quarter_blocks(ws_l7):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, q_col = None, None
                for c in range(sc, ec + 1):
                    for r in range(9, 13):
                        txt = str(ws_l7.cell(r, c).value or '').lower()
                        if 'particular' in txt and not part_col: part_col = c
                        if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                            if not q_col: q_col = c
                if not part_col: part_col = sc + 1
                if not q_col: q_col = sc + 2

                for r in range(10, ws_l7.max_row + 1):
                    line = str(ws_l7.cell(r, part_col).value or '').strip().lower()
                    if 'ceded in reinsurance' in line or 'amount ceded' in line or '2. (' in line or '2.(' in line:
                        break
                    val = clean_val(ws_l7.cell(r, q_col).value)
                    if 'claims by death' in line or 'death claims' in line:
                        if metrics[pid].get('death_claims_amount') is None:
                            metrics[pid]['death_claims_amount'] = val
                    elif 'by maturity' in line or 'maturity' in line:
                        if metrics[pid].get('maturity_amount') is None:
                            metrics[pid]['maturity_amount'] = val
                    elif 'total' in line and ('benefits' in line or 'claims' in line):
                        metrics[pid]['total_claim_amount_reported'] = val

        # ----------------------------------------------------
        # SCHEDULE L-8 & L-9: Share Capital & Reserves (Net Worth)
        # ----------------------------------------------------
        if 'L-8' in wb.sheetnames:
            ws_l8 = wb['L-8']
            for b in scan_quarter_blocks(ws_l8):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, q_col = sc + 1, sc + 2
                for r in range(10, ws_l8.max_row + 1):
                    line = str(ws_l8.cell(r, part_col).value or '').strip().lower()
                    val = clean_val(ws_l8.cell(r, q_col).value)
                    if 'total' in line:
                        metrics[pid]['share_capital'] = val
                        break

        if 'L-9' in wb.sheetnames:
            ws_l9 = wb['L-9']
            for b in scan_quarter_blocks(ws_l9):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, q_col = sc + 1, sc + 2
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

        # ----------------------------------------------------
        # SCHEDULE L-22: Analytical Ratios (Persistency, Conservation, ROE)
        # ----------------------------------------------------
        if 'L-22' in wb.sheetnames:
            ws_l22 = wb['L-22']
            for b in scan_quarter_blocks(ws_l22):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, q_col = sc + 1, sc + 2
                for c in range(sc, ec + 1):
                    for r in range(8, 12):
                        txt = str(ws_l22.cell(r, c).value or '').lower()
                        if 'particular' in txt: part_col = c
                        if 'for the' in txt and 'quarter' in txt and 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt:
                            q_col = c
                            
                current_p_basis = None
                for r in range(10, ws_l22.max_row + 1):
                    line = str(ws_l22.cell(r, part_col).value or '').strip().lower()
                    val = clean_val(ws_l22.cell(r, q_col).value)
                    
                    if 'conservation ratio' in line:
                        metrics[pid]['conservation_ratio'] = val
                    elif 'return on equity' in line or 'roe' in line:
                        metrics[pid]['roe_pct'] = val
                    elif 'solvency ratio' in line and 'solvency_ratio' not in metrics[pid]:
                        metrics[pid]['solvency_ratio'] = val
                        
                    if 'persistency ratio - premium basis ( regular' in line: current_p_basis = ('REGULAR_PREMIUM', 'PREMIUM_PERCENT')
                    elif 'persistency ratio - premium basis ( single' in line: current_p_basis = ('SINGLE_PREMIUM', 'PREMIUM_PERCENT')
                    elif 'persistency ratio - number of policy basis ( regular' in line: current_p_basis = ('REGULAR_PREMIUM', 'COUNT_PERCENT')
                    elif 'persistency ratio - number of policy basis ( single' in line: current_p_basis = ('SINGLE_PREMIUM', 'COUNT_PERCENT')
                    
                    cohort_match = None
                    for m_tag in ['13th', '25th', '37th', '49th', '61st']:
                        if f"{m_tag} month" in line:
                            cohort_match = m_tag
                            break
                    if cohort_match and current_p_basis:
                        p_type, b_metric = current_p_basis
                        if p_type == 'REGULAR_PREMIUM' and b_metric == 'PREMIUM_PERCENT':
                            metrics[pid][f'persistency_{cohort_match}_prem'] = val
                        elif p_type == 'REGULAR_PREMIUM' and b_metric == 'COUNT_PERCENT':
                            metrics[pid][f'persistency_{cohort_match}_count'] = val
                            
                        persistency_records.append({
                            'company_id': company_id,
                            'period_id': pid,
                            'cohort_month': cohort_match,
                            'premium_basis_type': p_type,
                            'basis_metric': b_metric,
                            'persistency_ratio_pct': val
                        })

        # ----------------------------------------------------
        # SCHEDULE L-32: Available Solvency Margin & Ratio
        # ----------------------------------------------------
        if 'L-32' in wb.sheetnames:
            ws_l32 = wb['L-32']
            for b in scan_quarter_blocks(ws_l32):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, val_col = sc + 1, sc + 3
                for r in range(10, ws_l32.max_row + 1):
                    line = str(ws_l32.cell(r, part_col).value or '').strip().lower()
                    val = clean_val(ws_l32.cell(r, val_col).value)
                    if 'solvency ratio' in line:
                        metrics[pid]['solvency_ratio'] = val

        # ----------------------------------------------------
        # SCHEDULE L-38: Channels & Intermediaries
        # ----------------------------------------------------
        if 'L-38' in wb.sheetnames:
            ws_l38 = wb['L-38']
            for b in scan_quarter_blocks(ws_l38):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, pol_col, prem_col = sc + 1, sc + 2, sc + 3
                
                channel_map = {
                    'individual agents': 'channel_agency_prem',
                    'corporate agents-banks': 'channel_banca_prem',
                    'brokers': 'channel_broker_prem',
                    'direct business': 'channel_direct_prem',
                    'web aggregators': 'channel_web_aggregator_prem'
                }
                for r in range(10, ws_l38.max_row + 1):
                    line = str(ws_l38.cell(r, part_col).value or '').strip().lower()
                    pol_val = clean_int(ws_l38.cell(r, pol_col).value)
                    prem_val = clean_val(ws_l38.cell(r, prem_col).value)
                    
                    for c_key, c_col_name in channel_map.items():
                        if c_key in line:
                            metrics[pid][c_col_name] = prem_val
                            channel_records.append({
                                'company_id': company_id,
                                'period_id': pid,
                                'channel_name': c_key.title(),
                                'policies_count': pol_val,
                                'premium_lakhs': prem_val,
                                'intermediary_count': 0,
                                'productivity_inr': round((prem_val * 100000.0) / pol_val, 2) if pol_val > 0 else 0.0
                            })

        # ----------------------------------------------------
        # SCHEDULE L-41: Grievance Disposal / Total Complaints
        # ----------------------------------------------------
        if 'L-41' in wb.sheetnames:
            ws_l41 = wb['L-41']
            for b in scan_quarter_blocks(ws_l41):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, reg_col = sc + 1, sc + 3
                for r in range(10, ws_l41.max_row + 1):
                    line = str(ws_l41.cell(r, part_col).value or '').strip().lower()
                    val = clean_int(ws_l41.cell(r, reg_col).value)
                    if 'total number of complaints' in line:
                        metrics[pid]['total_complaints'] = val
                        break

        # ----------------------------------------------------
        # SCHEDULE L-45: Offices, Branches & Web Info
        # ----------------------------------------------------
        if 'L-45' in wb.sheetnames:
            ws_l45 = wb['L-45']
            for b in scan_quarter_blocks(ws_l45):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col, num_col = sc + 1, sc + 3
                for r in range(9, ws_l45.max_row + 1):
                    line = str(ws_l45.cell(r, part_col).value or '').strip().lower()
                    val = clean_int(ws_l45.cell(r, num_col).value)
                    if 'no of branches at the end of' in line or 'no. of offices at the end' in line:
                        metrics[pid]['number_offices_branches'] = val
                    elif 'no. of insurance agents' in line:
                        metrics[pid]['number_individual_agents'] = val

        # ----------------------------------------------------
        # SCHEDULE L-25 (i): Geographical Distribution
        # ----------------------------------------------------
        if 'L-25 (i)' in wb.sheetnames:
            ws_l25 = wb['L-25 (i)']
            for b in scan_quarter_blocks(ws_l25):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col = sc + 1
                r_pol_c, r_prem_c, r_sa_c = sc + 2, sc + 3, sc + 4
                u_pol_c, u_prem_c, u_sa_c = sc + 5, sc + 6, sc + 7
                
                current_reg_type = 'STATE'
                for r in range(13, min(ws_l25.max_row + 1, 60)):
                    reg_name = str(ws_l25.cell(r, part_col).value or '').strip()
                    if not reg_name or reg_name.lower().startswith('note'):
                        continue
                    if 'union territories' in reg_name.lower():
                        current_reg_type = 'UNION_TERRITORY'
                        continue
                    if 'states' in reg_name.lower():
                        current_reg_type = 'STATE'
                        continue
                    if 'in india' in reg_name.lower():
                        current_reg_type = 'TOTAL'
                    elif 'outside india' in reg_name.lower():
                        current_reg_type = 'NRI'
                        
                    rp = clean_int(ws_l25.cell(r, r_pol_c).value)
                    rprem = clean_val(ws_l25.cell(r, r_prem_c).value)
                    rsa = clean_val(ws_l25.cell(r, r_sa_c).value)
                    up = clean_int(ws_l25.cell(r, u_pol_c).value)
                    uprem = clean_val(ws_l25.cell(r, u_prem_c).value)
                    usa = clean_val(ws_l25.cell(r, u_sa_c).value)
                    
                    geo_records.append({
                        'company_id': company_id,
                        'period_id': pid,
                        'region_type': current_reg_type,
                        'region_name': reg_name,
                        'rural_policies': rp,
                        'rural_premium_lakhs': rprem,
                        'rural_sum_assured_lakhs': rsa,
                        'urban_policies': up,
                        'urban_premium_lakhs': uprem,
                        'urban_sum_assured_lakhs': usa,
                        'total_policies': rp + up,
                        'total_premium_lakhs': round(rprem + uprem, 4),
                        'total_sum_assured_lakhs': round(rsa + usa, 4)
                    })

        # ----------------------------------------------------
        # DERIVED CALCULATIONS & CROSS-METRIC CONSOLIDATION
        # ----------------------------------------------------
        meta = COMPANY_METADATA.get(company_id, {})
        for i, pid in enumerate(ordered_periods):
            m = metrics[pid]
            
            # Root premiums from L-4 and L-36
            fy_p = m.get('l4_first_year_premium', 0.0)
            single_p = m.get('l4_single_premium', 0.0)
            renewal_p = m.get('l4_renewal_premium', 0.0)
            
            # Cross-schedule reconciliation fallback
            if fy_p == 0.0 and (m.get('individual_non_single_premium', 0.0) > 0 or m.get('group_non_single_premium', 0.0) > 0):
                fy_p = m.get('individual_non_single_premium', 0.0) + m.get('group_non_single_premium', 0.0)
            if single_p == 0.0 and (m.get('individual_single_premium', 0.0) > 0 or m.get('group_single_premium', 0.0) > 0):
                single_p = m.get('individual_single_premium', 0.0) + m.get('group_single_premium', 0.0)
            if renewal_p == 0.0 and m.get('group_yearly_renewal_premium', 0.0) > 0:
                renewal_p = m.get('group_yearly_renewal_premium', 0.0)
                
            m['financial_year_premium'] = round(fy_p, 4)
            m['total_single_premium'] = round(single_p, 4)
            m['renewal_premium'] = round(renewal_p, 4)
            
            # Gross Written Premium
            gwp = m.get('l4_total_premium', 0.0)
            if gwp == 0.0:
                gwp = fy_p + single_p + renewal_p
            m['gross_written_premium'] = round(gwp, 4)
            m['total_premium'] = round(gwp, 4)
            m['total_non_single_premium'] = round(fy_p + renewal_p, 4)
            
            # Total Claim Amount
            death_c = m.get('death_claims_amount', 0.0)
            maturity_c = m.get('maturity_amount', 0.0)
            m['total_claim_amount'] = round(death_c + maturity_c if (death_c + maturity_c) > 0 else m.get('total_claim_amount_reported', 0.0), 4)
            
            # Total Expense
            comm = m.get('comm_expense', 0.0)
            opex = m.get('opex_expense', 0.0)
            m['total_expense'] = round(comm + opex, 4)
            
            # Net Worth
            scap = m.get('share_capital', 0.0)
            res = m.get('reserves_and_surplus', 0.0)
            m['net_worth'] = round(scap + res, 4)
            
            # NOP & ATS
            pol = m.get('total_policies', 0)
            m['total_nop'] = pol
            if pol > 0 and gwp > 0:
                m['avg_ticket_size_inr'] = round((gwp * 100000.0) / pol, 2)
            else:
                m['avg_ticket_size_inr'] = 0.0
                
            # Growth Rates (vs Prior Year Same Quarter: i - 4)
            if i >= 4:
                prior_pid = ordered_periods[i - 4]
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

            # Company metadata
            m['company_website_link'] = meta.get('website', '')
            m['company_top_products'] = meta.get('top_products', '')
            m['geographical_summary'] = f"Geo details recorded in fact_geographical_distribution for {pid}"
            m['financial_performance'] = json.dumps({
                'GWP_Lakhs': m.get('gross_written_premium', 0.0),
                'PAT_Lakhs': m.get('profit_after_tax', 0.0),
                'Solvency_Ratio': m.get('solvency_ratio', 0.0),
                'Net_Worth_Lakhs': m.get('net_worth', 0.0)
            })

        # ----------------------------------------------------
        # PERSIST TO SQLITE DATABASE
        # ----------------------------------------------------
        print(f"[Curated Pipeline] Persisting {len(metrics)} quarterly records to fact_company_quarterly_metrics...")
        cursor = self.conn.cursor()
        
        columns = [
            'company_id', 'period_id', 'financial_year', 'quarter',
            'financial_year_premium', 'total_single_premium', 'renewal_premium',
            'total_individual_premium', 'total_group_premium', 'total_non_single_premium',
            'group_non_single_premium', 'group_yearly_renewal_premium',
            'individual_single_premium', 'individual_non_single_premium', 'group_single_premium',
            'gross_written_premium', 'avg_premium_growth_pct', 'policy_sales_growth_pct',
            'number_of_claims', 'death_claims_amount', 'maturity_amount', 'total_claim_amount',
            'comm_expense', 'opex_expense', 'total_expense', 'cagr_pct',
            'total_premium', 'total_sum_assured', 'avg_sum_assured_growth_pct',
            'total_policies', 'avg_ticket_size_inr', 'group_lives_covered',
            'market_share_premium_pct', 'market_share_sum_assured_pct', 'market_share_policies_pct',
            'business_profit', 'profit_before_tax', 'profit_after_tax',
            'aum_cagr', 'linked_aum', 'non_linked_aum', 'solvency_ratio',
            'group_policy_growth_pct', 'individual_policy_growth_pct', 'surrenders',
            'conservation_ratio', 'total_complaints', 'total_nop',
            'persistency_13m_count', 'persistency_13m_prem', 'persistency_25m_count', 'persistency_25m_prem',
            'persistency_37m_count', 'persistency_37m_prem', 'persistency_49m_count', 'persistency_49m_prem',
            'persistency_61m_count', 'persistency_61m_prem',
            'channel_agency_prem', 'channel_banca_prem', 'channel_broker_prem',
            'channel_direct_prem', 'channel_web_aggregator_prem', 'channel_other_prem',
            'geographical_summary', 'major_banking_partners', 'company_top_products',
            'number_banca_partners', 'number_banca_branches', 'bank_productivity_inr',
            'number_offices_branches', 'number_web_aggregators', 'number_individual_agents',
            'agent_productivity_inr', 'number_brokers', 'broker_productivity_inr',
            'share_capital', 'share_premium', 'profit_loss_carried_forward', 'net_worth',
            'roe_pct', 'product_mix_pct', 'channel_product_mix', 'financial_performance',
            'embedded_value', 'vnb_growth', 'company_website_link'
        ]
        
        placeholders = ", ".join(["?" for _ in columns])
        col_names = ", ".join(columns)
        sql_insert_master = f"INSERT OR REPLACE INTO fact_company_quarterly_metrics ({col_names}) VALUES ({placeholders})"
        
        for pid in ordered_periods:
            m = metrics[pid]
            row_vals = [m.get(c) for c in columns]
            cursor.execute(sql_insert_master, row_vals)

        # Persist Geo Records
        if geo_records:
            print(f"[Curated Pipeline] Persisting {len(geo_records)} records to fact_geographical_distribution...")
            sql_geo = """
                INSERT OR REPLACE INTO fact_geographical_distribution (
                    company_id, period_id, region_type, region_name,
                    rural_policies, rural_premium_lakhs, rural_sum_assured_lakhs,
                    urban_policies, urban_premium_lakhs, urban_sum_assured_lakhs,
                    total_policies, total_premium_lakhs, total_sum_assured_lakhs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            for g in geo_records:
                cursor.execute(sql_geo, (
                    g['company_id'], g['period_id'], g['region_type'], g['region_name'],
                    g['rural_policies'], g['rural_premium_lakhs'], g['rural_sum_assured_lakhs'],
                    g['urban_policies'], g['urban_premium_lakhs'], g['urban_sum_assured_lakhs'],
                    g['total_policies'], g['total_premium_lakhs'], g['total_sum_assured_lakhs']
                ))

        # Persist Persistency Cohorts
        if persistency_records:
            print(f"[Curated Pipeline] Persisting {len(persistency_records)} records to fact_persistency_cohorts...")
            sql_p = """
                INSERT OR REPLACE INTO fact_persistency_cohorts (
                    company_id, period_id, cohort_month, premium_basis_type, basis_metric, persistency_ratio_pct
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            for p in persistency_records:
                cursor.execute(sql_p, (
                    p['company_id'], p['period_id'], p['cohort_month'],
                    p['premium_basis_type'], p['basis_metric'], p['persistency_ratio_pct']
                ))

        # Persist Channels
        if channel_records:
            print(f"[Curated Pipeline] Persisting {len(channel_records)} records to fact_intermediary_channel_metrics...")
            sql_c = """
                INSERT OR REPLACE INTO fact_intermediary_channel_metrics (
                    company_id, period_id, channel_name, policies_count, premium_lakhs, intermediary_count, productivity_inr
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            for ch in channel_records:
                cursor.execute(sql_c, (
                    ch['company_id'], ch['period_id'], ch['channel_name'],
                    ch['policies_count'], ch['premium_lakhs'], ch['intermediary_count'], ch['productivity_inr']
                ))

        self.conn.commit()
        wb.close()
        print(f"[Curated Pipeline] Ingestion completed successfully for {company_id} ({len(ordered_periods)} quarters)!\n")
        return metrics

if __name__ == '__main__':
    conn = sqlite3.connect("life_insurance.db")
    pipeline = CuratedMetricsPipeline(conn)
    pipeline.ingest_company_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", "ACKO_LIFE")
    conn.close()
