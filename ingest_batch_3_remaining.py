#!/usr/bin/env python3
"""
Ingest Remaining 14 Life Insurance Companies into life_insurance_curated_v2.db:
1. Max Life (AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx)
2. Bajaj Allianz Life (BAJAJ_LIFE_INSURANCE_Consolidated.xlsx)
3. CreditAccess Life (CREDITACCESS_LIFE_INSURANCE_Consolidated.xlsx)
4. Edelweiss Tokio Life (EDELWEISS_LIFE_INSURANCE_Consolidated.xlsx)
5. Future Generali Life (GENERALI_CENTRAL_LIFE_INSURANCE_Consolidated.xlsx)
6. Go Digit Life (GO_DIGIT_LIFE_INSURANCE_Consolidated.xlsx)
7. IndiaFirst Life (INDIAFIRST_LIFE_INSURANCE_Consolidated.xlsx)
8. Reliance Nippon Life (INDUSIND_NIPPON_LIFE_INSURANCE_Consolidated.xlsx)
9. Kotak Mahindra Life (KOTAK_LIFE_INSURANCE_Consolidated.xlsx)
10. PNB MetLife (PNB_METLIFE_INSURANCE_Consolidated (new).xlsx)
11. Pramerica Life (PRAMERICA_LIFE_INSURANCE_Consolidated.xlsx)
12. Shriram Life (SHRIRAM_LIFE_INSURANCE_Consolidated.xlsx)
13. SUD Life (SUD_LIFE_INSURANCE_Consolidated.xlsx)
14. Tata AIA Life (TATA_AIA_LIFE_INSURANCE_Consolidated.xlsx)

Completes the entire Indian Life Insurance industry footprint (25 companies).
"""

import os
import sys
import json
import time
import sqlite3
from src.pipeline.curated_metrics_pipeline_v2 import CuratedMetricsPipelineV2, COMPANY_METADATA

DB_PATH = "life_insurance_curated_v2.db"

REMAINING_COMPANIES = [
    ('MAX_LIFE', 'AXIS_MAX_LIFE_INSURANCE_Consolidated.xlsx'),
    ('BAJAJ_ALLIANZ_LIFE', 'BAJAJ_LIFE_INSURANCE_Consolidated.xlsx'),
    ('CREDITACCESS_LIFE', 'CREDITACCESS_LIFE_INSURANCE_Consolidated.xlsx'),
    ('EDELWEISS_TOKIO_LIFE', 'EDELWEISS_LIFE_INSURANCE_Consolidated.xlsx'),
    ('FUTURE_GENERALI_LIFE', 'GENERALI_CENTRAL_LIFE_INSURANCE_Consolidated.xlsx'),
    ('GO_DIGIT_LIFE', 'GO_DIGIT_LIFE_INSURANCE_Consolidated.xlsx'),
    ('INDIAFIRST_LIFE', 'INDIAFIRST_LIFE_INSURANCE_Consolidated.xlsx'),
    ('RELIANCE_NIPPON_LIFE', 'INDUSIND_NIPPON_LIFE_INSURANCE_Consolidated.xlsx'),
    ('KOTAK_LIFE', 'KOTAK_LIFE_INSURANCE_Consolidated.xlsx'),
    ('PNB_METLIFE', 'PNB_METLIFE_INSURANCE_Consolidated (new).xlsx'),
    ('PRAMERICA_LIFE', 'PRAMERICA_LIFE_INSURANCE_Consolidated.xlsx'),
    ('SHRIRAM_LIFE', 'SHRIRAM_LIFE_INSURANCE_Consolidated.xlsx'),
    ('SUD_LIFE', 'SUD_LIFE_INSURANCE_Consolidated.xlsx'),
    ('TATA_AIA_LIFE', 'TATA_AIA_LIFE_INSURANCE_Consolidated.xlsx')
]

