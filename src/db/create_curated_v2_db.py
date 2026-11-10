#!/usr/bin/env python3
"""
Create a separate SQLite database: life_insurance_curated_v2.db
Contains exclusively the new curated schema and the ACKO Life Insurance data.
"""

import os
import sqlite3
import sys

SRC_DB = "life_insurance.db"
DST_DB = "life_insurance_curated_v2.db"

def main():
    if os.path.exists(DST_DB):
        print(f"Removing existing {DST_DB}...")
        os.remove(DST_DB)

    print(f"Connecting to source database: {SRC_DB}...")
    src_conn = sqlite3.connect(SRC_DB)
    src_cur = src_conn.cursor()

    print(f"Creating new destination database: {DST_DB}...")
    dst_conn = sqlite3.connect(DST_DB)
    dst_cur = dst_conn.cursor()

    # Tables to transfer
    curated_tables = [
        "dim_company",
        "dim_period",
        "dim_statement_schedule",
        "fact_company_quarterly_metrics",
        "fact_geographical_distribution",
        "fact_persistency_cohorts",
        "fact_intermediary_channel_metrics"
    ]

    # 1. Transfer Table Schemas and Indexes
    for table in curated_tables:
        src_cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
        ddl = src_cur.fetchone()
        if ddl and ddl[0]:
            print(f"Creating table {table}...")
            dst_cur.execute(ddl[0])
        else:
            print(f"Warning: DDL for {table} not found!")

        # Also transfer any explicit indexes on this table
        src_cur.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,))
        for idx in src_cur.fetchall():
            if idx[0]:
                dst_cur.execute(idx[0])

    # 2. Transfer Data
    # For dim_company: transfer ACKO Life (and other companies as dimension master if desired)
    print("Transferring dim_company (ACKO Life Insurance)...")
    src_cur.execute("SELECT * FROM dim_company WHERE company_id = 'ACKO_LIFE'")
    acko_comp = src_cur.fetchall()
    src_cur.execute("PRAGMA table_info(dim_company)")
    comp_cols = [c[1] for c in src_cur.fetchall()]
    placeholders = ",".join(["?"] * len(comp_cols))
    dst_cur.executemany(f"INSERT INTO dim_company ({','.join(comp_cols)}) VALUES ({placeholders})", acko_comp)

    # For dim_period: transfer periods corresponding to Acko's active timeline
    print("Transferring dim_period...")
    src_cur.execute("""
        SELECT * FROM dim_period 
        WHERE period_id IN (SELECT DISTINCT period_id FROM fact_company_quarterly_metrics WHERE company_id = 'ACKO_LIFE')
        ORDER BY chronological_sequence
    """)
    periods = src_cur.fetchall()
    src_cur.execute("PRAGMA table_info(dim_period)")
    period_cols = [c[1] for c in src_cur.fetchall()]
    placeholders = ",".join(["?"] * len(period_cols))
    dst_cur.executemany(f"INSERT INTO dim_period ({','.join(period_cols)}) VALUES ({placeholders})", periods)

    # For dim_statement_schedule: transfer schedule definitions
    print("Transferring dim_statement_schedule...")
    src_cur.execute("SELECT * FROM dim_statement_schedule")
    schedules = src_cur.fetchall()
    src_cur.execute("PRAGMA table_info(dim_statement_schedule)")
    sched_cols = [c[1] for c in src_cur.fetchall()]
    placeholders = ",".join(["?"] * len(sched_cols))
    dst_cur.executemany(f"INSERT INTO dim_statement_schedule ({','.join(sched_cols)}) VALUES ({placeholders})", schedules)

    # Transfer fact tables for ACKO
    facts = [
        "fact_company_quarterly_metrics",
        "fact_geographical_distribution",
        "fact_persistency_cohorts",
        "fact_intermediary_channel_metrics"
    ]

    for fact in facts:
        src_cur.execute(f"SELECT * FROM {fact} WHERE company_id = 'ACKO_LIFE'")
        rows = src_cur.fetchall()
        src_cur.execute(f"PRAGMA table_info({fact})")
        cols = [c[1] for c in src_cur.fetchall()]
        placeholders = ",".join(["?"] * len(cols))
        dst_cur.executemany(f"INSERT INTO {fact} ({','.join(cols)}) VALUES ({placeholders})", rows)
        print(f"Transferring {fact}: {len(rows)} rows copied.")

    # 3. Create Convenience Views for Instant Reporting
    dst_cur.execute("""
        CREATE VIEW IF NOT EXISTS v_acko_quarterly_summary AS
        SELECT 
            m.period_id,
            p.financial_year,
            p.quarter,
            m.gross_written_premium AS gwp_lakhs,
            m.financial_year_premium AS fy_prem_lakhs,
            m.total_single_premium AS single_prem_lakhs,
            m.renewal_premium AS renewal_lakhs,
            m.total_individual_premium AS ind_prem_lakhs,
            m.total_group_premium AS grp_prem_lakhs,
            m.total_policies,
            m.group_lives_covered,
            m.total_sum_assured AS sum_assured_lakhs,
            m.avg_ticket_size_inr,
            m.comm_expense AS comm_lakhs,
            m.opex_expense AS opex_lakhs,
            m.total_expense AS total_exp_lakhs,
            m.solvency_ratio,
            m.profit_after_tax AS pat_lakhs,
            m.net_worth AS net_worth_lakhs,
            m.avg_premium_growth_pct AS prem_grw_pct,
            m.policy_sales_growth_pct AS pol_grw_pct,
            m.total_complaints,
            m.number_offices_branches,
            m.company_website_link
        FROM fact_company_quarterly_metrics m
        JOIN dim_period p ON m.period_id = p.period_id
        ORDER BY p.chronological_sequence;
    """)

    dst_cur.execute("""
        CREATE VIEW IF NOT EXISTS v_acko_persistency_summary AS
        SELECT 
            period_id,
            cohort_month,
            premium_basis_type,
            basis_metric,
            persistency_ratio_pct
        FROM fact_persistency_cohorts
        ORDER BY period_id, cohort_month;
    """)

    dst_cur.execute("""
        CREATE VIEW IF NOT EXISTS v_acko_geo_summary AS
        SELECT 
            period_id,
            region_type,
            region_name,
            total_policies,
            total_premium_lakhs,
            total_sum_assured_lakhs
        FROM fact_geographical_distribution
        WHERE region_name NOT IN ('TOTAL', 'GRAND TOTAL')
        ORDER BY period_id, total_premium_lakhs DESC;
    """)

    dst_conn.commit()

    # 4. Verification
    print("\n--- Summary of New Database: life_insurance_curated_v2.db ---")
    dst_cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
    objects = dst_cur.fetchall()
    for name, obj_type in objects:
        if obj_type == 'table' and not name.startswith("sqlite_"):
            dst_cur.execute(f"SELECT COUNT(*) FROM {name}")
            cnt = dst_cur.fetchone()[0]
            print(f"  [Table] {name:<35}: {cnt} rows")
        elif obj_type == 'view':
            print(f"  [View]  {name}")

    file_size_kb = os.path.getsize(DST_DB) / 1024
    print(f"\nDatabase successfully created at: {os.path.abspath(DST_DB)}")
    print(f"Total file size: {file_size_kb:.2f} KB (clean, lightweight, ultra-compact)")

    src_conn.close()
    dst_conn.close()

if __name__ == "__main__":
    main()
