import os
import sqlite3
import openpyxl

DB_PATH = "life_insurance_curated_v2.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def clean_val(v):
    if v is None:
        return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', 'None', '-', 'NA', 'Nil', 'NIL', '.', '*'):
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

print("=" * 90)
print("🔎 DEEP MULTI-DIMENSIONAL AUDIT OF 5 NEWLY INGESTED LIFE INSURERS")
print(f"Target Database: {os.path.abspath(DB_PATH)}")
print("=" * 90)

# Checkpoints across all 5 companies and multiple quarters and statutory schedules
audit_checkpoints = [
    # =========================================================================
    # 1. ADITYA BIRLA SUN LIFE INSURANCE
    # =========================================================================
    # Form L-4 Premium
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-4',
        'metric': 'financial_year_premium',
        'cell': 'Row 11, Col 2',
        'raw_val': 3316571,
        'unit': "'000",
        'expected': 33165.71,
        'desc': 'Form L-4 First Year Premium'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-4',
        'metric': 'renewal_premium',
        'cell': 'Row 12, Col 2',
        'raw_val': 10922906,
        'unit': "'000",
        'expected': 109229.06,
        'desc': 'Form L-4 Renewal Premium'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-4',
        'metric': 'total_single_premium',
        'cell': 'Row 13, Col 2',
        'raw_val': 3388511,
        'unit': "'000",
        'expected': 33885.11,
        'desc': 'Form L-4 Single Premium'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Row 33, Col 2',
        'raw_val': 246162,
        'unit': "'000",
        'expected': 2461.62,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Row 70, Col 2',
        'raw_val': 1.82,
        'unit': 'Ratio',
        'expected': 1.82,
        'desc': 'Form L-22 Solvency Ratio'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Form L-4 Total',
        'raw_val': 703413,
        'unit': 'Lakhs',
        'expected': 703413.0,
        'desc': 'Form L-4 Q4 Total Premium'
    },
    {
        'cid': 'ADITYA_BIRLA_SUN_LIFE',
        'file': 'ADITYA_BIRLA_SUN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Form L-2 PAT',
        'raw_val': 3925,
        'unit': 'Lakhs',
        'expected': 3925.0,
        'desc': 'Form L-2 Q4 Profit After Tax'
    },

    # =========================================================================
    # 2. AGEAS FEDERAL LIFE INSURANCE
    # =========================================================================
    {
        'cid': 'AGEAS_FEDERAL_LIFE',
        'file': 'AGEAS_FEDERAL_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Row 32, Col 2',
        'raw_val': 101661,
        'unit': "'000",
        'expected': 1016.61,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'AGEAS_FEDERAL_LIFE',
        'file': 'AGEAS_FEDERAL_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 3.08,
        'unit': 'Ratio',
        'expected': 3.08,
        'desc': 'Form L-22 Solvency Ratio'
    },
    {
        'cid': 'AGEAS_FEDERAL_LIFE',
        'file': 'AGEAS_FEDERAL_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Form L-4 Total',
        'raw_val': 269737,
        'unit': 'Lakhs',
        'expected': 269737.0,
        'desc': 'Form L-4 Q4 Total Premium'
    },
    {
        'cid': 'AGEAS_FEDERAL_LIFE',
        'file': 'AGEAS_FEDERAL_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 2.6993,
        'unit': 'Ratio',
        'expected': 2.6993,
        'desc': 'Form L-22 Solvency Ratio'
    },

    # =========================================================================
    # 3. AVIVA LIFE INSURANCE
    # =========================================================================
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Row 12, Col 2',
        'raw_val': 2167216,
        'unit': "'000",
        'expected': 21672.16,
        'desc': 'Form L-4 Total Premium'
    },
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Form L-2 PAT',
        'raw_val': -36356,
        'unit': "'000",
        'expected': -363.56,
        'desc': 'Form L-2 PAT Net Loss'
    },
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 2.22,
        'unit': 'Ratio',
        'expected': 2.22,
        'desc': 'Form L-22 Solvency Ratio'
    },
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Form L-4 Total (Q4 column)',
        'raw_val': 48973,
        'unit': 'Lakhs',
        'expected': 48973.0,
        'desc': 'Form L-4 Q4 Total Premium'
    },
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Form L-2 PAT',
        'raw_val': 10752,
        'unit': 'Lakhs',
        'expected': 10752.0,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'AVIVA_LIFE',
        'file': 'AVIVA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 1.93,
        'unit': 'Ratio',
        'expected': 1.93,
        'desc': 'Form L-22 Solvency Ratio'
    },

    # =========================================================================
    # 4. BANDHAN LIFE INSURANCE
    # =========================================================================
    {
        'cid': 'BANDHAN_LIFE',
        'file': 'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Row 34, Col 2',
        'raw_val': -260493,
        'unit': "'000",
        'expected': -2604.93,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'BANDHAN_LIFE',
        'file': 'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Row 62, Col 2',
        'raw_val': 2.36,
        'unit': 'Ratio',
        'expected': 2.36,
        'desc': 'Form L-22 Solvency Ratio'
    },
    {
        'cid': 'BANDHAN_LIFE',
        'file': 'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Form L-4 Total',
        'raw_val': 20579,
        'unit': 'Lakhs',
        'expected': 20579.0,
        'desc': 'Form L-4 Total Premium'
    },
    {
        'cid': 'BANDHAN_LIFE',
        'file': 'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Form L-2 PAT',
        'raw_val': -1895,
        'unit': 'Lakhs',
        'expected': -1895.0,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'BANDHAN_LIFE',
        'file': 'BANDHAN_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 2.48,
        'unit': 'Ratio',
        'expected': 2.48,
        'desc': 'Form L-22 Solvency Ratio'
    },

    # =========================================================================
    # 5. BHARTI AXA LIFE INSURANCE
    # =========================================================================
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-4',
        'metric': 'gross_written_premium',
        'cell': 'Row 12, Col 2',
        'raw_val': 4290266,
        'unit': "'000",
        'expected': 42902.66,
        'desc': 'Form L-4 Gross Written Premium'
    },
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Row 26, Col 2',
        'raw_val': -842439,
        'unit': "'000",
        'expected': -8424.39,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2021-22_Q1',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 1.76,
        'unit': 'Ratio',
        'expected': 1.76,
        'desc': 'Form L-22 Solvency Ratio'
    },
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-4',
        'metric': 'total_premium',
        'cell': 'Form L-4 Total',
        'raw_val': 108565,
        'unit': 'Lakhs',
        'expected': 108565.0,
        'desc': 'Form L-4 Total Premium'
    },
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-2',
        'metric': 'profit_after_tax',
        'cell': 'Form L-2 PAT',
        'raw_val': 2404,
        'unit': 'Lakhs',
        'expected': 2404.0,
        'desc': 'Form L-2 Profit After Tax'
    },
    {
        'cid': 'BHARTI_AXA_LIFE',
        'file': 'BHARTI_AXA_LIFE_INSURANCE_Consolidated.xlsx',
        'pid': 'FY2024-25_Q4',
        'sheet': 'L-22',
        'metric': 'solvency_ratio',
        'cell': 'Form L-22 Solvency',
        'raw_val': 1.67,
        'unit': 'Ratio',
        'expected': 1.67,
        'desc': 'Form L-22 Solvency Ratio'
    }
]

