# Project: Life Insurance Database Design & ETL Architecture (v3.0 Production Hardened)

## Architecture
- **Staging & Ingestion Layer**: 
  - 2D Spatial Table Bounding Box (`SpatialTableBlock`) extractor for horizontal multi-quarter concatenation and vertical statement stacking.
  - Streaming openpyxl reader (`read_only=True`, `data_only=True`).
  - Column-group/quarter-block scoped unit normalizer (handling Thousands, Lakhs, Crores, Counts, Ratios, and bilingual Hindi strings).
  - 5-Tier Non-Data Tabular Filtering (stripping footnote tokens while preserving numerical floats, routing pure narrative/disclaimer blocks to `dim_notes`).
  - Tri-engine PDF extraction pipeline (`pdfplumber` vector, `Camelot` lattice/stream, PaddleOCR/Tesseract fallback) with multi-page stitching.
- **Relational Storage & Schema Layer**:
  - Strict 3NF entity & master dimensions: `dim_company`, `dim_period`, `dim_filing_period`, `dim_accounting_standard`, `dim_segment`, `dim_schedule`, `dim_line_item`, `dim_metric_alias` (bilingual English + Hindi), `map_line_item_schedule_ref`.
  - Star-schema facts: `fact_financial_statement` with pure natural business grain `(company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id)`.
  - Explicit hierarchy and double-counting prevention: `classification_axis` (`BY_PRODUCT_TYPE`, `BY_GEOGRAPHY`, `SUMMARY_TOTAL`), `hierarchy_level`, `parent_line_id`, `is_leaf`, `is_subtotal`, `is_total`.
  - Disjoint analytical views (`vw_financial_metrics_primary`, `vw_financial_metrics_geographic`, `vw_dashboard_financials`) guaranteeing zero double-counting.
  - Precision: `NUMERIC(18, 4)` for all currency values, engine-agnostic ANSI SQL DDL compatible with SQLite, DuckDB, and PostgreSQL.
  - Full cell-level audit lineage: `fact_cell_lineage` tracking `source_file`, `sheet_name`, `row_idx`, `col_idx`, `cell_address`, `batch_id`, `extraction_timestamp`, `checksum`.
  - Zero-loss non-destructive upsert logic: SCD Type 2 / Versioned Immutable Ledger with `statement_version_id`, `is_active`, and superseding batch ID.
- **Financial Reconciliation & Audit Engine**:
  - Multi-form cross-statement mathematical assertions:
    * L-1 Gross Premium == L-4 Total Premium
    * L-1 Net Premium == L-4 Total Premium - Reinsurance Ceded + Reinsurance Accepted
    * L-1 Commission == L-5 Total Commission
    * L-1 Operating Expenses == L-6 Total OpEx
    * L-1 Benefits Paid == L-7 Total Benefits Paid
    * L-3 Balance Sheet: Total Sources of Funds == Total Application of Funds ($\Delta = 0.0$)
    * L-3 Balance Sheet Investments == L-12 (Shareholders) + L-13 (Policyholders) + L-14 (Linked)
    * Fund Cross-Flow: L-1 Surplus Transfer to Shareholders == L-2 Transfer from Policyholders; L-2 Contribution to Policyholders == L-1 Contribution from Shareholders
    * Solvency Margin: L-32 Solvency Ratio == ASM / RSM
  - Dual-condition tolerance rules ($T_{\text{abs}}$ and $T_{\text{rel}}$) by statement scale.
  - Tri-tier quarantine engine: `quarantine_syntax_cells`, `quarantine_unmapped_taxonomy`, and `quarantine_reconciliation_discrepancies` with severity levels (`INFO`, `WARNING`, `BLOCKING`).
- **Ind AS 117 Bridge Architecture**:
  - Dual-model schema support: Legacy statutory cash-basis vs Ind AS 117 accrual-basis (Insurance Revenue, CSM Rollforward, Risk Adjustment, PVFCF) via `dim_accounting_standard` and `fact_csm_rollforward`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Multi-Perspective Adversarial Architectural Review | Exhaustive review of plan v2.0 across Data Eng, Actuarial Audit, and Regulatory domains with explicit Defect & Con Log paired with mitigations | M1 | Survey & R1 |
