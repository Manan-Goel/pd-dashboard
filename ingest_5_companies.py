#!/usr/bin/env python3
"""
Ingest 5 Life Insurance Companies into life_insurance_curated_v2.db:
1. HDFC Life (HDFC_Consolidated.xlsx)
2. LIC (LIC_Consolidated.xlsx)
3. Canara HSBC Life (CANARA_HSBC_LIFE_INSURANCE_Consolidated.xlsx)
4. ICICI Prudential Life (ICICI_PRUDENTIAL_LIFE_INSURANCE_Consolidated.xlsx)
5. SBI Life (SBI_LIFE_INSURANCE_Consolidated.xlsx)

Re-computes market share metrics across companies and exports updated data to api/all-data.json.
"""

import os
import sys
import json
import time
import sqlite3
from src.pipeline.curated_metrics_pipeline_v2 import CuratedMetricsPipelineV2, COMPANY_METADATA

DB_PATH = "life_insurance_curated_v2.db"

COMPANIES_TO_INGEST = [
    ('HDFC_LIFE', 'HDFC_Consolidated.xlsx'),
    ('LIC', 'LIC_Consolidated.xlsx'),
    ('CANARA_HSBC_LIFE', 'CANARA_HSBC_LIFE_INSURANCE_Consolidated.xlsx'),
    ('ICICI_PRUDENTIAL_LIFE', 'ICICI_PRUDENTIAL_LIFE_INSURANCE_Consolidated.xlsx'),
    ('SBI_LIFE', 'SBI_LIFE_INSURANCE_Consolidated.xlsx')
]

def main():
    print("=" * 75)
    print("🏛️ LIFE INSURANCE CURATED V2 MULTI-COMPANY INGESTION")
    print(f"Target Database: {os.path.abspath(DB_PATH)}")
    print("=" * 75)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Ensure all companies are in dim_company
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
    for cid, fname in COMPANIES_TO_INGEST:
        if not os.path.exists(fname):
            print(f"❌ Error: File {fname} not found!")
            continue
        t0 = time.time()
        metrics = pipeline.ingest_company_workbook(fname, cid)
        elapsed = time.time() - t0
        ingested_counts[cid] = len(metrics)
        print(f"⏱️ Finished {cid} in {elapsed:.2f}s ({len(metrics)} quarters)\n")

    # 3. Compute Market Share Ratios across companies per period
    print("Computing market share percentages across all companies...")
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

    # 4. Export updated data to api/all-data.json
    print("Exporting updated multi-company dataset to api/all-data.json...")
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
    print("=" * 75)
    print(f"🎉 MULTI-COMPANY INGESTION COMPLETE IN {total_time:.2f}s!")
    print(f"Total Companies: {len(all_companies)}")
    print(f"Total Quarterly Metric Records: {len(all_metrics)}")
    print(f"Total Geographic Distribution Records: {len(all_geo)}")
    print(f"Total Persistency Records: {len(all_persistency)}")
    print(f"Total Channel Records: {len(all_channels)}")
    print(f"JSON Payload Size: {os.path.getsize('api/all-data.json') / 1024:.2f} KB")
    print("=" * 75)

    conn.close()

if __name__ == '__main__':
    main()
