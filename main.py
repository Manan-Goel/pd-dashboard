"""
Command-Line Interface (CLI) for Life Insurance Data Warehouse Pipeline.
Usage:
    python main.py --init-db
    python main.py --ingest-all
    python main.py --ingest-file <path_to_excel>
    python main.py --status
    python main.py --top-premiums [period_id]
"""

import sys
import argparse
from src.pipeline.orchestrator import PipelineOrchestrator
from src.db.database import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description="Life Insurance Data Warehouse & ETL CLI")
    parser.add_argument("--init-db", action="store_true", help="Initialize schema and seed master dimensions")
    parser.add_argument("--ingest-all", action="store_true", help="Ingest all 25 consolidated company Excel workbooks")
    parser.add_argument("--ingest-file", type=str, default="", help="Ingest an individual Excel filing")
    parser.add_argument("--status", action="store_true", help="Show database table record counts and data quality status")
    parser.add_argument("--top-premiums", type=str, nargs="?", const="FY2024-25_Q4", default=None, help="Show top insurers by Total Premium for a given period")
    parser.add_argument("--solvency-ranking", type=str, nargs="?", const="FY2024-25_Q4", default=None, help="Show insurer solvency ratio rankings for a given period")
    parser.add_argument("--db-path", type=str, default="life_insurance.db", help="Path to SQLite database file")
    parser.add_argument("--engine", type=str, default="sqlite", help="Target database engine: 'sqlite' or 'duckdb'")

    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(db_path=args.db_path, engine=args.engine)

    if args.init_db:
        orchestrator.initialize(force=True)
        print("Database schema and master dimensions initialized successfully.")
        return

    if args.ingest_all:
        orchestrator.initialize(force=False)
        orchestrator.run_all()
        return

    if args.ingest_file:
        orchestrator.initialize(force=False)
        res = orchestrator.ingestor.ingest_file(args.ingest_file)
        print(f"Ingested {args.ingest_file}: {res}")
        return

    if args.status:
        db = DatabaseManager(db_path=args.db_path, engine=args.engine)
        print(f"\n=== DATABASE STATUS ({args.db_path}) ===")
        tables = [
            "dim_company", "dim_period", "dim_statement_schedule", "dim_line_item",
            "audit_etl_batches", "stage_tabular_blocks", "fact_financial_statement",
            "fact_cell_lineage", "quarantine_unmapped_taxonomy", "quarantine_reconciliation_discrepancies"
        ]
        for tbl in tables:
            try:
                cnt = db.execute(f"SELECT COUNT(*) as c FROM {tbl}").fetchone()["c"]
                print(f"  {tbl:<45}: {cnt:8,d} records")
            except Exception as e:
                print(f"  {tbl:<45}: Table not found or error ({e})")
        return

    if args.top_premiums:
        period_id = args.top_premiums
        db = DatabaseManager(db_path=args.db_path, engine=args.engine)
        print(f"\n=== TOP INSURERS BY GROSS PREMIUM ({period_id}) ===")
        rows = db.execute("""
            SELECT 
                c.short_name as company,
                f.quarter_amount_lakhs as quarter_lakhs,
                f.ytd_amount_lakhs as ytd_lakhs,
                f.source_unit_id as unit
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            WHERE f.period_id = ? AND f.schedule_code = 'L-4' AND f.line_item_id = 'L4_PREM_TOTAL'
              AND f.segment_id = 'TOTAL' AND f.is_active = 1
            ORDER BY f.quarter_amount_lakhs DESC
        """, (period_id,)).fetchall()
        print(f"{'Company':<32} | {'Quarter (INR Lakhs)':<22} | {'YTD (INR Lakhs)':<22}")
        print("-" * 80)
        for r in rows:
            q_val = f"{r['quarter_lakhs']:,.2f}" if r['quarter_lakhs'] is not None else "N/A"
            y_val = f"{r['ytd_lakhs']:,.2f}" if r['ytd_lakhs'] is not None else "N/A"
            print(f"{r['company']:<32} | {q_val:<22} | {y_val:<22}")
        return

    if args.solvency_ranking:
        period_id = args.solvency_ranking
        db = DatabaseManager(db_path=args.db_path, engine=args.engine)
        print(f"\n=== SOLVENCY RATIO RANKINGS ({period_id}) ===")
        rows = db.execute("""
            SELECT 
                c.short_name as company,
                f.point_in_time_amount_lakhs as solvency_ratio,
                CASE WHEN f.point_in_time_amount_lakhs >= 1.5 THEN 'COMPLIANT' ELSE 'BREACH (<1.50)' END as status
            FROM fact_financial_statement f
            JOIN dim_company c ON f.company_id = c.company_id
            WHERE f.period_id = ? AND f.schedule_code = 'L-32' AND f.line_item_id = 'L32_SOLV_RATIO'
              AND f.is_active = 1
            ORDER BY f.point_in_time_amount_lakhs DESC
        """, (period_id,)).fetchall()
        print(f"{'Company':<32} | {'Solvency Ratio':<18} | {'Regulatory Status':<20}")
        print("-" * 75)
        for r in rows:
            solv_val = f"{r['solvency_ratio']:.4f}" if r['solvency_ratio'] is not None else "N/A"
            print(f"{r['company']:<32} | {solv_val:<18} | {r['status']:<20}")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
