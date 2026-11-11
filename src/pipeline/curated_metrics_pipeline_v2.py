"""
Curated Life Insurance Pipeline V2 (High-Performance & Universal Multi-Company Ingestion).
Supports ACKO, HDFC, LIC, CANARA HSBC, ICICI PRUDENTIAL, and SBI LIFE.
Features rigorous cell-level empirical resolution, multi-tier unit normalization,
and statutory fallback handling (e.g. Form L-32 Solvency Margin for LIC).
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
        'category': 'Private',
        'website': 'https://www.acko.com',
        'top_products': 'Group Term Life, Credit Life, Group Single'
    },
    'HDFC_LIFE': {
        'name': 'HDFC Life Insurance Company Limited',
        'reg_no': '101',
        'category': 'Private',
        'website': 'https://www.hdfclife.com',
        'top_products': 'HDFC Life Sanchay Plus, Click 2 Protect, Sampoorn Samridhi Plus'
    },
    'LIC': {
        'name': 'Life Insurance Corporation of India',
        'reg_no': '512',
        'category': 'Public',
        'website': 'https://licindia.in',
        'top_products': 'Jeevan Umang, Jeevan Labh, Tech Term, SIIP, Jeevan Anand'
    },
    'CANARA_HSBC_LIFE': {
        'name': 'Canara HSBC Life Insurance Company Limited',
        'reg_no': '136',
        'category': 'Private',
        'website': 'https://www.canarahsbclife.com',
        'top_products': 'iSelect Smart, Guaranteed Income4Life, Invest 4G'
    },
    'ICICI_PRUDENTIAL_LIFE': {
        'name': 'ICICI Prudential Life Insurance Company Limited',
        'reg_no': '105',
        'category': 'Private',
        'website': 'https://www.iciciprulife.com',
        'top_products': 'iProtect Smart, Signature, Gift Pro, Pru Gold'
    },
    'SBI_LIFE': {
        'name': 'SBI Life Insurance Company Limited',
        'reg_no': '111',
        'category': 'Private',
        'website': 'https://www.sbilife.co.in',
        'top_products': 'eShield Next, Smart Platina Plus, Retiresmart, Smart Wealth Builder'
    },
    'ADITYA_BIRLA_SUN_LIFE': {
        'name': 'Aditya Birla Sun Life Insurance Company Limited',
        'reg_no': '109',
        'category': 'Private',
        'website': 'https://lifeinsurance.adityabirlacapital.com',
        'top_products': 'DigiShield Plan, Vision LifeIncome, Assured Income Plus'
    },
    'AGEAS_FEDERAL_LIFE': {
        'name': 'Ageas Federal Life Insurance Company Limited',
        'reg_no': '135',
        'category': 'Private',
        'website': 'https://www.ageasfederal.com',
        'top_products': 'Life Guaranteed Income Plan, Smart Wealth Plan'
    },
    'AVIVA_LIFE': {
        'name': 'Aviva Life Insurance Company India Limited',
        'reg_no': '122',
        'category': 'Private',
        'website': 'https://www.avivaindia.com',
        'top_products': 'Signature Guaranteed Income, Extra Cover, Affluence'
    },
    'BANDHAN_LIFE': {
        'name': 'Bandhan Life Insurance Limited',
        'reg_no': '138',
        'category': 'Private',
        'website': 'https://www.bandhanlife.com',
        'top_products': 'iTerm Prime, Guaranteed Income, POS iSuraksha'
    },
    'BHARTI_AXA_LIFE': {
        'name': 'Bharti AXA Life Insurance Company Limited',
        'reg_no': '130',
        'category': 'Private',
        'website': 'https://www.bhartiaxa.com',
        'top_products': 'Flexi Term Pro, Guaranteed Income Pro, Elite Protect'
    }
}

VALID_FY_PREFIXES = ('FY2021-22', 'FY2022-23', 'FY2023-24', 'FY2024-25', 'FY2025-26')

def clean_val(v) -> float:
    if v is None:
        return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', '-', 'NA', 'Nil', 'NIL', '.', 'None', '#', '*'):
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def clean_int(v) -> int:
    return int(round(clean_val(v)))

def scan_quarter_blocks_rows(rows: List[Tuple]) -> List[Dict[str, Any]]:
    """Detects all quarter blocks across row 0 & 1, respecting valid FY range."""
    if not rows or len(rows) < 2:
        return []
    row1, row2 = rows[0], rows[1]
    max_c = max(len(r) for r in rows[:10])
    
    blocks = []
    current_fy = None
    for c in range(max_c):
        v1 = row1[c] if c < len(row1) else None
        v2 = row2[c] if c < len(row2) else None
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
        b['end_col'] = blocks[i+1]['start_col'] - 1 if i+1 < len(blocks) else max_c - 1
    return blocks

def detect_unit_multiplier(rows: List[Tuple], sc: int, ec: int) -> float:
    """Detects monetary unit multiplier (to convert to INR Lakhs) within a quarter block."""
    headers = []
    for r in range(min(16, len(rows))):
        for c in range(sc, min(ec + 1, len(rows[r]))):
            v = rows[r][c]
            if v is not None:
                headers.append(str(v))
    txt = " ".join(headers).lower()
    
    if "'000" in txt or "thousand" in txt or "` 000" in txt:
        return 0.01
    elif "crore" in txt or "crs" in txt:
        return 100.0
    elif "lakh" in txt or "lac" in txt:
        return 1.0
    return 1.0

class CuratedMetricsPipelineV2:
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def ingest_company_workbook(self, file_path: str, company_id: str) -> Dict[str, Any]:
        print(f"\n=======================================================")
        print(f"🚀 INGESTING: {company_id} ({os.path.basename(file_path)})")
        print(f"=======================================================")
        
        # 1. Fast read_only load of relevant sheets into memory
        schedules = ['L-1', 'L-2', 'L-4', 'L-7', 'L-8', 'L-9', 'L-22', 'L-25 (i)', 'L-32', 'L-36', 'L-38', 'L-41', 'L-45']
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_data: Dict[str, List[Tuple]] = {}
        for s in schedules:
            if s in wb.sheetnames:
                sheet_data[s] = list(wb[s].iter_rows(values_only=True))
        wb.close()
        print(f"Loaded {len(sheet_data)} statutory schedules into memory.")

        # 2. Discover all unique available periods
        available_periods = set()
        for s in ['L-4', 'L-1', 'L-2', 'L-36']:
            if s in sheet_data:
                for b in scan_quarter_blocks_rows(sheet_data[s]):
                    available_periods.add(b['period_id'])

        ordered_periods = sorted(list(available_periods))
        print(f"Discovered {len(ordered_periods)} active quarters for {company_id}: {ordered_periods[0] if ordered_periods else 'None'} -> {ordered_periods[-1] if ordered_periods else 'None'}")

        metrics: Dict[str, Dict[str, Any]] = {
            pid: {
                'company_id': company_id,
                'period_id': pid,
                'financial_year': pid.split('_')[0],
                'quarter': pid.split('_')[1]
            } for pid in ordered_periods
        }
        geo_records = []
        persistency_records = []
        channel_records = []

        # ----------------------------------------------------
        # SCHEDULE L-4: Statutory Premium Ingestion
        # ----------------------------------------------------
        if 'L-4' in sheet_data:
            rows = sheet_data['L-4']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)

                part_col = None
                for c in range(sc, ec + 1):
                    for r in range(6, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'particular' in txt and part_col is None:
                            part_col = c
                            break
                    if part_col is not None: break
                if part_col is None: part_col = sc

                total_col = None
                # Check for segment total column (ICICI/SBI)
                for c in range(sc, ec + 1):
                    if c == part_col: continue
                    for r in range(7, min(13, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if txt in ('total', 'grand total'):
                            total_col = c
                            break
                    if total_col is not None: break

                # Check for 'for the quarter' / 'up to the quarter'
                if total_col is None:
                    for c in range(sc, ec + 1):
                        if c == part_col: continue
                        for r in range(6, min(14, len(rows))):
                            txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                            if ('for the quarter' in txt or 'up to the quarter' in txt or 'quarter ended' in txt) and 'previous' not in txt and 'corresponding' not in txt:
                                total_col = c
                                break
                        if total_col is not None: break

                if total_col is None: total_col = part_col + 1

                # Raw magnitude check: if total > 5,000,000 and mult == 1.0, scale was '000
                test_val = 0.0
                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').lower() if part_col < len(rows[r]) else ''
                    if 'total' in line:
                        test_val = clean_val(rows[r][total_col] if total_col < len(rows[r]) else None)
                        break
                if test_val > 5000000.0 and mult == 1.0:
                    mult = 0.01

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    raw_val = clean_val(rows[r][total_col] if total_col < len(rows[r]) else None)
                    val = round(raw_val * mult, 4)
                    if 'first year' in line:
                        metrics[pid]['l4_first_year_premium'] = val
                    elif 'renewal' in line:
                        metrics[pid]['l4_renewal_premium'] = val
                    elif 'single' in line:
                        metrics[pid]['l4_single_premium'] = val
                    elif 'total premium' in line or (line == 'total' and 'l4_total_premium' not in metrics[pid]):
                        metrics[pid]['l4_total_premium'] = val

        # ----------------------------------------------------
        # SCHEDULE L-36: Universal Dynamic Ingestion (Slabs, SA, Policies, Lives)
        # ----------------------------------------------------
        if 'L-36' in sheet_data:
            rows = sheet_data['L-36']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']

                q_start = None
                q_next = ec + 1
                for c in range(sc, ec + 1):
                    for r in range(6, min(12, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'for the quarter' in txt or 'current quarter' in txt or 'quarter ended' in txt:
                            if 'previous' not in txt and 'corresponding' not in txt and 'up to' not in txt and 'same quarter' not in txt:
                                if q_start is None: q_start = c
                            elif q_start is not None and c > q_start:
                                q_next = min(q_next, c)
                                break
                        elif 'up to the' in txt and q_start is not None and c > q_start:
                            q_next = min(q_next, c)
                            break
                        elif 'same quarter' in txt and q_start is not None and c > q_start:
                            q_next = min(q_next, c)
                            break

                if not q_start: q_start = sc + 2
                current_q_end = q_next - 1

                part_cols = []
                for c in range(sc, q_start):
                    has_text = any(len(str(rows[r][c] or '').strip()) > 3 for r in range(10, min(22, len(rows))) if c < len(rows[r]))
                    if has_text: part_cols.append(c)
                if not part_cols:
                    part_cols = [sc + 1, sc + 2] if sc + 2 < q_start else [sc + 1]

                num_cols = []
                for c in range(q_start, current_q_end + 1):
                    for r in range(10, min(30, len(rows))):
                        if c < len(rows[r]):
                            val = rows[r][c]
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
                for r in range(9, len(rows)):
                    part_text = " ".join(str(rows[r][pc] or '').strip() for pc in part_cols if pc < len(rows[r])).lower()

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

                    p_val = clean_val(rows[r][p_col] if p_col < len(rows[r]) else None)
                    pol_val = clean_val(rows[r][pol_col] if pol_col < len(rows[r]) else None)
                    lives_val = clean_val(rows[r][lives_col] if lives_col < len(rows[r]) else None)
                    sa_val = clean_val(rows[r][sa_col] if sa_col < len(rows[r]) else None)

                    if p_val > 5000000.0: p_val /= 100.0
                    if sa_val > 50000000.0: sa_val /= 100.0

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
        if 'L-1' in sheet_data:
            rows = sheet_data['L-1']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)

                part_col = None
                for c in range(sc, ec + 1):
                    for r in range(6, min(14, len(rows))):
                        txt = str(rows[r][c] or '').strip().lower()
                        if 'particular' in txt and part_col is None:
                            part_col = c
                            break
                    if part_col is not None: break
                if part_col is None: part_col = sc

                total_col = None
                # Check for explicit Grand Total or Total Policyholder Fund
                for c in range(sc, ec + 1):
                    if c == part_col: continue
                    for r in range(6, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'grand total' in txt or 'total policyholder' in txt or txt == 'total':
                            total_col = c
                            break
                    if total_col is not None: break

                if total_col is None:
                    for c in range(sc, ec + 1):
                        if c == part_col: continue
                        for r in range(6, min(14, len(rows))):
                            txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                            if ('for the quarter' in txt or 'up to the quarter' in txt or 'quarter ended' in txt) and 'previous' not in txt and 'corresponding' not in txt:
                                total_col = c
                                break
                        if total_col is not None: break

                if total_col is None: total_col = ec

                # Magnitude check for L-1
                for r in range(12, min(30, len(rows))):
                    v = str(rows[r][total_col] if total_col < len(rows[r]) else '')
                    try:
                        fv = float(v.replace(',', ''))
                        if fv > 5000000.0 and mult == 1.0:
                            mult = 0.01
                            break
                    except: pass

                comm_found = False
                for r in range(10, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    raw_val = clean_val(rows[r][total_col] if total_col < len(rows[r]) else None)
                    val = round(raw_val * mult, 4)

                    if 'commission' in line and 'gross' not in line and not comm_found:
                        if val > 0:
                            metrics[pid]['comm_expense'] = val
                            comm_found = True
                        else:
                            # Search next 8 rows for Sub Total
                            for r_sub in range(r + 1, min(r + 8, len(rows))):
                                sub_line = str(rows[r_sub][part_col] or '').strip().lower()
                                sub_val = round(clean_val(rows[r_sub][total_col] if total_col < len(rows[r_sub]) else None) * mult, 4)
                                if 'sub total' in sub_line and sub_val > 0:
                                    metrics[pid]['comm_expense'] = sub_val
                                    comm_found = True
                                    break
                    elif 'operating expenses' in line:
                        metrics[pid]['opex_expense'] = val
                    elif 'surrender' in line:
                        metrics[pid]['surrenders'] = val
                    elif 'surplus' in line or 'deficit' in line or 'transferred to shareholders' in line:
                        if 'business_profit' not in metrics[pid]:
                            metrics[pid]['business_profit'] = val

        # ----------------------------------------------------
        # SCHEDULE L-2: Profit & Loss Account (PBT, PAT, Carried Forward)
        # ----------------------------------------------------
        if 'L-2' in sheet_data:
            rows = sheet_data['L-2']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)

                part_col = None
                for c in range(sc, ec + 1):
                    for r in range(8, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'particular' in txt and part_col is None: part_col = c; break
                    if part_col is not None: break
                if part_col is None: part_col = sc

                q_col = None
                for c in range(sc, ec + 1):
                    if c == part_col: continue
                    for r in range(8, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if ('for the quarter' in txt or 'up to the quarter' in txt or 'quarter ended' in txt) and 'previous' not in txt and 'corresponding' not in txt:
                            q_col = c; break
                    if q_col is not None: break

                if q_col is None:
                    q_col = part_col + 2 if part_col + 2 <= ec else part_col + 1

                # Magnitude check for L-2
                for r in range(12, min(35, len(rows))):
                    v = str(rows[r][q_col] if q_col < len(rows[r]) else '')
                    try:
                        fv = abs(float(v.replace(',', '')))
                        if fv > 5000000.0 and mult == 1.0:
                            mult = 0.01
                            break
                    except: pass

                for r in range(10, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = round(clean_val(rows[r][q_col] if q_col < len(rows[r]) else None) * mult, 4)
                    norm_line = re.sub(r'[\(\)/]+', ' ', line)

                    if re.search(r'(?:profit|loss).*before tax', norm_line):
                        metrics[pid]['profit_before_tax'] = val
                    elif re.search(r'(?:profit|loss).*after tax', norm_line):
                        metrics[pid]['profit_after_tax'] = val
                    elif 'balance' in norm_line and ('brought forward' in norm_line or 'carried forward' in norm_line or 'carried to balance' in norm_line):
                        metrics[pid]['profit_loss_carried_forward'] = val

        # ----------------------------------------------------
        # SCHEDULE L-7: Benefits Paid / Claims (Death, Maturity, Total)
        # ----------------------------------------------------
        if 'L-7' in sheet_data:
            rows = sheet_data['L-7']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)

                part_col = None
                for c in range(sc, ec + 1):
                    for r in range(7, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'particular' in txt and part_col is None: part_col = c; break
                    if part_col is not None: break
                if part_col is None: part_col = sc

                q_col = None
                for c in range(sc, ec + 1):
                    if c == part_col: continue
                    for r in range(7, min(14, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if ('for the quarter' in txt or 'up to the quarter' in txt or 'quarter ended' in txt) and 'previous' not in txt and 'corresponding' not in txt:
                            q_col = c; break
                    if q_col is not None: break

                if q_col is None:
                    q_col = part_col + 1 if part_col + 1 <= ec else part_col

                # Magnitude check for L-7
                for r in range(9, min(25, len(rows))):
                    v = str(rows[r][q_col] if q_col < len(rows[r]) else '')
                    try:
                        fv = float(v.replace(',', ''))
                        if fv > 5000000.0 and mult == 1.0:
                            mult = 0.01
                            break
                    except: pass

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    if 'ceded in reinsurance' in line or 'amount ceded' in line or '2. (' in line or '2.(' in line:
                        break
                    val = round(clean_val(rows[r][q_col] if q_col < len(rows[r]) else None) * mult, 4)
                    norm_line = re.sub(r'[\(\)/]+', ' ', line)

                    if 'claims by death' in norm_line or 'death claims' in norm_line:
                        if metrics[pid].get('death_claims_amount') is None or metrics[pid].get('death_claims_amount') == 0:
                            metrics[pid]['death_claims_amount'] = val
                    elif 'by maturity' in norm_line or 'maturity' in norm_line:
                        if metrics[pid].get('maturity_amount') is None or metrics[pid].get('maturity_amount') == 0:
                            metrics[pid]['maturity_amount'] = val
                    elif 'total' in norm_line and ('benefits' in norm_line or 'claims' in norm_line):
                        metrics[pid]['total_claim_amount_reported'] = val

        # ----------------------------------------------------
        # SCHEDULE L-8 & L-9: Share Capital & Reserves (Net Worth)
        # ----------------------------------------------------
        if 'L-8' in sheet_data:
            rows = sheet_data['L-8']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)
                part_col = sc
                for c in range(sc, ec + 1):
                    for r in range(6, min(12, len(rows))):
                        if 'particular' in str(rows[r][c] or '').lower(): part_col = c; break
                q_col = part_col + 1 if part_col + 1 <= ec else part_col

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = round(clean_val(rows[r][q_col] if q_col < len(rows[r]) else None) * mult, 4)
                    if 'total' in line:
                        metrics[pid]['share_capital'] = val
                        break

        if 'L-9' in sheet_data:
            rows = sheet_data['L-9']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)
                part_col = sc
                for c in range(sc, ec + 1):
                    for r in range(6, min(12, len(rows))):
                        if 'particular' in str(rows[r][c] or '').lower(): part_col = c; break
                q_col = part_col + 1 if part_col + 1 <= ec else part_col
                reserves_total = 0.0

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = round(clean_val(rows[r][q_col] if q_col < len(rows[r]) else None) * mult, 4)
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
        if 'L-22' in sheet_data:
            rows = sheet_data['L-22']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col = sc
                q_col = sc + 1
                for c in range(sc, ec + 1):
                    for r in range(6, min(13, len(rows))):
                        txt = re.sub(r'\s+', ' ', str(rows[r][c] or '').strip().lower())
                        if 'particular' in txt: part_col = c
                        if ('for the quarter' in txt or 'up to the quarter' in txt or 'quarter ended' in txt) and 'previous' not in txt and 'corresponding' not in txt:
                            q_col = c

                current_p_basis = None
                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = clean_val(rows[r][q_col] if q_col < len(rows[r]) else None)

                    if 'by number of policies' in line: current_p_basis = 'COUNT'
                    elif 'by premium' in line: current_p_basis = 'PREMIUM'

                    if '13th month' in line:
                        if current_p_basis == 'PREMIUM' or 'persistency_13m_prem' not in metrics[pid]:
                            metrics[pid]['persistency_13m_prem'] = val
                        if current_p_basis == 'COUNT' or 'persistency_13m_count' not in metrics[pid]:
                            metrics[pid]['persistency_13m_count'] = val
                        persistency_records.append({
                            'company_id': company_id, 'period_id': pid, 'cohort_month': 13,
                            'premium_basis_type': current_p_basis or 'PREMIUM',
                            'basis_metric': 'PERCENT', 'persistency_ratio_pct': val
                        })
                    elif '25th month' in line:
                        if current_p_basis == 'PREMIUM': metrics[pid]['persistency_25m_prem'] = val
                        else: metrics[pid]['persistency_25m_count'] = val
                        persistency_records.append({
                            'company_id': company_id, 'period_id': pid, 'cohort_month': 25,
                            'premium_basis_type': current_p_basis or 'PREMIUM',
                            'basis_metric': 'PERCENT', 'persistency_ratio_pct': val
                        })
                    elif '37th month' in line:
                        if current_p_basis == 'PREMIUM': metrics[pid]['persistency_37m_prem'] = val
                        else: metrics[pid]['persistency_37m_count'] = val
                        persistency_records.append({
                            'company_id': company_id, 'period_id': pid, 'cohort_month': 37,
                            'premium_basis_type': current_p_basis or 'PREMIUM',
                            'basis_metric': 'PERCENT', 'persistency_ratio_pct': val
                        })
                    elif '49th month' in line:
                        if current_p_basis == 'PREMIUM': metrics[pid]['persistency_49m_prem'] = val
                        else: metrics[pid]['persistency_49m_count'] = val
                        persistency_records.append({
                            'company_id': company_id, 'period_id': pid, 'cohort_month': 49,
                            'premium_basis_type': current_p_basis or 'PREMIUM',
                            'basis_metric': 'PERCENT', 'persistency_ratio_pct': val
                        })
                    elif '61st month' in line:
                        if current_p_basis == 'PREMIUM': metrics[pid]['persistency_61m_prem'] = val
                        else: metrics[pid]['persistency_61m_count'] = val
                        persistency_records.append({
                            'company_id': company_id, 'period_id': pid, 'cohort_month': 61,
                            'premium_basis_type': current_p_basis or 'PREMIUM',
                            'basis_metric': 'PERCENT', 'persistency_ratio_pct': val
                        })
                    elif 'conservation ratio' in line:
                        metrics[pid]['conservation_ratio'] = val
                    elif 'solvency ratio' in line:
                        if val > 0:
                            norm_solvency = val if val < 10.0 else round(val / 100.0, 4)
                            metrics[pid]['solvency_ratio'] = norm_solvency
                    elif 'roe' in line or 'return on equity' in line:
                        metrics[pid]['roe_pct'] = val

        # ----------------------------------------------------
        # SCHEDULE L-32: Solvency Margin Fallback (e.g. for LIC)
        # ----------------------------------------------------
        if 'L-32' in sheet_data:
            rows = sheet_data['L-32']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                if metrics[pid].get('solvency_ratio') is not None and metrics[pid].get('solvency_ratio') > 0:
                    continue
                sc, ec = b['start_col'], b['end_col']

                for r in range(len(rows)):
                    line = " ".join(str(rows[r][c] or '') for c in range(sc, min(ec + 1, len(rows[r])))).lower()
                    if 'solvency ratio' in line:
                        for c in range(sc, min(ec + 1, len(rows[r]))):
                            val = rows[r][c]
                            if isinstance(val, (int, float)) and val > 0 and val != 10:
                                norm_s = val if val < 10.0 else round(val / 100.0, 4)
                                metrics[pid]['solvency_ratio'] = norm_s
                                break

        # ----------------------------------------------------
        # SCHEDULE L-38: Channels & Intermediaries
        # ----------------------------------------------------
        if 'L-38' in sheet_data:
            rows = sheet_data['L-38']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)
                part_col = sc + 1 if sc + 1 <= ec else sc
                pol_col = sc + 2 if sc + 2 <= ec else sc + 1
                prem_col = sc + 3 if sc + 3 <= ec else sc + 2

                channel_map = {
                    'individual agents': 'channel_agency_prem',
                    'corporate agents-banks': 'channel_banca_prem',
                    'brokers': 'channel_broker_prem',
                    'direct business': 'channel_direct_prem',
                    'web aggregators': 'channel_web_aggregator_prem'
                }
                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    pol_val = clean_int(rows[r][pol_col] if pol_col < len(rows[r]) else None)
                    raw_prem = clean_val(rows[r][prem_col] if prem_col < len(rows[r]) else None)
                    prem_val = round(raw_prem * mult, 4)

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
        # SCHEDULE L-41: Grievances / Complaints
        # ----------------------------------------------------
        if 'L-41' in sheet_data:
            rows = sheet_data['L-41']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col = sc
                for c in range(sc, ec + 1):
                    for r in range(6, min(12, len(rows))):
                        if 'particular' in str(rows[r][c] or '').lower(): part_col = c; break
                reg_col = part_col + 2 if part_col + 2 <= ec else ec

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = clean_int(rows[r][reg_col] if reg_col < len(rows[r]) else None)
                    if 'total number of complaints' in line:
                        metrics[pid]['total_complaints'] = val
                        break

        # ----------------------------------------------------
        # SCHEDULE L-45: Offices, Branches & Agents
        # ----------------------------------------------------
        if 'L-45' in sheet_data:
            rows = sheet_data['L-45']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                part_col = sc
                for c in range(sc, ec + 1):
                    for r in range(6, min(12, len(rows))):
                        if 'particular' in str(rows[r][c] or '').lower(): part_col = c; break
                num_col = part_col + 2 if part_col + 2 <= ec else ec

                for r in range(8, len(rows)):
                    line = str(rows[r][part_col] or '').strip().lower() if part_col < len(rows[r]) else ''
                    val = clean_int(rows[r][num_col] if num_col < len(rows[r]) else None)
                    if 'no of branches at the end of' in line or 'no. of offices at the end' in line:
                        metrics[pid]['number_offices_branches'] = val
                    elif 'no. of insurance agents' in line:
                        metrics[pid]['number_individual_agents'] = val

        # ----------------------------------------------------
        # SCHEDULE L-25 (i): Geographical Distribution
        # ----------------------------------------------------
        if 'L-25 (i)' in sheet_data:
            rows = sheet_data['L-25 (i)']
            for b in scan_quarter_blocks_rows(rows):
                pid = b['period_id']
                if pid not in metrics: continue
                sc, ec = b['start_col'], b['end_col']
                mult = detect_unit_multiplier(rows, sc, ec)

                part_col = sc + 1 if sc + 1 <= ec else sc
                r_pol_c = sc + 2 if sc + 2 <= ec else sc + 1
                r_prem_c = sc + 3 if sc + 3 <= ec else sc + 2
                r_sa_c = sc + 4 if sc + 4 <= ec else sc + 3
                u_pol_c = sc + 5 if sc + 5 <= ec else sc + 4
                u_prem_c = sc + 6 if sc + 6 <= ec else sc + 5
                u_sa_c = sc + 7 if sc + 7 <= ec else sc + 6

                current_reg_type = 'STATE'
                for r in range(11, min(len(rows), 65)):
                    reg_name = str(rows[r][part_col] or '').strip() if part_col < len(rows[r]) else ''
                    if not reg_name or reg_name.lower().startswith('note') or 'particular' in reg_name.lower():
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

                    rp = clean_int(rows[r][r_pol_c] if r_pol_c < len(rows[r]) else None)
                    rprem = round(clean_val(rows[r][r_prem_c] if r_prem_c < len(rows[r]) else None) * mult, 4)
                    rsa = round(clean_val(rows[r][r_sa_c] if r_sa_c < len(rows[r]) else None) * mult, 4)
                    up = clean_int(rows[r][u_pol_c] if u_pol_c < len(rows[r]) else None)
                    uprem = round(clean_val(rows[r][u_prem_c] if u_prem_c < len(rows[r]) else None) * mult, 4)
                    usa = round(clean_val(rows[r][u_sa_c] if u_sa_c < len(rows[r]) else None) * mult, 4)

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

            # Total non-single
            m['total_non_single_premium'] = round(fy_p + renewal_p, 4)

            # Claims
            d_claims = m.get('death_claims_amount', 0.0) or 0.0
            mat_claims = m.get('maturity_amount', 0.0) or 0.0
            tot_claims = d_claims + mat_claims
            if tot_claims == 0.0 and m.get('total_claim_amount_reported', 0.0) > 0:
                tot_claims = m.get('total_claim_amount_reported', 0.0)
            m['total_claim_amount'] = round(tot_claims, 4)

            # Expenses
            c_exp = m.get('comm_expense', 0.0) or 0.0
            op_exp = m.get('opex_expense', 0.0) or 0.0
            m['total_expense'] = round(c_exp + op_exp, 4)

            # Net Worth
            sc = m.get('share_capital', 0.0) or 0.0
            res = m.get('reserves_and_surplus', 0.0) or 0.0
            sp = m.get('share_premium', 0.0) or 0.0
            cf = m.get('profit_loss_carried_forward', 0.0) or 0.0
            nw = sc + res if res != 0.0 else sc + sp + cf
            m['net_worth'] = round(nw, 4)

            # Average ticket size
            tot_pols = m.get('total_policies', 0) or 0
            if tot_pols > 0 and gwp > 0:
                m['avg_ticket_size_inr'] = round((gwp * 100000.0) / tot_pols, 2)
            else:
                m['avg_ticket_size_inr'] = 0.0

            # Growth metrics (QoQ / YoY against previous quarter in sequence)
            if i > 0:
                prev_pid = ordered_periods[i - 1]
                prev_m = metrics[prev_pid]
                prev_gwp = prev_m.get('gross_written_premium', 0.0) or 0.0
                prev_pols = prev_m.get('total_policies', 0) or 0
                prev_sa = prev_m.get('total_sum_assured', 0.0) or 0.0

                if prev_gwp > 0 and gwp > 0:
                    m['avg_premium_growth_pct'] = round(((gwp - prev_gwp) / prev_gwp) * 100.0, 2)
                else:
                    m['avg_premium_growth_pct'] = None

                if prev_pols > 0 and tot_pols > 0:
                    m['policy_sales_growth_pct'] = round(((tot_pols - prev_pols) / prev_pols) * 100.0, 2)
                else:
                    m['policy_sales_growth_pct'] = None

                if prev_sa > 0 and m.get('total_sum_assured', 0.0) > 0:
                    m['avg_sum_assured_growth_pct'] = round(((m['total_sum_assured'] - prev_sa) / prev_sa) * 100.0, 2)
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
        print(f"Persisting {len(metrics)} quarterly records to fact_company_quarterly_metrics...")
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
            print(f"Persisting {len(geo_records)} records to fact_geographical_distribution...")
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
            print(f"Persisting {len(persistency_records)} records to fact_persistency_cohorts...")
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
            print(f"Persisting {len(channel_records)} records to fact_intermediary_channel_metrics...")
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
        print(f"✅ Ingestion completed successfully for {company_id} ({len(ordered_periods)} quarters)!\n")
        return metrics
