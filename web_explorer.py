#!/usr/bin/env python3
"""
Lightweight Local Web Dashboard & SQL Explorer for Life Insurance Data Warehouse.
Zero external dependencies (uses Python built-in http.server + sqlite3).

Usage:
  python web_explorer.py           # Starts server on http://localhost:8501 and opens browser
  python web_explorer.py --port 8080
"""

import os
import sys
import json
import sqlite3
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "life_insurance.db")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Life Insurance Data Warehouse Explorer</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    body { background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; }
    .navbar { background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); }
    .card { border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .badge-pill { font-size: 0.8rem; padding: 0.35em 0.65em; border-radius: 50rem; }
    pre { background: #0f172a; color: #f8fafc; padding: 12px; border-radius: 6px; font-size: 0.88rem; }
    .table-container { 
      max-height: 560px; 
      overflow-x: auto !important; 
      overflow-y: auto !important; 
      white-space: nowrap !important;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
    }
    .table th { 
      position: sticky; 
      top: 0; 
      background: #0f172a; 
      color: #38bdf8; 
      z-index: 2; 
      font-size: 0.78rem; 
      padding: 8px 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .table td { 
      font-size: 0.82rem; 
      padding: 6px 12px; 
      vertical-align: middle;
    }
    .preset-btn { margin-bottom: 5px; text-align: left; font-size: 0.82rem; }
  </style>
</head>
<body>
  <nav class="navbar navbar-dark py-2 px-3 shadow-sm">
    <div class="container-fluid">
      <span class="navbar-brand mb-0 h1 fw-bold">🏛️ Life Insurance Data Warehouse (IRDAI Disclosures)</span>
      <span class="badge bg-success">Active DB: Curated V2 Warehouse (64 Metrics)</span>
    </div>
  </nav>

  <div class="container-fluid py-4 px-4">
    <div class="row">
      <!-- Left Column: Quick Presets & Filters -->
      <div class="col-md-3">
        <div class="card mb-3">
          <div class="card-header bg-white fw-bold">⚡ Curated Metric Views</div>
          <div class="card-body p-2 d-grid gap-1">
            <button class="btn btn-success btn-sm preset-btn fw-bold" onclick="runPreset('all-64')">💎 ALL 64 Metrics (Complete View)</button>
            <button class="btn btn-outline-primary btn-sm preset-btn" onclick="runPreset('premiums')">📊 Premiums & Growth (M01-M15)</button>
            <button class="btn btn-outline-primary btn-sm preset-btn" onclick="runPreset('claims-expenses')">🩺 Claims & Expenses (M16-M22)</button>
            <button class="btn btn-outline-primary btn-sm preset-btn" onclick="runPreset('solvency-pnl')">🛡️ Solvency, P&L & Net Worth (M31-M38, M55-M58)</button>
            <button class="btn btn-outline-primary btn-sm preset-btn" onclick="runPreset('channels-acko')">🏢 Channels & Productivity (M42, M46-M54)</button>
            <button class="btn btn-outline-info btn-sm preset-btn" onclick="runPreset('geo-acko')">🗺️ Geographical Distribution (Field 43)</button>
            <button class="btn btn-outline-warning btn-sm preset-btn" onclick="runPreset('persistency-acko')">📈 Persistency Cohorts (Field 41)</button>
          </div>
        </div>

        <div class="card">
          <div class="card-header bg-white fw-bold">🔍 Slicer</div>
          <div class="card-body">
            <div class="mb-2">
              <label class="form-label small fw-bold">Company:</label>
              <select id="filterCompany" class="form-select form-select-sm"></select>
            </div>
            <div class="mb-2">
              <label class="form-label small fw-bold">Period (Quarter):</label>
              <select id="filterPeriod" class="form-select form-select-sm"></select>
            </div>
            <button class="btn btn-primary btn-sm w-100 mt-2" onclick="fetchSlice()">Filter Slice</button>
          </div>
        </div>
      </div>

      <!-- Right Column: Query Editor & Data View -->
      <div class="col-md-9">
        <div class="card mb-3">
          <div class="card-header bg-white d-flex justify-content-between align-items-center">
            <span class="fw-bold">💻 Interactive SQL Console</span>
            <div>
              <button class="btn btn-outline-secondary btn-sm me-2" onclick="exportCSV()">📥 Export CSV</button>
              <button class="btn btn-success btn-sm px-3 fw-bold" onclick="runCustomQuery()">▶ Run SQL</button>
            </div>
          </div>
          <div class="card-body p-2">
            <textarea id="sqlInput" class="form-control font-monospace" rows="4" style="background:#0f172a; color:#38bdf8; font-size:0.92rem;">SELECT * FROM v_all_64_metrics WHERE company_id = 'ACKO_LIFE' ORDER BY period_id;</textarea>
          </div>
        </div>

        <div class="card">
          <div class="card-header bg-white d-flex justify-content-between align-items-center">
            <span class="fw-bold" id="resultTitle">Query Results</span>
            <span class="badge bg-secondary" id="rowCount">0 rows</span>
          </div>
          <div class="card-body p-0 table-container">
            <div id="loading" class="text-center py-5 d-none">
              <div class="spinner-border text-primary" role="status"></div>
              <div class="text-muted small mt-2">Executing query...</div>
            </div>
            <table class="table table-sm table-striped table-hover mb-0" id="resultTable">
              <thead class="table-dark sticky-top" id="resultHead"></thead>
              <tbody id="resultBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentData = [];

    async function loadMetadata() {
      const res = await fetch('/api/meta');
      const data = await res.json();
      
      const compSel = document.getElementById('filterCompany');
      compSel.innerHTML = '';
      data.companies.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        compSel.appendChild(opt);
      });
      if (data.companies.length > 0) compSel.value = data.companies[0].id;

      const perSel = document.getElementById('filterPeriod');
      perSel.innerHTML = '';
      data.periods.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.id;
        perSel.appendChild(opt);
      });
      if (data.periods.length > 0) perSel.value = data.periods[data.periods.length - 1].id;

      runPreset('all-64');
    }

    async function executeSQL(sql, title) {
      document.getElementById('loading').classList.remove('d-none');
      document.getElementById('resultTable').classList.add('d-none');
      document.getElementById('resultTitle').textContent = title || "Query Result";

      try {
        const res = await fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sql })
        });
        const result = await res.json();
        
        if (result.error) {
          alert('SQL Error: ' + result.error);
          return;
        }

        currentData = result.rows;
        renderTable(result.columns, result.rows);
      } catch (err) {
        alert('Fetch Error: ' + err);
      } finally {
        document.getElementById('loading').classList.add('d-none');
        document.getElementById('resultTable').classList.remove('d-none');
      }
    }

    function renderTable(columns, rows) {
      const head = document.getElementById('resultHead');
      const body = document.getElementById('resultBody');
      head.innerHTML = '';
      body.innerHTML = '';

      document.getElementById('rowCount').textContent = `${rows.length} rows returned`;

      if (columns.length === 0) return;

      const trHead = document.createElement('tr');
      columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        trHead.appendChild(th);
      });
      head.appendChild(trHead);

      rows.forEach(r => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
          const td = document.createElement('td');
          const val = r[col];
          if (typeof val === 'number') {
            td.textContent = val.toLocaleString(undefined, { maximumFractionDigits: 4 });
            td.style.textAlign = 'right';
          } else {
            td.textContent = val !== null ? val : '-';
          }
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }

    function runCustomQuery() {
      const sql = document.getElementById('sqlInput').value.trim();
      executeSQL(sql, "Custom SQL Execution");
    }

    function fetchSlice() {
      const comp = document.getElementById('filterCompany').value;
      const per = document.getElementById('filterPeriod').value;

      const sql = `SELECT 
    period_id, 
    gross_written_premium AS gwp_lakhs, 
    financial_year_premium AS fy_prem_lakhs, 
    total_single_premium AS single_prem_lakhs, 
    renewal_premium AS renewal_lakhs,
    total_policies, 
    group_lives_covered, 
    total_sum_assured AS sum_assured_lakhs, 
    solvency_ratio, 
    profit_after_tax AS pat_lakhs, 
    net_worth AS net_worth_lakhs, 
    total_complaints
FROM fact_company_quarterly_metrics
WHERE company_id = '${comp}' AND period_id = '${per}';`;

      document.getElementById('sqlInput').value = sql;
      executeSQL(sql, `${comp} - ${per}`);
    }

    function runPreset(name) {
      let sql = "";
      let title = "";
      if (name === 'all-64') {
        title = "Acko Life Insurance - Standardized 64 Metrics (Complete View, Sequential M01-M64)";
        sql = `SELECT * FROM v_all_64_metrics WHERE company_id = 'ACKO_LIFE' ORDER BY period_id;`;
      } else if (name === 'premiums') {
        title = "Acko Life Insurance - Premiums & Policy Growth Metrics (M01-M15, M24, M27)";
        sql = `SELECT 
    period_id, 
    m01_fy_premium, 
    m02_total_single_premium, 
    m03_renewal_premium, 
    m04_total_individual_premium, 
    m05_total_group_premium, 
    m07_total_non_single_premium, 
    m08_group_non_single_premium, 
    m09_group_yearly_renewal_premium, 
    m10_individual_single_premium, 
    m11_individual_non_single_premium, 
    m12_group_single_premium, 
    m13_gross_written_premium, 
    m14_avg_premium_growth_pct, 
    m15_policy_sales_growth_pct, 
    m24_total_premium, 
    m25_total_sum_assured, 
    m27_total_policies, 
    m28_avg_ticket_size_inr,
    m29_group_lives_covered
FROM v_all_64_metrics 
WHERE company_id = 'ACKO_LIFE' 
ORDER BY period_id;`;
      } else if (name === 'claims-expenses') {
        title = "Acko Life Insurance - Claims, Expenses & Surrenders (M16-M22, M37, M39)";
        sql = `SELECT 
    period_id, 
    m16_number_of_claims, 
    m17_death_claims, 
    m18_maturity_amount, 
    m19_total_claim_amount, 
    m20_comm_expense, 
    m21_opex_expense, 
    m22_total_expense, 
    m37_surrenders, 
    m38_conservation_ratio, 
    m39_total_complaints
FROM v_all_64_metrics 
WHERE company_id = 'ACKO_LIFE' 
ORDER BY period_id;`;
      } else if (name === 'solvency-pnl') {
        title = "Acko Life Insurance - Solvency, Profitability & Net Worth (M31-M35, M55-M58)";
        sql = `SELECT 
    period_id, 
    m31_business_profit, 
    m32a_profit_before_tax, 
    m32b_profit_after_tax, 
    m33_aum_cagr, 
    m34a_linked_aum, 
    m34b_non_linked_aum, 
    m35_solvency_ratio, 
    m55a_share_capital, 
    m55b_share_premium, 
    m56_profit_loss_carried_forward, 
    m57_net_worth, 
    m58_roe_pct
FROM v_all_64_metrics 
WHERE company_id = 'ACKO_LIFE' 
ORDER BY period_id;`;
      } else if (name === 'channels-acko') {
        title = "Acko Life Insurance - Intermediary Distribution Channels & Productivity (M42, M46-M54)";
        sql = `SELECT 
    period_id, 
    m42a_channel_agency_prem, 
    m42b_channel_banca_prem, 
    m42c_channel_broker_prem, 
    m42d_channel_direct_prem, 
    m42e_channel_web_agg_prem, 
    m46_number_banca_partners, 
    m47_number_banca_branches, 
    m48_bank_productivity_inr, 
    m49_number_offices_branches, 
    m50_number_web_aggregators, 
    m51_number_individual_agents, 
    m52_agent_productivity_inr, 
    m53_number_brokers, 
    m54_broker_productivity_inr
FROM v_all_64_metrics 
WHERE company_id = 'ACKO_LIFE' 
ORDER BY period_id;`;
      } else if (name === 'geo-acko') {
        title = "Acko Life Insurance - Geographical Distribution (Field 43 Table)";
        sql = `SELECT 
    period_id,
    region_type,
    region_name,
    total_policies,
    total_premium_lakhs,
    total_sum_assured_lakhs
FROM fact_geographical_distribution
WHERE company_id = 'ACKO_LIFE'
ORDER BY period_id, total_premium_lakhs DESC;`;
      } else if (name === 'persistency-acko') {
        title = "Acko Life Insurance - Persistency Cohorts (Field 41 Table)";
        sql = `SELECT 
    period_id,
    cohort_month,
    premium_basis_type,
    basis_metric,
    persistency_ratio_pct
FROM fact_persistency_cohorts
WHERE company_id = 'ACKO_LIFE'
ORDER BY period_id, cohort_month;`;
      }

      document.getElementById('sqlInput').value = sql;
      executeSQL(sql, title);
    }

    function exportCSV() {
      if (!currentData || currentData.length === 0) {
        alert("No data available to export.");
        return;
      }
      const keys = Object.keys(currentData[0]);
      let csv = keys.join(",") + "\\n";
      currentData.forEach(row => {
        csv += keys.map(k => {
          let val = row[k];
          if (val === null) val = "";
          return '"' + String(val).replace(/"/g, '""') + '"';
        }).join(",") + "\\n";
      });

      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = "insurance_data_export.csv";
      a.click();
    }

    window.onload = loadMetadata;
  </script>
</body>
</html>
"""

class WarehouseRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif url.path == "/api/meta":
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            companies = [{"id": r[0], "name": r[1]} for r in cur.execute("SELECT company_id, short_name FROM dim_company ORDER BY short_name").fetchall()]
            periods = [{"id": r[0]} for r in cur.execute("SELECT period_id FROM dim_period ORDER BY chronological_sequence").fetchall()]
            try:
                schedules = [{"code": r[0], "name": r[1]} for r in cur.execute("SELECT schedule_code, schedule_name FROM dim_statement_schedule ORDER BY schedule_code").fetchall()]
            except Exception:
                schedules = []
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"companies": companies, "periods": periods, "schedules": schedules}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/api/query":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            sql = data.get("sql", "").strip()

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            try:
                cur.execute(sql)
                cols = [desc[0] for desc in cur.description] if cur.description else []
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"columns": cols, "rows": rows}).encode("utf-8"))
            except Exception as e:
                conn.close()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    global DB_PATH
    parser = argparse.ArgumentParser(description="Start Web Dashboard Explorer")
    parser.add_argument("--db", default=DB_PATH, help="Path to SQLite database file (default: life_insurance.db)")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind (default: 8501)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    DB_PATH = os.path.abspath(args.db)
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        sys.exit(1)

    server = HTTPServer(("localhost", args.port), WarehouseRequestHandler)
    url = f"http://localhost:{args.port}"
    print(f"\n" + "=" * 70)
    print(f"🚀 LIFE INSURANCE DATA WAREHOUSE EXPLORER RUNNING AT:")
    print(f"   {url}")
    print(f"=" * 70)
    print("Press Ctrl+C to stop the server.\n")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.server_close()

if __name__ == "__main__":
    main()