# Run reconciliation
matched = 0
failed = 0

for cp in audit_checkpoints:
    cid = cp['cid']
    pid = cp['pid']
    m = cp['metric']
    exp = cp['expected']
    
    c.execute(f"SELECT {m} FROM fact_company_quarterly_metrics WHERE company_id = ? AND period_id = ?", (cid, pid))
    row = c.fetchone()
    db_val = row[0] if row else None
    
    is_match = False
    if db_val is not None:
        if isinstance(exp, float):
            is_match = abs(float(db_val) - exp) < 0.05
        else:
            is_match = (db_val == exp)
            
    status = "EXACT MATCH" if is_match else "MISMATCH"
    if is_match:
        matched += 1
    else:
        failed += 1
        
    print(f"[{status:11s}] {cid:22s} | {pid:13s} | {cp['desc']:32s}")
    print(f"               Excel Raw: {cp['raw_val']} ({cp['unit']}) -> DB: {db_val} (Expected: {exp})")

print("\n" + "=" * 90)
print(f"📊 BATCH 2 DEEP AUDIT SUMMARY: {matched}/{len(audit_checkpoints)} Checkpoints Verified ({(matched/len(audit_checkpoints))*100:.2f}%)")
print("=" * 90)

# Check Satellite Tables: Geo, Persistency, Channels
print("\n" + "=" * 90)
print("🌍 SATELLITE TABLES AUDIT (Geographic, Persistency, Intermediary Channels)")
print("=" * 90)

for cid in ['ADITYA_BIRLA_SUN_LIFE', 'AGEAS_FEDERAL_LIFE', 'AVIVA_LIFE', 'BANDHAN_LIFE', 'BHARTI_AXA_LIFE']:
    # Geo
    c.execute("SELECT count(*), count(DISTINCT region_name), sum(total_premium_lakhs) FROM fact_geographical_distribution WHERE company_id = ?", (cid,))
    g_cnt, g_reg, g_prem = c.fetchone()
    
    # Persistency
    c.execute("SELECT count(*), count(DISTINCT cohort_month) FROM fact_persistency_cohorts WHERE company_id = ?", (cid,))
    p_cnt, p_hor = c.fetchone()
    
    # Channels
    c.execute("SELECT count(*), count(DISTINCT channel_name), sum(premium_lakhs) FROM fact_intermediary_channel_metrics WHERE company_id = ?", (cid,))
    ch_cnt, ch_names, ch_prem = c.fetchone()
    
    print(f"Insurer: {cid}")
    print(f"  • Geographical (L-34): {g_cnt} records across {g_reg} States/UTs (Cumulative Premium: ₹{g_prem:,.1f} Lakhs)")
    print(f"  • Persistency (L-33):  {p_cnt} cohort records across {p_hor} cohort horizons (13M, 25M, 37M, 49M, 61M)")
    print(f"  • Channels (L-35):     {ch_cnt} channel records across {ch_names} distribution channels (Cumulative Premium: ₹{ch_prem:,.1f} Lakhs)")

conn.close()