def main():
    print("=" * 80)
    print("🏛️ INGESTING 14 REMAINING LIFE INSURERS INTO CURATED V2 WAREHOUSE")
    print(f"Target Database: {os.path.abspath(DB_PATH)}")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Ensure all 25 companies are registered in dim_company
    for cid, meta in COMPANY_METADATA.items():
        cur.execute("""
            INSERT OR REPLACE INTO dim_company (company_id, company_name, short_name, irda_reg_no, category, active_status)
            VALUES (?, ?, ?, ?, ?, 'Active')
        """, (cid, meta['name'], meta['name'].split()[0], meta['reg_no'], meta.get('category', 'Private')))
    conn.commit()

    pipeline = CuratedMetricsPipelineV2(conn)
    total_start = time.time()

    # 2. Ingest each company
    ingested_counts = {}
    for idx, (cid, fname) in enumerate(REMAINING_COMPANIES, 1):
        if not os.path.exists(fname):
            print(f"❌ [{idx}/{len(REMAINING_COMPANIES)}] File {fname} not found!")
            continue
        print(f"\n🚀 [{idx}/{len(REMAINING_COMPANIES)}] Ingesting {cid} from {fname}...")
        t0 = time.time()
        try:
            metrics = pipeline.ingest_company_workbook(fname, cid)
            elapsed = time.time() - t0
            ingested_counts[cid] = len(metrics)
            print(f"⏱️ Finished {cid} in {elapsed:.2f}s ({len(metrics)} quarters)")
        except Exception as e:
            print(f"❌ Error ingesting {cid}: {e}")
            import traceback
            traceback.print_exc()

    # 3. Recompute Market Share Ratios across all companies per period
    print("\nRe-computing market share percentages across all 25 companies...")
    cur.execute("SELECT DISTINCT period_id FROM fact_company_quarterly_metrics")
    periods = [r[0] for r in cur.fetchall()]

    for pid in periods:
        cur.execute("""
            SELECT SUM(gross_written_premium), SUM(total_sum_assured), SUM(total_policies)
            FROM fact_company_quarterly_metrics
            WHERE period_id = ?
        """, (pid,))
        tot_gwp, tot_sa, tot_pol = cur.fetchone()
        tot_gwp = tot_gwp or 0.0
        tot_sa = tot_sa or 0.0
        tot_pol = tot_pol or 0

        cur.execute("""
            SELECT company_id, gross_written_premium, total_sum_assured, total_policies
            FROM fact_company_quarterly_metrics
            WHERE period_id = ?
        """, (pid,))
        rows = cur.fetchall()

        for cid, gwp, sa, pol in rows:
            ms_prem = round((gwp / tot_gwp) * 100.0, 2) if tot_gwp > 0 and gwp else 0.0
            ms_sa = round((sa / tot_sa) * 100.0, 2) if tot_sa > 0 and sa else 0.0
            ms_pol = round((pol / tot_pol) * 100.0, 2) if tot_pol > 0 and pol else 0.0

            cur.execute("""
                UPDATE fact_company_quarterly_metrics
                SET market_share_premium_pct = ?,
                    market_share_sum_assured_pct = ?,
                    market_share_policies_pct = ?
                WHERE company_id = ? AND period_id = ?
            """, (ms_prem, ms_sa, ms_pol, cid, pid))

    conn.commit()

    # 4. Export complete multi-company dataset to api/all-data.json
    print("Exporting complete 25-company dataset to api/all-data.json...")
    os.makedirs("api", exist_ok=True)
    conn.row_factory = sqlite3.Row
    c_read = conn.cursor()

    c_read.execute("SELECT * FROM v_all_64_metrics ORDER BY company_id, period_id")
    all_metrics = [dict(r) for r in c_read.fetchall()]

    c_read.execute("""
        SELECT company_id, period_id, region_type, region_name, total_policies, total_premium_lakhs, 
               total_sum_assured_lakhs, rural_policies, urban_policies 
        FROM fact_geographical_distribution 
        ORDER BY company_id, period_id, total_premium_lakhs DESC
    """)
    all_geo = [dict(r) for r in c_read.fetchall()]

    c_read.execute("""
        SELECT company_id, period_id, cohort_month, premium_basis_type, basis_metric, persistency_ratio_pct 
        FROM fact_persistency_cohorts 
        ORDER BY company_id, period_id, cohort_month
    """)
    all_persistency = [dict(r) for r in c_read.fetchall()]

    c_read.execute("""
        SELECT company_id, period_id, channel_name, policies_count, premium_lakhs, intermediary_count, productivity_inr 
        FROM fact_intermediary_channel_metrics 
        ORDER BY company_id, period_id, premium_lakhs DESC
    """)
    all_channels = [dict(r) for r in c_read.fetchall()]

    c_read.execute("SELECT company_id, company_name, short_name, irda_reg_no, category FROM dim_company ORDER BY company_name")
    all_companies = [dict(r) for r in c_read.fetchall()]

    export_payload = {
        'companies': all_companies,
        'metrics': all_metrics,
        'geo': all_geo,
        'persistency': all_persistency,
        'channels': all_channels
    }

    with open("api/all-data.json", "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2)

    total_time = time.time() - total_start
    print("=" * 80)
    print(f"🎉 ALL REMAINING COMPANIES INGESTED IN {total_time:.2f}s!")
    print(f"Total Companies in Warehouse: {len(all_companies)}")
    print(f"Total Quarterly Metric Records: {len(all_metrics)}")
    print(f"Total Geographic Distribution Records: {len(all_geo)}")
    print(f"Total Persistency Records: {len(all_persistency)}")
    print(f"Total Channel Records: {len(all_channels)}")
    print(f"JSON Payload Size: {os.path.getsize('api/all-data.json') / 1024:.2f} KB")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
