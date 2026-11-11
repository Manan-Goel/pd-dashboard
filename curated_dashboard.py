#!/usr/bin/env python3
"""
Curated Web Dashboard & Visual Analytics for Life Insurance Data Warehouse.
Connected exclusively to life_insurance_curated_v2.db.
Features:
- Multi-company selection: HDFC Life, LIC, Canara HSBC, ICICI Prudential, SBI Life, Acko Life
- 64 Standardized statutory and derived metrics
- Dynamic period slicer (FY2021-22 Q1 to FY2025-26 Q4)
- Metric category slicer & real-time search
- Chart.js interactive visualizations
- Multi-company industry leaderboard
- CSV Export
"""

import os
import sys
import json
import sqlite3
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "life_insurance_curated_v2.db")
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

class CuratedDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            if os.path.exists(HTML_PATH):
                with open(HTML_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = "<h1>Dashboard index.html not found</h1>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        elif url.path in ("/api/all-data", "/api/all-data.json"):
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT * FROM v_all_64_metrics ORDER BY company_id, period_id")
            metrics = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT company_id, period_id, region_type, region_name, total_policies, total_premium_lakhs, 
                       total_sum_assured_lakhs, rural_policies, urban_policies 
                FROM fact_geographical_distribution 
                ORDER BY company_id, period_id, total_premium_lakhs DESC
            """)
            geo = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT company_id, period_id, cohort_month, premium_basis_type, basis_metric, persistency_ratio_pct 
                FROM fact_persistency_cohorts 
                ORDER BY company_id, period_id, cohort_month
            """)
            persistency = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT company_id, period_id, channel_name, policies_count, premium_lakhs, intermediary_count, productivity_inr 
                FROM fact_intermediary_channel_metrics 
                ORDER BY company_id, period_id, premium_lakhs DESC
            """)
            channels = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT company_id, company_name, short_name, irda_reg_no, category FROM dim_company ORDER BY company_name")
            companies = [dict(r) for r in cur.fetchall()]

            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "companies": companies,
                "metrics": metrics,
                "geo": geo,
                "persistency": persistency,
                "channels": channels
            }).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    parser = argparse.ArgumentParser(description="Start Curated Multi-Company Web Dashboard")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind (default: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found!")
        sys.exit(1)

    server = HTTPServer(("localhost", args.port), CuratedDashboardHandler)
    url = f"http://localhost:{args.port}"
    print("=" * 75)
    print("🚀 LIFE INSURANCE CURATED MULTI-COMPANY EXECUTIVE DASHBOARD ACTIVE")
    print(f"   URL: {url}")
    print(f"   Database: {os.path.abspath(DB_PATH)}")
    print("=" * 75)

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
        server.server_close()

if __name__ == "__main__":
    main()
