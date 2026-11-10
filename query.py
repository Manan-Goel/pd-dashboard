#!/usr/bin/env python3
"""
Interactive SQL Query Runner for Life Insurance Data Warehouse.
Allows running ad-hoc SQL queries, pre-built financial presets, and exporting to CSV.

Usage:
  python query.py                                      # Opens interactive SQL prompt
  python query.py "SELECT * FROM dim_company"          # Runs one-off SQL
  python query.py --preset top-premiums                # Runs Gross Premium Ranking
  python query.py --preset solvency                    # Runs Solvency Ranking
  python query.py --preset shareholding ADITYA_BIRLA_LIFE
  python query.py --preset pnl HDFC_LIFE
  python query.py --preset list-schedules
  python query.py --preset list-companies
"""

import sys
import os
import sqlite3
import argparse
import pandas as pd
from tabulate import tabulate

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "life_insurance.db")

PRESETS = {
    "list-companies": {
        "title": "Master Insurers in Warehouse",
        "sql": """
            SELECT company_id, short_name, irda_reg_no, category 
            FROM dim_company 
            ORDER BY short_name;
        """
    },
    "list-schedules": {
        "title": "IRDAI Statements & Schedules Available in Warehouse",
        "sql": """
            SELECT s.schedule_code, s.schedule_name, COUNT(f.fact_id) as total_facts
            FROM dim_statement_schedule s
            LEFT JOIN fact_financial_statement f ON s.schedule_code = f.schedule_code
            GROUP BY s.schedule_code, s.schedule_name
            ORDER BY total_facts DESC;
        """
    },
    "top-premiums": {
        "title": "Top 10 Insurers by Gross Premium (FY2023-24 Q4)",
        "sql": """
            SELECT 
                c.short_name AS insurer,
                p.financial_year,
                p.quarter,
                ROUND(f.quarter_amount_lakhs, 2) AS gross_premium_lakhs,
                ROUND(f.quarter_amount_lakhs / 100.0, 2) AS gross_premium_crores
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_period p ON f.period_id = p.period_id
            WHERE f.schedule_code = 'L-4'
              AND f.line_item_id = 'L4_PREM_TOTAL'
              AND p.period_id = 'FY2023-24_Q4'
            ORDER BY f.quarter_amount_lakhs DESC
            LIMIT 10;
        """
    },
    "solvency": {
        "title": "Statutory Solvency Ratios (FY2023-24 Q4 - IRDAI Min: 1.50)",
        "sql": """
            SELECT 
                c.short_name AS insurer,
                ROUND(f.point_in_time_amount_lakhs, 4) AS solvency_ratio,
                CASE WHEN f.point_in_time_amount_lakhs >= 1.50 THEN 'COMPLIANT' ELSE 'BREACH' END AS regulatory_status
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            WHERE f.schedule_code = 'L-32'
              AND f.line_item_id = 'L32_SOLV_RATIO'
              AND f.period_id = 'FY2023-24_Q4'
            ORDER BY f.point_in_time_amount_lakhs DESC;
        """
    },
    "shareholding": {
        "title": "Shareholding Breakdown (Form L-9, FY2021-22 Q1)",
        "sql": """
            SELECT 
                c.short_name AS insurer,
                p.financial_year,
                p.quarter,
                m.canonical_label AS category,
                CAST(f.quarter_amount_lakhs AS INTEGER) AS number_of_shares,
                ROUND(f.quarter_amount_lakhs * 10.0 / 100000.0, 2) AS nominal_value_inr_lakhs,
                ROUND(f.quarter_amount_lakhs * 10.0 / 10000000.0, 2) AS nominal_value_inr_crores
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_period p ON f.period_id = p.period_id
            JOIN dim_line_item m ON f.line_item_id = m.line_item_id
            WHERE f.schedule_code = 'L-9'
              AND p.period_id = 'FY2021-22_Q1'
              AND f.company_id = '{company_id}'
            ORDER BY f.quarter_amount_lakhs DESC;
        """
    },
    "pnl": {
        "title": "Profit & Loss Summary (Form L-2, FY2023-24 Q4)",
        "sql": """
            SELECT 
                c.short_name AS insurer,
                m.canonical_label AS line_item,
                ROUND(f.quarter_amount_lakhs, 2) AS quarter_amount_lakhs,
                ROUND(f.ytd_amount_lakhs, 2) AS ytd_amount_lakhs
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            JOIN dim_line_item m ON f.line_item_id = m.line_item_id
            WHERE f.schedule_code = 'L-2'
              AND f.period_id = 'FY2023-24_Q4'
              AND f.company_id = '{company_id}'
            ORDER BY f.quarter_amount_lakhs DESC;
        """
    },
    "all-64": {
        "title": "Acko Life Insurance - All 64 Standardized Metrics (Complete View, M01-M64)",
        "sql": """
            SELECT * FROM v_all_64_metrics
            WHERE company_id = 'ACKO_LIFE'
            ORDER BY period_id;
        """
    },
    "premiums-acko": {
        "title": "Acko Life Insurance - Premiums & Growth Metrics (M01-M15, M24, M27)",
        "sql": """
            SELECT 
                period_id, m01_fy_premium, m02_total_single_premium, m03_renewal_premium, 
                m04_total_individual_premium, m05_total_group_premium, m07_total_non_single_premium, 
                m08_group_non_single_premium, m09_group_yearly_renewal_premium, m10_individual_single_premium, 
                m11_individual_non_single_premium, m12_group_single_premium, m13_gross_written_premium, 
                m14_avg_premium_growth_pct, m15_policy_sales_growth_pct, m24_total_premium, 
                m25_total_sum_assured, m27_total_policies, m28_avg_ticket_size_inr, m29_group_lives_covered 
            FROM v_all_64_metrics 
            WHERE company_id = 'ACKO_LIFE' 
            ORDER BY period_id;
        """
    },
    "claims-acko": {
        "title": "Acko Life Insurance - Claims, Expenses & Surrenders (M16-M22, M37, M39)",
        "sql": """
            SELECT 
                period_id, m16_number_of_claims, m17_death_claims, m18_maturity_amount, 
                m19_total_claim_amount, m20_comm_expense, m21_opex_expense, m22_total_expense, 
                m37_surrenders, m38_conservation_ratio, m39_total_complaints 
            FROM v_all_64_metrics 
            WHERE company_id = 'ACKO_LIFE' 
            ORDER BY period_id;
        """
    },
    "solvency-acko": {
        "title": "Acko Life Insurance - Solvency, Profitability & Net Worth (M31-M35, M55-M58)",
        "sql": """
            SELECT 
                period_id, m31_business_profit, m32a_profit_before_tax, m32b_profit_after_tax, 
                m33_aum_cagr, m34a_linked_aum, m34b_non_linked_aum, m35_solvency_ratio, 
                m55a_share_capital, m55b_share_premium, m56_profit_loss_carried_forward, 
                m57_net_worth, m58_roe_pct 
            FROM v_all_64_metrics 
            WHERE company_id = 'ACKO_LIFE' 
            ORDER BY period_id;
        """
    },
    "channels-acko": {
        "title": "Acko Life Insurance - Intermediary Distribution Channels & Productivity (M42, M46-M54)",
        "sql": """
            SELECT 
                period_id, m42a_channel_agency_prem, m42b_channel_banca_prem, m42c_channel_broker_prem, 
                m42d_channel_direct_prem, m42e_channel_web_agg_prem, m46_number_banca_partners, 
                m47_number_banca_branches, m48_bank_productivity_inr, m49_number_offices_branches, 
                m50_number_web_aggregators, m51_number_individual_agents, m52_agent_productivity_inr, 
                m53_number_brokers, m54_broker_productivity_inr 
            FROM v_all_64_metrics 
            WHERE company_id = 'ACKO_LIFE' 
            ORDER BY period_id;
        """
    },
    "acko-64": {
        "title": "Acko Life Insurance - Standardized 64 Metrics (All 12 Quarters)",
        "sql": """
            SELECT 
                period_id, 
                gross_written_premium AS gwp_lakhs, 
                financial_year_premium AS fy_prem_lakhs, 
                total_single_premium AS single_prem_lakhs, 
                renewal_premium AS renewal_lakhs,
                total_policies,
                group_lives_covered,
                total_sum_assured AS sum_assured_lakhs,
                avg_ticket_size_inr,
                comm_expense AS comm_lakhs,
                opex_expense AS opex_lakhs,
                total_expense AS total_exp_lakhs,
                solvency_ratio,
                profit_after_tax AS pat_lakhs,
                net_worth AS net_worth_lakhs,
                avg_premium_growth_pct AS prem_grw_pct,
                policy_sales_growth_pct AS pol_grw_pct,
                total_complaints,
                number_offices_branches,
                company_website_link
            FROM fact_company_quarterly_metrics
            WHERE company_id = 'ACKO_LIFE'
            ORDER BY period_id;
        """
    },
    "geo-acko": {
        "title": "Acko Life Insurance - Geographical Distribution (Field 43)",
        "sql": """
            SELECT 
                period_id,
                region_type,
                region_name,
                total_policies,
                total_premium_lakhs,
                total_sum_assured_lakhs
            FROM fact_geographical_distribution
            WHERE company_id = 'ACKO_LIFE' AND (total_policies > 0 OR total_premium_lakhs > 0)
            ORDER BY period_id, total_premium_lakhs DESC;
        """
    },
    "persistency-acko": {
        "title": "Acko Life Insurance - Persistency Cohorts (Field 41)",
        "sql": """
            SELECT 
                period_id,
                cohort_month,
                premium_basis_type,
                basis_metric,
                persistency_ratio_pct
            FROM fact_persistency_cohorts
            WHERE company_id = 'ACKO_LIFE'
            ORDER BY period_id, cohort_month;
        """
    }
}

