import os
import sqlite3
import openpyxl

DB_PATH = "life_insurance_curated_v2.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def clean_val(v):
    if v is None: return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', 'None', '-', 'NA', 'Nil', 'NIL', '.', '*'): return 0.0
    try: return float(s)
    except: return 0.0

checkpoints = [
    # 1. MAX LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('MAX_LIFE', 'AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 34840641, 0.01, 348406.41, 'Form L-4 Total Premium (GWP)'),
    ('MAX_LIFE', 'AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-2', 'profit_after_tax', 'Row 28, Col 2', 'Profit After Tax', 708081, 0.01, 7080.81, 'Form L-2 Profit After Tax'),
    ('MAX_LIFE', 'AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.97, 1.0, 1.97, 'Form L-22 Solvency Ratio'),

    # 2. BAJAJ ALLIANZ LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('BAJAJ_ALLIANZ_LIFE', 'BAJAJ_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 14, Col 12', 'Total Premiums', 25154780, 0.01, 251547.8, 'Form L-4 Total Premium (GWP)'),
    ('BAJAJ_ALLIANZ_LIFE', 'BAJAJ_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-2', 'profit_after_tax', 'Row 30, Col 1', 'Profit After Tax', 840449, 0.01, 8404.49, 'Form L-2 Profit After Tax'),
    ('BAJAJ_ALLIANZ_LIFE', 'BAJAJ_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 7.6, 1.0, 7.6, 'Form L-22 Solvency Ratio'),

    # 3. KOTAK MAHINDRA LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('KOTAK_LIFE', 'KOTAK_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 16632592, 0.01, 166325.92, 'Form L-4 Total Premium (GWP)'),
    ('KOTAK_LIFE', 'KOTAK_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 2.57, 1.0, 2.57, 'Form L-22 Solvency Ratio'),

    # 4. TATA AIA LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('TATA_AIA_LIFE', 'TATA_AIA_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 20519620, 0.01, 205196.2, 'Form L-4 Total Premium (GWP)'),
    ('TATA_AIA_LIFE', 'TATA_AIA_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.95, 1.0, 1.95, 'Form L-22 Solvency Ratio'),

    # 5. PNB METLIFE (FY21-22 Q1, Unit: Lakhs Rs)
    ('PNB_METLIFE', 'PNB_METLIFE_INSURANCE_Consolidated (new).xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 14, Col 10', 'Total Premiums', 110967.2, 1.0, 110967.2, 'Form L-4 Total Premium (GWP)'),
    ('PNB_METLIFE', 'PNB_METLIFE_INSURANCE_Consolidated (new).xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.8, 1.0, 1.8, 'Form L-22 Solvency Ratio'),

    # 6. INDIAFIRST LIFE (FY21-22 Q1, Unit: Lakhs Rs)
    ('INDIAFIRST_LIFE', 'INDIAFIRST_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 90796.82, 1.0, 90796.82, 'Form L-4 Total Premium (GWP)'),
    ('INDIAFIRST_LIFE', 'INDIAFIRST_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.76, 1.0, 1.76, 'Form L-22 Solvency Ratio'),

    # 7. RELIANCE NIPPON LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('RELIANCE_NIPPON_LIFE', 'INDUSIND_NIPPON_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 8449034, 0.01, 84490.34, 'Form L-4 Total Premium (GWP)'),
    ('RELIANCE_NIPPON_LIFE', 'INDUSIND_NIPPON_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 2.35, 1.0, 2.35, 'Form L-22 Solvency Ratio'),

    # 8. SUD LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('SUD_LIFE', 'SUD_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 6880799, 0.01, 68807.99, 'Form L-4 Total Premium (GWP)'),
    ('SUD_LIFE', 'SUD_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 2.53, 1.0, 2.53, 'Form L-22 Solvency Ratio'),

    # 9. SHRIRAM LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('SHRIRAM_LIFE', 'SHRIRAM_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 3237582, 0.01, 32375.82, 'Form L-4 Total Premium (GWP)'),

    # 10. EDELWEISS TOKIO LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('EDELWEISS_TOKIO_LIFE', 'EDELWEISS_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 2151295, 0.01, 21512.95, 'Form L-4 Total Premium (GWP)'),
    ('EDELWEISS_TOKIO_LIFE', 'EDELWEISS_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.84, 1.0, 1.84, 'Form L-22 Solvency Ratio'),

    # 11. FUTURE GENERALI LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('FUTURE_GENERALI_LIFE', 'GENERALI_CENTRAL_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 16, Col 10', 'Total Premiums', 2247804, 0.01, 22478.04, 'Form L-4 Total Premium (GWP)'),
    ('FUTURE_GENERALI_LIFE', 'GENERALI_CENTRAL_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 1.84, 1.0, 1.84, 'Form L-22 Solvency Ratio'),

    # 12. PRAMERICA LIFE (FY21-22 Q1, Unit: Thousands Rs)
    ('PRAMERICA_LIFE', 'PRAMERICA_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-4', 'gross_written_premium', 'Row 15, Col 19', 'Total Premiums', 2323164, 0.01, 23231.64, 'Form L-4 Total Premium (GWP)'),
    ('PRAMERICA_LIFE', 'PRAMERICA_LIFE_INSURANCE_Consolidated.xlsx', 'FY2021-22_Q1', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 4.17, 1.0, 4.17, 'Form L-22 Solvency Ratio'),

    # 13. CREDITACCESS LIFE (FY24-25 Q4, Unit: Lakhs Rs)
    ('CREDITACCESS_LIFE', 'CREDITACCESS_LIFE_INSURANCE_Consolidated.xlsx', 'FY2024-25_Q4', 'L-4', 'gross_written_premium', 'Row 14, Col 54', 'Total Premiums', 9472.0, 1.0, 9472.0, 'Form L-4 Total Premium (GWP)'),
    ('CREDITACCESS_LIFE', 'CREDITACCESS_LIFE_INSURANCE_Consolidated.xlsx', 'FY2024-25_Q4', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 3.35, 1.0, 3.35, 'Form L-22 Solvency Ratio'),

    # 14. GO DIGIT LIFE (FY24-25 Q4, Unit: Lakhs Rs)
    ('GO_DIGIT_LIFE', 'GO_DIGIT_LIFE_INSURANCE_Consolidated.xlsx', 'FY2024-25_Q4', 'L-4', 'gross_written_premium', 'Row 12, Col 52', 'Total Premiums', 28717.0, 1.0, 28717.0, 'Form L-4 Total Premium (GWP)'),
    ('GO_DIGIT_LIFE', 'GO_DIGIT_LIFE_INSURANCE_Consolidated.xlsx', 'FY2024-25_Q4', 'L-22', 'solvency_ratio', 'L-22 Item 17', 'Solvency Ratio', 3.85, 1.0, 3.85, 'Form L-22 Solvency Ratio')
]

print("=" * 90)
print("🔬 EMPIRICAL VALIDATION: ALL 14 REMAINING LIFE INSURERS (BATCH 3)")
print(f"Target Database: {os.path.abspath(DB_PATH)}")
print("=" * 90)

matched = 0
total = len(checkpoints)

for cid, fname, pid, sheet, metric_col, coord, label, raw, mult, exp, desc in checkpoints:
    c.execute(f"SELECT {metric_col} FROM fact_company_quarterly_metrics WHERE company_id = ? AND period_id = ?", (cid, pid))
    row = c.fetchone()
    db_val = row[0] if row else None
    
    is_match = False
    if db_val is not None:
        if isinstance(exp, (float, int)):
            is_match = abs(float(db_val) - float(exp)) < 0.1
        else:
            is_match = (str(db_val).strip() == str(exp).strip())
            
    status = "EXACT MATCH" if is_match else "MISMATCH"
    if is_match: matched += 1
    
    print(f"[{status:11s}] {cid:22s} | {pid:13s} | {desc:32s}")
    print(f"               Excel Cell ({coord}) -> DB: {db_val} (Expected: {exp})")

print("=" * 90)
pct = (matched / total) * 100
print(f"📊 BATCH 3 VALIDATION SUMMARY: {matched}/{total} Checkpoints ({pct:.2f}%)")
print("=" * 90)
