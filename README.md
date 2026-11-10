# 🛡️ Life Insurance Statutory Analytics & Executive Dashboard

> **Interactive 64-Metric Regulatory Intelligence Platform built on IRDAI Public Disclosures.**  
> Designed with a 3-Dimensional Unified Star Schema, empirical cell-level auditing, and real-time interactive analytics.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
![IRDAI Compliant](https://img.shields.io/badge/IRDAI-Statutory%20Public%20Disclosures-blue)
![Curated Metrics](https://img.shields.io/badge/Metrics-64%20Standardized%20KPIs-green)
![Audit Reconciliation](https://img.shields.io/badge/Audit-100%25%20Empirically%20Reconciled-success)
![Database](https://img.shields.io/badge/Database-SQLite3%20Curated%20v2-orange)

---

## 📊 Overview

This repository hosts the **Curated Executive Dashboard** and data warehouse pipeline for Indian Life Insurance statutory public disclosures (Forms L-1 to L-42). 

It currently features **Acko Life Insurance Limited** across all **12 statutory quarters** from **FY2023-24 Q1 through FY2025-26 Q4**, mapping **64 standardized root and derived metrics** along with deep actuarial breakdowns for geographical spread, persistency cohorts, and intermediary distribution channels.

### 🌟 Key Dashboard Capabilities
- **8 Executive Visual KPI Cards**: Gross Written Premium (GWP), Solvency Ratio (vs 1.50x floor), In-force Policies & Group Lives, Total Sum Assured, Gross Claims Settled, Net Worth, 13-Month Persistency Ratio, IRDAI Grievances.
- **Dynamic Slicers**:
  - **Statutory Period**: Filter across all 12 quarters or inspect any single quarter.
  - **Metric Categories**: Quick-filter across *Premiums & Income*, *Scale & Volumes*, *Claims & Benefits*, *Expenses & Ratios*, *Solvency & Capital*, and *Distribution Channels*.
- **Interactive Visualizations (Chart.js)**:
  - Gross Premium Trajectory (Regular vs Single vs Renewal).
  - Business Scale (Individual In-force Policies vs Group Lives Covered).
  - Regulatory Solvency Ratio vs 1.50x statutory requirement.
  - Geographic Heatmap / State-wise Leaderboard by premium and policies.
- **Granular Actuarial Tables**:
  - Full 64 Curated Metrics Explorer with instant search.
  - State-wise Rural vs Urban distribution (469 records).
  - 13th to 61st Month Persistency Cohorts (240 records).
  - Intermediary Channel Productivity in INR (60 records).
- **Export**: One-click full CSV export of all curated metrics.

---

## 🏛️ Architecture & Schema

The data warehouse uses a **3-Dimensional Unified Star Schema** optimized for high-speed slicing and zero garbage data:

```
                          ┌───────────────────────────┐
                          │   dim_statement_schedule  │
                          │   (Forms L-1 to L-42)     │
                          └─────────────┬─────────────┘
                                        │
┌──────────────────┐                    │                     ┌──────────────────┐
│   dim_company    │                    │                     │    dim_period    │
│  (Company Code)  ├────────────┐       │       ┌─────────────┤  (FY & Quarter)  │
└──────────────────┘            │       │       │             └──────────────────┘
                                ▼       ▼       ▼
                ┌───────────────────────────────────────────────┐
                │        fact_company_quarterly_metrics         │
                │             (All 64 Curated Metrics)          │
                └───────────────────────────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ fact_geographical_   │     │   fact_persistency_  │     │ fact_intermediary_   │
│    distribution      │     │       cohorts        │     │   channel_metrics    │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

---

## 🔬 Empirical Data Validation

The curated database was verified against raw statutory filings using an empirical cell-by-cell audit (`validate_excel_vs_db.py`):
- **88 statutory checkpoints** tested across all 12 quarters.
- **100% reconciliation rate** with zero unexplained deviations.
- Handles Form L-4 prior-period comparative columns and Form L-7 reinsurance deductions accurately.

---

## 🚀 Deployment & Running Locally

### 1. Run Locally (Zero external dependencies)
```bash
# Clone the repository
git clone https://github.com/Manan-Goel/pd-dashboard.git
cd pd-dashboard

# Start the dashboard server
python curated_dashboard.py --port 8501
```
Navigate to `http://localhost:8501` in your browser.

### 2. Deploy to Vercel
This repository is pre-configured for instant Vercel deployment with:
- `index.html` (frontend dashboard)
- `api/all-data.json` (curated statutory dataset)
- `vercel.json` (serverless routing and URL rewrites)

Simply connect your GitHub repo to [Vercel](https://vercel.com) and deploy with 1 click!

---

## 📄 License
Internal statutory analysis & business intelligence tool. Public disclosure data sourced from IRDAI regulatory filings.