def execute_query(conn, sql: str, title: str = ""):
    """Executes SQL and prints a formatted table using tabulate."""
    if title:
        print(f"\n=== {title} ===")
    try:
        df = pd.read_sql_query(sql, conn)
        if df.empty:
            print("[No records found]")
        else:
            print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))
            print(f"({len(df)} rows returned)")
    except Exception as e:
        print(f"SQL Error: {e}", file=sys.stderr)

def interactive_mode(conn):
    """Interactive SQL CLI loop."""
    print("=" * 80)
    print(" LIFE INSURANCE DATA WAREHOUSE - INTERACTIVE SQL SHELL")
    print(" Type any SQL query (e.g. 'SELECT * FROM dim_company LIMIT 5;')")
    print(" Type 'presets' to see built-in queries, or 'exit' / 'quit' to exit.")
    print("=" * 80)

    buffer = []
    while True:
        prompt = "SQL> " if not buffer else " ...> "
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            print("Goodbye.")
            break
        if line.lower() == "presets":
            print("\nAvailable Presets (run with: python query.py --preset <name>):")
            for k, v in PRESETS.items():
                print(f"  - {k:<16}: {v['title']}")
            print()
            continue

        buffer.append(line)
        if line.endswith(";"):
            sql = " ".join(buffer)
            execute_query(conn, sql)
            buffer = []

