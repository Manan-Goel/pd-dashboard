# Power BI & Dashboard Integration Guide: Life Insurance Financial Analytics

## 1. Overview
The database `life_insurance.db` is an enterprise-grade, normalized relational data warehouse containing standardized financial disclosures across all 25 Indian life insurance companies.

All metrics are normalized to **INR Lakhs** (or standard decimals for ratios like Solvency Ratio), ensuring that multi-company cross-comparisons and multi-year time series are accurate and consistent.

---

## 2. Zero Double-Counting Guarantee
To ensure dashboards (e.g. Power BI, Tableau, Metabase, or custom web apps) never inflate revenue or balance sheet figures, analytical queries should read from the dedicated reporting views:

- **`vw_dashboard_financials`**: Filters strictly to additive leaf-level financial lines (`is_leaf = 1`), completely isolating summary parent totals and orthogonal geographic slices.
- **`vw_unified_insurance_revenue`**: Bridges statutory cash-basis Gross Direct Premium with Ind AS 117 accrual Insurance Revenue.
- **`fact_financial_statement`**: Contains the complete natural business grain for granular reporting, including summary totals when queried with `WHERE is_total = 1`.

---

## 3. Power BI Connection Instructions

### Option A: Direct SQLite ODBC Driver (Recommended for Local Dashboards)
1. Install the SQLite ODBC Driver (e.g. from [ch-werner.de](http://www.ch-werner.de/sqliteodbc/) or standard Windows 64-bit SQLite ODBC driver).
2. In Power BI Desktop:
   - Click **Get Data** -> **ODBC**.
   - Connection String: `Driver={SQLite3 ODBC Driver};Database=c:\Users\amitg\Downloads\Life Insurance\life_insurance.db;`
   - Select the views: `vw_dashboard_financials` and `dim_period`.

### Option B: Python Script Data Source (Zero Setup)
Power BI includes a built-in Python connector that requires no driver installation:
1. In Power BI Desktop, click **Get Data** -> **More...** -> **Python script**.
2. Paste the following script:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect(r"c:\Users\amitg\Downloads\Life Insurance\life_insurance.db")

# Load Additive Analytical Facts
df_dashboard = pd.read_sql_query("SELECT * FROM vw_dashboard_financials", conn)

# Load Dimension Slicers
df_companies = pd.read_sql_query("SELECT * FROM dim_company", conn)
df_periods = pd.read_sql_query("SELECT * FROM dim_period ORDER BY chronological_sequence", conn)
df_schedules = pd.read_sql_query("SELECT * FROM dim_statement_schedule", conn)

conn.close()
```
3. Click **OK** and load the tables into the Power BI Data Model.

---

## 4. Configuring Dashboard Filters & Slicers

Connect the tables in the Power BI Model View:
- `dim_company[company_id]` (1) -> `vw_dashboard_financials[company_id]` (*)
- `dim_period[period_id]` (1) -> `vw_dashboard_financials[period_id]` (*)
- `dim_statement_schedule[schedule_code]` (1) -> `vw_dashboard_financials[schedule_code]` (*)

### Slicers to Place on Dashboard:
1. **Insurer Filter**: `dim_company[short_name]` (Multi-select dropdown, e.g. "HDFC Life", "SBI Life", "LIC").
2. **Financial Year Filter**: `dim_period[financial_year]` (e.g. "FY2021-22", "FY2022-23", "FY2023-24").
3. **Quarter Filter**: `dim_period[quarter]` (e.g. "Q1", "Q2", "Q3", "Q4").
4. **Schedule / Statement**: `dim_statement_schedule[schedule_name]` (e.g. "Premium Schedule L-4", "Revenue Account L-1", "Solvency Margin L-32").
5. **Metric Aggregation**: Toggle between `quarter_amount_lakhs` (discrete quarter) and `ytd_amount_lakhs` (cumulative year-to-date).

---

## 5. Routine Operations & Upcoming Quarter Ingestion

When a new quarter's filing arrives (or an updated Excel workbook is published):
1. Place the new or updated Excel file in the project folder.
2. Run single-file ingestion:
```powershell
python main.py --ingest-file <path_to_excel_file>
```
3. Or re-run the complete batch orchestrator across all 25 insurers:
```powershell
python main.py --ingest-all
```
4. Check real-time database record counts and quarantine status:
```powershell
python main.py --status
```
5. View market share and solvency rankings instantly:
```powershell
python main.py --top-premiums FY2023-24_Q4
python main.py --solvency-ranking FY2023-24_Q4
```