| 2 | Relational Schema Normalization & 3NF Dimensions | Elimination of multi-valued attributes, normalized dimension tables, bilingual alias mapping | M2 | Survey & R2 |
| 3 | Star Schema Fact & Hierarchy Double-Counting Prevention | Pure business grain, `classification_axis`, `hierarchy_level`, `is_leaf` flags, and disjoint aggregation views | M2 | Survey & R2 |
| 4 | Engine-Agnostic ANSI SQL DDL Specification | Portable DDL with `NUMERIC(18, 4)` and constraints compatible across SQLite, DuckDB, and PostgreSQL | M2 | Survey & R2 |
| 5 | Full Cell-Level Audit Lineage & Versioned Ledger Upserts | `fact_cell_lineage`, SCD Type 2 versioning, non-destructive upsert logic | M2 | Survey & R2 |
| 6 | Cross-Statement Financial Reconciliation Framework | Explicit mathematical assertions covering L-1 to L-4, Balance Sheet balancing, fund transfers, and supporting schedules | M3 | Survey & R3 |
| 7 | Column-Group Scoped Unit Normalization Engine | Dynamic unit detection per quarter block with negative-lookahead regex and non-currency protection | M3 | Survey & R3 |
| 8 | Configurable Tolerance & Tri-Tier Quarantine Engine | Dual tolerance ($T_{\text{abs}}, T_{\text{rel}}$) and quarantine tables with severity routing (`INFO`, `WARNING`, `BLOCKING`) | M3 | Survey & R3 |
| 9 | 2D Bounding Box Ingestion & Dynamic Header Anchoring | Handling horizontal multi-quarter concatenation and vertical statement stacking with 2D spatial slicing | M4 | Survey & R4 |
| 10 | Zero-Text Tabular Filtering Rules | 5-tier filtering stripping footnote tokens without dropping numeric rows, routing narrative blocks to notes table | M4 | Survey & R4 |
| 11 | Multi-Engine Tabular PDF Extraction Strategy | Tri-engine orchestration (`pdfplumber` vector + `Camelot` + OCR fallback) with multi-page table stitching | M4 | Survey & R4 |
| 12 | Ind AS 117 (IFRS 17) Taxonomy Transition Architecture | Schema bridging legacy IRDAI to Ind AS 117 Insurance Revenue and CSM rollforward without redesign | M4 | Survey & R4 |
| 13 | Master Hardened Production Architecture Plan Synthesis | Unified, production-grade deliverable document incorporating all specifications, diagrams, formulas, and DDL | M5 | Synthesis & All Requirements |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Multi-Perspective Adversarial Review & Defect Log | Enumerate all 10+ architectural risks, vulnerabilities, and parsing flaws across all 25 workbooks with concrete mitigations | Survey | DONE |
| M2 | Hardened Schema, Normalization & DDL Specification | 3NF dimensions, star-schema fact, ANSI SQL DDL across SQLite/DuckDB/Postgres, lineage, zero-loss upserts | Survey, M1 | DONE |
| M3 | Automated Cross-Statement Financial Reconciliation & Quarantine | Complete mathematical assertions, SQL validation rules, column-group unit scaling, and tri-tier quarantine engine | Survey, M1, M2 | DONE |
| M4 | Resilient Quarterly Ingestion, PDF & Ind AS 117 Strategy | 2D spatial bounding boxes, zero-text filtering rules, tri-engine PDF pipeline, Ind AS 117 schema bridge | Survey, M1, M2 | DONE |
| M5 | Master Production Architecture Plan & Multi-Agent Gate | Synthesize master production plan document; execute multi-agent Reviewer, Challenger empirical verification, and Forensic Audit | M1, M2, M3, M4 | DONE |
| M6 | Production ETL Pipeline Implementation & Batch Ingestion | Ingest all 25 insurers, build CLI, extract 28,707 fact lines, verify zero-leakage analytical views | M1 - M5 | DONE |

## Production Pipeline Implementation
The pipeline is fully operational with CLI support via `main.py`:
- `python main.py --init-db`: Initializes schema and dimensions in SQLite/DuckDB.
- `python main.py --ingest-all`: Executes streaming spatial block ingestion across all 25 insurer workbooks (completes in ~17-21 seconds).
- `python main.py --ingest-file <path>`: Ingests an individual insurer workbook.
- `python main.py --status`: Displays real-time database record counts across dimensions, facts, lineages, and quarantines.
- `python main.py --top-premiums <period_id>`: Produces cross-insurer gross premium market share rankings normalized to INR Lakhs.
- `python main.py --solvency-ranking <period_id>`: Computes and ranks IRDAI statutory solvency ratios with regulatory compliance flags.

## Database File & Analytics
- Primary SQLite Database: `life_insurance.db` (WAL mode enabled, foreign keys enforced).
- Analytical Views:
  - `vw_dashboard_financials`: High-performance additive leaf metric view for Power BI / Web dashboards guaranteeing ZERO double-counting.
  - `vw_leaf_financials`: Granular leaf-level financial records.
  - `vw_unified_insurance_revenue`: Seamless time-series bridging statutory legacy premium and Ind AS 117 accrual metrics.

## Interface Contracts
### Ingestion Engine ↔ Relational Storage Layer
- Input: `SpatialTableBlock` (bounding box coordinates, insurer ID, fiscal period, schedule code, block unit multiplier).
- Output: Records staged in `stage_raw_cells` and transformed into `fact_financial_statement` and `fact_cell_lineage`.
- Data types: `cell_value_raw TEXT`, `cell_value_numeric NUMERIC(18, 4)`, `is_numeric BOOLEAN`.
- Error Handling: Malformed cells routed to `quarantine_syntax_cells`.

### Relational Storage Layer ↔ Reconciliation Engine
- Input: `fact_financial_statement` active records for a given `(company_id, period_id)`.
- Output: Pass/fail records logged to `audit_reconciliation_runs`; discrepancies routed to `quarantine_reconciliation_discrepancies`.
- Verification Signatures:
  * `reconcile_l1_l4_premium(company_id, period_id) -> Result[Status, Delta, Tolerance]`
  * `reconcile_l3_balance_sheet(company_id, period_id) -> Result[Status, Delta, Tolerance]`
  * `reconcile_fund_cross_flow(company_id, period_id) -> Result[Status, Delta, Tolerance]`

### Legacy IRDAI Model ↔ Ind AS 117 Bridge
- Mapping: `dim_accounting_standard` links legacy `IRDAI_CASH` reporting to `IND_AS_117_ACCRUAL`.
- View `vw_unified_insurance_revenue` provides seamless multi-year analytical series across standard transition dates.

## Code Layout
- Agent metadata & reports: `.agents/teamwork/`
- Reference documents & outputs:
  * Master Hardened Architecture Deliverable: `docs/life_insurance_hardened_database_and_etl_architecture_plan.md`