def main():
    parser = argparse.ArgumentParser(description="Query Life Insurance Data Warehouse")
    parser.add_argument("query", nargs="?", help="Direct SQL query to execute")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database file (default: life_insurance.db)")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Run a built-in analytical preset")
    parser.add_argument("--company", default="ADITYA_BIRLA_LIFE", help="Company ID for presets (default: ADITYA_BIRLA_LIFE)")
    parser.add_argument("--export-csv", help="Export result of query to CSV file path")

    args = parser.parse_args()

    db_path = args.db
    if not os.path.exists(db_path):
        print(f"Error: Database not found at '{db_path}'.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)

    if args.preset:
        preset_info = PRESETS[args.preset]
        sql = preset_info["sql"].format(company_id=args.company)
        execute_query(conn, sql, preset_info["title"])
        if args.export_csv:
            df = pd.read_sql_query(sql, conn)
            df.to_csv(args.export_csv, index=False)
            print(f"[Exported to {args.export_csv}]")
    elif args.query:
        execute_query(conn, args.query, "Custom Query Result")
        if args.export_csv:
            df = pd.read_sql_query(args.query, conn)
            df.to_csv(args.export_csv, index=False)
            print(f"[Exported to {args.export_csv}]")
    else:
        interactive_mode(conn)

    conn.close()

if __name__ == "__main__":
    main()
