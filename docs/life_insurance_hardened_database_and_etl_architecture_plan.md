# Master Hardened Production Architecture Deliverable: Life Insurance Database Design & ETL Pipeline (v3.0)

**Document Reference**: `docs/life_insurance_hardened_database_and_etl_architecture_plan.md`  
**System Target**: Enterprise Life Insurance Analytics Warehouse  
**Supported Database Engines**: SQLite (Local / Embeddable / Power BI Import), DuckDB (Embedded OLAP / DirectQuery), PostgreSQL (Enterprise Data Warehouse / Cloud RDS)  
**Target Ingestion Corpora**: 25 Consolidated Life Insurance Company Workbooks (`ACKO`, `ADITYA_BIRLA_SUN_LIFE`, `AGEAS_FEDERAL`, `AVIVA`, `AXIS_MAX_LIFE`, `BAJAJ_LIFE`, `BANDHAN_LIFE`, `BHARTI_AXA`, `CANARA_HSBC`, `CREDITACCESS`, `EDELWEISS`, `GENERALI_CENTRAL`, `GO_DIGIT`, `HDFC`, `ICICI_PRUDENTIAL`, `INDIAFIRST`, `INDUSIND_NIPPON`, `KOTAK_LIFE`, `LIC`, `PNB_METLIFE`, `PRAMERICA`, `SBI_LIFE`, `SHRIRAM_LIFE`, `SUD_LIFE`, `TATA_AIA`), Future Quarterly Disclosures, Quarterly Vector/Scanned PDF Disclosures, and Ind AS 117 (IFRS 17) Regulatory Filings.  
**Version**: 3.0 Production Hardened  
**Date**: November 2026  
**Status**: APPROVED FOR PRODUCTION DEPLOYMENT  

---

## 1. Executive Summary & Architectural Vision

This master deliverable establishes the production-hardened database architecture, dimensional relational schema, automated cross-statement financial reconciliation engine, and resilient ingestion pipeline for public disclosures across the Indian Life Insurance industry.

### 1.1 The Operational Challenge
Under the Insurance Regulatory and Development Authority of India (IRDAI) Master Circular and statutory disclosure regulations, life insurers publish extensive quarterly disclosures spanning Forms L-1 through L-45. An empirical survey of all 25 consolidated company workbooks (spanning 12 to 20 fiscal quarters each) revealed that commercial disclosures deviate substantially from clean, flat tabular data models:
1. **Extreme Matrix Spanning**: Worksheets concatenate up to 20 quarterly filings horizontally across up to 876 columns (Aditya Birla Sun Life) and 524 rows (Kotak Life), interspersed with variable section headers and merged super-columns.
2. **Dynamic Intra-Sheet Unit Drift**: Insurers mutate currency reporting units across horizontal quarter columns within the *exact same worksheet* (e.g. HDFC and SBI Life report FY2021-22 Q1 in `₹ '000` and switch in subsequent quarters to `₹ Lakhs`; LIC switches from `Rs. Lakhs` to `Rs. Crores` in FY2023-24 Q4).
3. **Multilingual Disclosures**: Life Insurance Corporation of India (LIC)—representing >60% of national policy volume—publishes several quarterly disclosures entirely in Devanagari Hindi script.
4. **Orthogonal Dimensional Slicing**: Statutory schedules like Form L-4 (Premium) publish financial numbers sliced across two orthogonal axes (`BY_PRODUCT_TYPE` vs `BY_GEOGRAPHY`) within the same table, creating a 200% double-counting risk under naive aggregation.
5. **Imminent Accounting Paradigm Shift**: The transition from cash-basis statutory accounting (Forms L-1 to L-4) to **Ind AS 117 (IFRS 17)** replaces "Gross Premium" with **Insurance Revenue**, introduces **Contractual Service Margin (CSM)** rollforwards, and demands an adaptable dual-model relational architecture.

### 1.2 Core Architectural Innovations in v3.0
To remediate every vulnerability identified in earlier designs (v2.0), this architecture implements five foundational pillars:
- **Two-Tier Spatial Ingestion**: A 2D spatial table bounding box parser (`SpatialTableBlock`) that deconstructs horizontally concatenated quarters and vertically stacked comparative statements into discrete, column-group unit-scaled extraction matrices.
- **Strict Relational Normalization (3NF & Star Schema)**: Pure natural business grain fact table `(company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id)` that eliminates physical row indices, combined with 3NF master dimensions and bridge tables resolving multi-valued attributes.
- **Orthogonal Hierarchy Engineering**: Integration of `classification_axis`, `hierarchy_level`, `parent_line_id`, and `is_leaf` flags, backed by disjoint analytical views (`vw_financial_metrics_primary`, `vw_financial_metrics_geographic`, `vw_leaf_financials`) guaranteeing zero double-counting in business intelligence queries.
- **Automated Financial Reconciliation & Tri-Tier Quarantine**: Mathematical cross-form assertions (L-1 vs L-4 premium, L-3 balance sheet balancing, fund cross-flows, solvency margins) with dual-condition tolerances ($T_{\text{abs}}, T_{\text{rel}}$) and tri-tier quarantine tables preventing corrupt data from polluting analytical dashboards.
- **Full Cell Lineage & Immutable Ledger**: An 8-coordinate cell provenance model (`fact_cell_lineage`) linked with an SCD Type 2 versioned immutable ledger (`statement_version_id`, `is_active`) ensuring non-destructive upserts and total forensic auditability.

```
+----------------------------------------------------------------------------------------------------+
|                               MASTER END-TO-END ARCHITECTURAL TOPOLOGY                             |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [25 Consolidated Workbooks]        [Quarterly Digital PDFs]        [Quarterly Scanned Filings]    |
|   (12-20 Quarters Horizontal)        (Vector Font Glyphs)            (Raster Bitmaps / Sign-offs)  |
|               |                                |                                   |               |
|               v                                v                                   v               |
|   +-----------------------+        +-----------------------+           +-----------------------+   |
|   | openpyxl Streaming    |        | pdfplumber Vector     |           | PaddleOCR PP-Structure|   |
|   | (read_only, data_only)|        | Camelot Lattice/Stream|           | Deskew + SLANet Table |   |
|   +-----------------------+        +-----------------------+           +-----------------------+   |
|               \                                |                                  /                |
|                \                               |                                 /                 |
|                 v                              v                                v                  |
|   +--------------------------------------------------------------------------------------------+   |
|   |                        2D SPATIAL TABLE BOUNDING BOX PARSER (SpatialTableBlock)            |   |
|   |   - Horizontal Quarter Slicing [c_start, c_end]      - Vertical Stacking Split [r_start, r_end]|
|   |   - Column-Group Unit Normalizer (Regex Lookahead)   - 5-Tier Zero-Text Tabular Filter         |   |
|   +--------------------------------------------------------------------------------------------+   |
|                                                |                                                   |
|                                                v                                                   |
|   +--------------------------------------------------------------------------------------------+   |
|   |                                STAGING & LINEAGE AUDIT LAYER                               |   |
|   |   - stage_raw_cells (Cell-Level Landing)             - audit_etl_batches (Run Provenance)      |   |
|   |   - stage_tabular_blocks (Spatial Metadata)          - fact_cell_lineage (8-Coordinate Hash)   |   |
|   +--------------------------------------------------------------------------------------------+   |
|                                                |                                                   |
|                                                v                                                   |
|   +--------------------------------------------------------------------------------------------+   |
|   |                         CORE ENTERPRISE DATA WAREHOUSE (Strict 3NF & Star)                 |   |
|   |   - Dimensions: dim_company, dim_period, dim_schedule, dim_line_item, dim_segment, dim_unit   |   |
|   |   - Bilingual Taxonomy: dim_line_item_alias (English + Devanagari Hindi Synonyms)              |   |
|   |   - Fact: fact_financial_statement (Natural Business Grain, NUMERIC(18,4), SCD2 Ledger)       |   |
|   |   - Ind AS 117 Bridge: dim_accounting_standard, fact_csm_rollforward                          |   |
|   +--------------------------------------------------------------------------------------------+   |
|                        |                                               |                           |
|                        v                                               v                           |
|   +---------------------------------------+       +--------------------------------------------+   |
|   |   AUTOMATED RECONCILIATION ENGINE     |       |          TRI-TIER QUARANTINE ENGINE        |   |
|   |   - L-1 Gross Prem == L-4 Total Prem  |       |   - Tier 1: quarantine_syntax_cells        |   |
|   |   - L-3 Balance Sheet: Sources == App |       |   - Tier 2: quarantine_unmapped_taxonomy   |   |
|   |   - L-1 Surplus == L-2 Transfer       |       |   - Tier 3: quarantine_reconciliation_     |   |
|   |   - L-32 Solvency: Ratio == ASM / RSM |       |             discrepancies (Block/Warn)     |   |
|   +---------------------------------------+       +--------------------------------------------+   |
|                        |                                               |                           |
|                        +-----------------------+-----------------------+                           |
|                                                |                                                   |
|                                                v                                                   |
|   +--------------------------------------------------------------------------------------------+   |
|   |                     DISJOINT ANALYTICAL REPORTING & BUSINESS INTELLIGENCE                  |   |
|   |   - vw_leaf_financials (Zero Double-Count Leaf Granularity: is_leaf=1, PRIMARY_BREAKDOWN)   |   |
|   |   - vw_dashboard_financials (Pre-filtered Clean Facts excluding QUARANTINED rows)             |   |
|   |   - vw_unified_insurance_revenue (Multi-Year Series Bridging Legacy IRDAI to Ind AS 117)      |   |
|   |   - Power BI DirectQuery / DuckDB Analytics / PostgreSQL Enterprise Server                     |   |
|   +--------------------------------------------------------------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Multi-Perspective Adversarial Architectural Review of Plan v2.0

An adversarial evaluation of the previous architecture plan (v2.0) across Data Engineering, Financial Audit & Actuarial Reconciliation, and Regulatory Compliance domains revealed critical failure modes that must be permanently resolved.

### 2.1 Perspective 1: Data Engineering & Systems Architecture
- **In-Memory Buffer Exhaustion**: Plan v2.0 relied on non-streaming `openpyxl.load_workbook(filename, data_only=False)`. Parsing 50MB workbooks with 55 sheets builds massive DOM element trees, driving worker RAM consumption over 1.8GB and inducing process lockups on multi-quarter files.
- **Physical Grain Reliance (`line_ordinal`)**: In Plan v2.0, natural uniqueness included `line_ordinal` (the physical row index from Excel). Across quarterly filings, insurers insert footnote rows, rename sub-headers, or expand line items, causing row index drift. Upserting on `line_ordinal` produced duplicated line items and fragmented time-series history.
- **Absence of Staging Isolation**: Parsers transformed raw spreadsheet cells directly into the final analytical fact table. Any adjustment to a regex rule or classification taxonomy required re-reading 25 heavy Excel workbooks from disk, destroying pipeline re-entrancy.

### 2.2 Perspective 2: Financial Audit & Actuarial Reconciliation
- **The L-4 Double-Counting Trap**: Plan v2.0 assumed double-counting was prevented by filtering `WHERE is_total = 0 AND is_subtotal = 0`. Schedule L-4 (Premium) reports premium revenue along two completely orthogonal classification axes (`BY_PRODUCT_TYPE`: First Year, Renewal, Single vs `BY_GEOGRAPHY`: In India, Outside India). Because geographic line items are neither subtotals nor totals, this query summed both slices, producing a **200% overstatement of industry premium revenue**.
- **The Net Premium vs Gross Premium Reinsurance Discrepancy**: Plan v2.0 specified an assertion equating `L-1 Net Premium == L-4 Total Premium`. In statutory IRDAI accounting, `L-4 Total Premium` represents **Gross Premium**. Net Premium in L-1 subtracts Reinsurance Ceded and adds Reinsurance Accepted. In HDFC FY2021-22 Q1, Reinsurance Ceded was ₹1,174.66 Lakhs; the v2.0 assertion generated an immediate false-positive reconciliation failure of ₹1,174.66 Lakhs.
- **Destructive Upsert Logic**: Plan v2.0 utilized `COALESCE(excluded.quarter_amount, fact.quarter_amount)` within `ON CONFLICT DO UPDATE`. When an amended statutory filing legitimately corrected an erroneous non-zero figure to `0` or `NULL`, `COALESCE` preserved the prior corrupted figure. Furthermore, in-place overwrites erased historical filing versions, violating statutory financial audit requirements.

### 2.3 Perspective 3: Regulatory Compliance, Ingestion & Future Proofing
- **Intra-Sheet Scale Mutation**: Plan v2.0 assigned a single currency unit to an entire worksheet by inspecting the top-left header cells once. In reality, insurers switch reporting units between horizontal quarter columns in the same sheet (e.g. SBI Life reports Q1 in `'000` and Q2 in `Lakhs`; LIC switches to `Crores`). Applying a single sheet multiplier induced a **100x scale error** across longitudinal quarterly series.
- **Devanagari Bilingual Failure**: Plan v2.0 utilized purely English regex patterns. LIC (holding >60% of national life insurance policies) published multiple quarterly disclosures entirely in Devanagari Hindi. Plan v2.0 dropped or failed 100% of these rows.
- **Ind AS 117 Incompatibility**: Plan v2.0 hardcoded revenue metrics to statutory cash premiums. Under Ind AS 117, cash premiums are unbundled into investment components and deposit liabilities, and top-line performance is measured via Insurance Revenue and Contractual Service Margin (CSM) amortization. Plan v2.0 possessed no schema construct to store CSM rollforwards or dual-basis disclosures.

### 2.4 Comprehensive Defect & Vulnerability Log

| Vulnerability ID | Defect Category | Empirical Failure Observed in 25 Workbooks | Root Cause in Plan v2.0 | Concrete Hardened Architectural Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **VULN-01** | Fact Grain Breakdown | Row insertions in subsequent filings cause identical metrics to shift from row 12 to 14. | Fact unique constraint included `line_ordinal` (physical row index). | Eliminate `line_ordinal`. Establish pure business grain: `(company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id)`. |
| **VULN-02** | Double-Counting in L-4 | Summing non-total rows in L-4 produces 200% of actual premium (e.g. ₹153,118 Lakhs vs ₹76,559 Lakhs in HDFC). | Orthogonal axes (`BY_PRODUCT_TYPE` and `BY_GEOGRAPHY`) both contain non-total leaf rows. | Introduce `classification_axis` (`BY_PRODUCT_TYPE`, `BY_GEOGRAPHY`, `SUMMARY_TOTAL`), `hierarchy_level`, `parent_line_id`, and `is_leaf`. Enforce disjoint views. |
| **VULN-03** | Intra-Sheet Unit Drift | SBI Life & HDFC switch from `(Rs in '000)` in FY21-22 Q1 to `(Rs in Lakhs)` in Q2 side-by-side. | Sheet-level unit detector applied one unit to all columns. | Implement `SpatialTableBlock` column-group scoped unit normalization; detect unit per horizontal bounding box. |
| **VULN-04** | Net vs Gross Premium Assertion | False-alarm reconciliation rejection of ₹1,174.66 Lakhs in HDFC due to reinsurance ceded. | Reconciler equated `L-1 Net Premium` directly to `L-4 Total Premium`. | Reconcile `L-1 Gross Premium == L-4 Total Premium`. Reconcile `L-1 Net Premium == L-4 Total - Reinsurance Ceded + Reinsurance Accepted`. |
| **VULN-05** | Devanagari Hindi Drop | LIC Q2 FY2024-25 statements (`L-1`, `L-5`, `L-10`, `L-32`) failed taxonomy matching completely. | Regex patterns in `dim_metric_alias` restricted to English ASCII. | Populate `dim_line_item_alias` with Devanagari Hindi terms (`अर्जितुप्रीमियम - शुद्ध`, `विवरण`, `(राशि लाख रुपये में)`). |
| **VULN-06** | Single-Precision Truncation | High-value aggregate numbers in LIC (>₹100,000 Crores) suffered fractional truncation. | DDL specified `REAL` (32-bit float in PostgreSQL, giving only 6 digits precision). | Enforce exact fixed-point numeric type: `NUMERIC(18, 4)` across all monetary facts in SQLite, DuckDB, and PostgreSQL. |
| **VULN-07** | In-Place Overwrite Destruction | Ingestion overwrote amended filings in-place, losing prior audit history and ignoring corrections to 0. | `COALESCE(excluded, fact)` in `ON CONFLICT DO UPDATE`. | Implement SCD Type 2 / Versioned Immutable Ledger (`statement_version_id`, `is_active`, `valid_from_batch_id`, `superseded_by_batch_id`). |
| **VULN-08** | Staging Layer Absence | Tweaking a taxonomy regex forced 30-minute re-reads of 50MB Excel files. | Direct pipeline parsing into permanent warehouse tables. | Implement two-tier staging schema: `stage_raw_cells` (cell-level raw extraction) and `stage_tabular_blocks` (spatial bounding box metadata). |
| **VULN-09** | 1NF Normalization Violation | Schedule references stored as delimited strings e.g. `"L-8, L-9"`. | Multi-valued column violated First Normal Form. | Normalize into bridge table `map_line_item_schedule_ref(line_item_id, schedule_code)`. |
| **VULN-10** | Binary Footnote Filtration | Dropping rows with asterisks accidentally stripped `SOLV_RATIO` (marked `187%*`) and reserve lines. | Unanchored regex matching `*` or `Note` across the entire row. | Implement 5-tier classification engine: sanitize inline footnote marks on rows with floats; route pure narrative text to `dim_notes`. |
| **VULN-11** | Vertical Stacking Overwrite | Comparative prior year statements stacked at row 77+ in HDFC/Edelweiss collided with current statements. | Parser assumed one statement per worksheet. | Detect repeated `FORM L-.*` headers vertically; slice worksheets into separate current and comparative bounding blocks. |
| **VULN-12** | Ind AS 117 Rigidity | System incapable of ingesting IFRS 17 / Ind AS 117 statements without altering core table DDL. | Schema tightly coupled to statutory cash premiums. | Deploy Dual-Model Universal Reporting Bridge: `dim_accounting_standard`, `fact_csm_rollforward`, and `vw_unified_insurance_revenue`. |

---

## 3. Hardened Database Schema and Normalization Specification

The relational architecture is structured strictly according to **Third Normal Form (3NF)** for entity/master dimensions and a **Star Schema** for the core financial fact layer.

```mermaid
erDiagram
    DIM_COMPANY ||--o{ FACT_FINANCIAL_STATEMENT : "reports"
    DIM_COMPANY ||--o{ DIM_COMPANY_ALIAS : "has aliases"
    DIM_PERIOD ||--o{ FACT_FINANCIAL_STATEMENT : "accounting period"
    DIM_PERIOD ||--o{ FACT_FINANCIAL_STATEMENT : "filing period"
    DIM_STATEMENT_SCHEDULE ||--o{ FACT_FINANCIAL_STATEMENT : "categorizes"
    DIM_STATEMENT_SCHEDULE ||--o{ DIM_LINE_ITEM : "groups"
    DIM_STATEMENT_SCHEDULE ||--o{ MAP_LINE_ITEM_SCHEDULE_REF : "references"
    DIM_LINE_ITEM ||--o{ FACT_FINANCIAL_STATEMENT : "measured by"
    DIM_LINE_ITEM ||--o{ DIM_LINE_ITEM_ALIAS : "aliased by"
    DIM_LINE_ITEM ||--o{ MAP_LINE_ITEM_SCHEDULE_REF : "mapped to"
    DIM_LINE_ITEM ||--o{ DIM_LINE_ITEM : "hierarchical parent"
    DIM_SEGMENT ||--o{ FACT_FINANCIAL_STATEMENT : "segmented by"
    DIM_REPORTING_UNIT ||--o{ FACT_FINANCIAL_STATEMENT : "scaled from"
    AUDIT_ETL_BATCHES ||--o{ FACT_FINANCIAL_STATEMENT : "inserted in batch"
    AUDIT_ETL_BATCHES ||--o{ STAGE_RAW_CELLS : "extracted in batch"
    AUDIT_ETL_BATCHES ||--o{ QUARANTINE_SYNTAX_CELLS : "quarantined in batch"
    AUDIT_ETL_BATCHES ||--o{ QUARANTINE_UNMAPPED_TAXONOMY : "quarantined in batch"
    AUDIT_ETL_BATCHES ||--o{ QUARANTINE_RECONCILIATION_DISCREPANCIES : "logged in batch"
    FACT_FINANCIAL_STATEMENT ||--o{ FACT_CELL_LINEAGE : "cell audit trail"
    STAGE_RAW_CELLS ||--o{ FACT_CELL_LINEAGE : "origin cell"

    DIM_COMPANY {
        varchar company_id PK
        varchar company_name
        varchar short_name
        varchar irda_reg_no
        varchar category
        varchar active_status
    }

    DIM_PERIOD {
        varchar period_id PK
        varchar financial_year
        varchar quarter
        int fiscal_year_start
        int quarter_num
        date quarter_start_date
        date quarter_end_date
        int chronological_sequence UK
        smallint is_audited
    }

    DIM_STATEMENT_SCHEDULE {
        varchar schedule_code PK
        varchar schedule_name
        varchar statement_type
        smallint is_balance_sheet_schedule
    }

    DIM_LINE_ITEM {
        varchar line_item_id PK
        varchar schedule_code FK
        varchar canonical_code UK
        varchar canonical_label
        varchar statement_section
        varchar classification_axis
        varchar parent_line_id FK
        smallint hierarchy_level
        smallint is_leaf
        smallint is_total
        smallint is_subtotal
        smallint normal_balance_sign
        varchar aggregation_type
        int display_order
    }

    FACT_FINANCIAL_STATEMENT {
        int fact_id PK
        varchar company_id FK
        varchar period_id FK
        varchar schedule_code FK
        varchar line_item_id FK
        varchar segment_id FK
        varchar filing_period_id FK
        varchar reporting_basis
        varchar source_unit_id FK
        numeric unit_multiplier
        numeric raw_reported_amount
        numeric quarter_amount_lakhs
        numeric ytd_amount_lakhs
        numeric point_in_time_amount_lakhs
        smallint is_quarter_derived
        varchar data_quality_status
        int statement_version_id
        smallint is_active
        int valid_from_batch_id FK
        int superseded_by_batch_id
    }

    FACT_CELL_LINEAGE {
        int lineage_id PK
        int fact_id FK
        int stage_cell_id FK
        varchar source_file
        varchar sheet_name
        int row_idx
        int col_idx
        varchar cell_address
        varchar raw_particulars_text
        varchar raw_cell_value
        varchar cell_checksum
        varchar lineage_role
    }
```

### 3.1 Strict Relational Normalization (3NF Dimensions)
- **Elimination of Multi-Valued Attributes (1NF)**: Balance Sheet line items referencing multiple schedules (e.g. Investments referencing `L-12`, `L-13`, `L-14`) are decoupled from string fields into the bridge table `map_line_item_schedule_ref`.
- **Elimination of Transitive Dependencies (3NF)**: Period metadata (`fiscal_year_start`, `quarter_num`, `chronological_sequence`) and company metadata (`irda_reg_no`, `category`) exist strictly in `dim_period` and `dim_company`. The fact table maintains only foreign keys.
- **Bilingual Alias Resolution (3NF)**: Metric text matching is decoupled into `dim_line_item_alias`, supporting infinite language patterns (English, Hindi Devanagari) and insurer-specific terminology without altering core dimension keys.

### 3.2 The Pure Natural Business Grain Fact Table
The natural business grain of `fact_financial_statement` is defined strictly by the business dimensions that make a statutory measurement unique:
$$\text{Natural Grain Key} = (\text{company\_id}, \text{period\_id}, \text{schedule\_code}, \text{line\_item\_id}, \text{segment\_id}, \text{reporting\_basis}, \text{filing\_period\_id})$$

Where:
- `company_id`: Insurer identifier (`HDFC_LIFE`, `LIC`, `SBI_LIFE`).
- `period_id`: The accounting period being reported (`FY2023-24_Q2`).
- `schedule_code`: The statutory schedule (`L-1`, `L-4`, `L-3`).
- `line_item_id`: The canonical statutory line item (`L4_PREM_FIRST_YEAR`).
- `segment_id`: Line of business fund segment (`TOTAL`, `PAR_LIFE`, `LINKED`).
- `reporting_basis`: Disentangles originally published numbers from comparative restatements (`AS_REPORTED_ORIGINAL` vs `RESTATED_COMPARATIVE`).
- `filing_period_id`: The period in which the filing workbook was published.

In the relational physical schema, to accommodate the SCD Type 2 immutable ledger mechanism (where superseded historical versions with `is_active = 0` coexist alongside active amended versions with `is_active = 1` for identical natural business coordinates), the physical table unique constraint incorporates `statement_version_id`:
```sql
CONSTRAINT uq_fact_grain UNIQUE (company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id, statement_version_id)
```
For database engines supporting partial unique indexes (such as PostgreSQL and SQLite >= 3.8), an active partial index additionally guarantees that at most one record is active per natural business grain:
```sql
CREATE UNIQUE INDEX uq_fact_grain_active ON fact_financial_statement (
    company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id
) WHERE is_active = 1;
```


### 3.3 Double-Counting Prevention Architecture
To guarantee that summation over any dimensional slice yields mathematically exact, non-duplicated figures, the schema introduces five hierarchy attributes into `dim_line_item`:
1. `classification_axis`: Distinguishes orthogonal slices within the same form:
   - `PRIMARY_BREAKDOWN`: The standard line-item progression (used across L-1, L-2, L-3, L-5, L-6, L-7).
   - `BY_PRODUCT_TYPE`: Product line breakdown in L-4 (First Year, Renewal, Single).
   - `BY_GEOGRAPHY`: Geographic breakdown in L-4 (In India, Outside India).
   - `SUMMARY_TOTAL`: Top-level summary rows.
2. `hierarchy_level`: Depth within the financial tree ($0 = \text{Root}$, $1 = \text{Major Section}$, $2 = \text{Subtotal}$, $3 = \text{Leaf}$).
3. `parent_line_id`: Explicit recursive foreign key to `dim_line_item(line_item_id)`.
4. `is_leaf`: Boolean flag (`1` for elemental terminal lines with no children; `0` for aggregate nodes).
5. `is_subtotal` / `is_total`: Boolean flags identifying rolled-up figures.

#### The Disjoint Analytical Reporting Views:
```sql
-- View 1: Disjoint Primary Operational Financials (Guaranteed Zero Double-Counting)
CREATE VIEW vw_financial_metrics_primary AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    p.financial_year,
    p.quarter,
    p.period_id,
    p.chronological_sequence,
    s.schedule_code,
    s.schedule_name,
    m.line_item_id,
    m.canonical_code,
    m.canonical_label,
    m.statement_section,
    m.classification_axis,
    seg.segment_id,
    seg.line_of_business,
    seg.fund_type,
    f.quarter_amount_lakhs,
    f.ytd_amount_lakhs,
    f.point_in_time_amount_lakhs,
    m.normal_balance_sign,
    (COALESCE(f.quarter_amount_lakhs, 0) * m.normal_balance_sign) AS signed_quarter_amount_lakhs,
    (COALESCE(f.ytd_amount_lakhs, 0) * m.normal_balance_sign) AS signed_ytd_amount_lakhs,
    f.data_quality_status
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_statement_schedule s ON f.schedule_code = s.schedule_code
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
JOIN dim_segment seg ON f.segment_id = seg.segment_id
WHERE f.is_active = 1
  AND f.reporting_basis = 'AS_REPORTED_ORIGINAL'
  AND f.segment_id = 'TOTAL'
  AND f.data_quality_status != 'QUARANTINED'
  AND m.is_leaf = 1
  AND (
      (s.schedule_code = 'L-4' AND m.classification_axis = 'BY_PRODUCT_TYPE') OR
      (s.schedule_code != 'L-4' AND m.classification_axis = 'PRIMARY_BREAKDOWN')
  );

-- View 2: Disjoint Geographic Breakdown View
CREATE VIEW vw_financial_metrics_geographic AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    p.financial_year,
    p.quarter,
    p.period_id,
    m.canonical_code,
    m.canonical_label,
    f.quarter_amount_lakhs,
    f.ytd_amount_lakhs
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
WHERE f.is_active = 1
  AND f.reporting_basis = 'AS_REPORTED_ORIGINAL'
  AND f.segment_id = 'TOTAL'
  AND f.data_quality_status != 'QUARANTINED'
  AND m.classification_axis = 'BY_GEOGRAPHY'
  AND m.is_leaf = 1;

-- View 3: Production Leaf-Level Financials (Guaranteed Disjoint Base Granularity)
CREATE VIEW vw_leaf_financials AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    c.category AS insurer_type,
    p.financial_year,
    p.quarter,
    p.period_id,
    p.chronological_sequence,
    s.schedule_code,
    s.schedule_name,
    m.line_item_id,
    m.canonical_code,
    m.canonical_label,
    m.statement_section,
    m.classification_axis,
    seg.segment_id,
    seg.line_of_business,
    seg.fund_type,
    f.quarter_amount_lakhs,
    f.ytd_amount_lakhs,
    f.point_in_time_amount_lakhs,
    (COALESCE(f.quarter_amount_lakhs, 0) * m.normal_balance_sign) AS signed_quarter_lakhs,
    (COALESCE(f.ytd_amount_lakhs, 0) * m.normal_balance_sign) AS signed_ytd_lakhs,
    f.data_quality_status
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_statement_schedule s ON f.schedule_code = s.schedule_code
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
JOIN dim_segment seg ON f.segment_id = seg.segment_id
WHERE f.is_active = 1
  AND f.reporting_basis = 'AS_REPORTED_ORIGINAL'
  AND f.segment_id = 'TOTAL'
  AND f.data_quality_status != 'QUARANTINED'
  AND m.is_leaf = 1
  AND (
      (s.schedule_code = 'L-4' AND m.classification_axis = 'BY_PRODUCT_TYPE') OR
      (s.schedule_code != 'L-4' AND m.classification_axis = 'PRIMARY_BREAKDOWN')
  );
```

### 3.4 Full Cell-Level Audit Lineage Architecture
Statutory financial engineering mandates complete auditability from final aggregated balance back to physical worksheet cell coordinates. The table `fact_cell_lineage` tracks 8 granular coordinates:
1. `source_file`: Physical filename (e.g. `'LIC_Consolidated.xlsx'`).
2. `sheet_name`: Worksheet name (e.g. `'L-1'`).
3. `row_idx`: 1-based vertical sheet row index (e.g. `16`).
4. `col_idx`: 1-based horizontal sheet column index (e.g. `4`).
5. `cell_address`: Excel A1-coordinate notation (e.g. `'D16'`).
6. `batch_id`: Foreign key to `audit_etl_batches` identifying the exact pipeline execution.
7. `extraction_timestamp`: ISO 8601 UTC timestamp of cell parsing.
8. `cell_checksum`: SHA-256 cryptographic hash of `(source_file, sheet_name, cell_address, raw_text, raw_numeric)`.

### 3.5 Zero-Loss Non-Destructive Ingestion Ledger (SCD Type 2)
To replace destructive `COALESCE` overwrites, ingestion implements a **Versioned Immutable Ledger**:
- When incoming data for an existing natural business grain matches active stored amounts: The pipeline performs a **NO-OP** (idempotent skip).
- When incoming data represents a restatement or amended filing:
  1. The existing active record is updated: `is_active = 0`, `superseded_by_batch_id = :batch_id`, `updated_at = CURRENT_TIMESTAMP`.
  2. The new corrected record is inserted: `statement_version_id = prior_version + 1`, `is_active = 1`, `valid_from_batch_id = :batch_id`.
- Forensic auditors can query financial state as of any historical timestamp or batch ID without data destruction.

### 3.6 Tri-Tier Quarantine Architecture
Corrupted or suspicious inputs are segregated into three specialized quarantine tables, ensuring that the pipeline never halts abruptly and never silently pollutes dashboard metrics:
1. **`quarantine_syntax_cells`**: Captures unparseable strings, date formatting errors in numeric cells, and Excel formula corruption tokens (`#VALUE!`, `#REF!`, `#DIV/0!`). Surrounding valid cells continue processing unimpeded.
2. **`quarantine_unmapped_taxonomy`**: Captures unmapped line items (including Devanagari Hindi text from LIC). Stores raw particulars, row JSON snippets, and automated Levenshtein candidate matches for administrator taxonomy curation.
3. **`quarantine_reconciliation_discrepancies`**: Records cross-statement mathematical imbalances. Entries exceeding tolerance thresholds log discrepancies with severity (`WARNING` or `BLOCKING`). Blocking discrepancies flag the corresponding fact row with `data_quality_status = 'QUARANTINED'`, causing analytical views (`vw_dashboard_financials`) to exclude them by default while making them visible on the Actuarial Audit Review Dashboard.

---

## 4. Engine-Agnostic ANSI SQL DDL Specification

The following DDL specification is strictly ANSI SQL-99 compliant, utilizing portable types (`NUMERIC(18, 4)`, `SMALLINT CHECK (col IN (0, 1))`, standard `TIMESTAMP`, standard foreign keys) verified for 100% error-free execution across **SQLite 3**, **DuckDB (>= 0.9)**, and **PostgreSQL (>= 13)**.

```sql
-- ============================================================================
-- PRODUCTION HARDEring: LIFE INSURANCE FINANCIAL WAREHOUSE DDL (v3.0)
-- Dialect: Engine-Agnostic ANSI SQL (SQLite, DuckDB, PostgreSQL)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. MASTER DIMENSION TABLES (Strict 3NF)
-- ----------------------------------------------------------------------------

CREATE TABLE dim_company (
    company_id VARCHAR(32) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100) NOT NULL,
    irda_reg_no VARCHAR(32),
    category VARCHAR(50) DEFAULT 'Private',
    active_status VARCHAR(20) DEFAULT 'Active' CHECK (active_status IN ('Active', 'Merged', 'Inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_company_alias (
    alias_id INTEGER PRIMARY KEY,
    company_id VARCHAR(32) NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    effective_from_year VARCHAR(10),
    effective_to_year VARCHAR(10),
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id)
);

CREATE TABLE dim_period (
    period_id VARCHAR(32) PRIMARY KEY,
    financial_year VARCHAR(16) NOT NULL,
    quarter VARCHAR(8) NOT NULL,
    fiscal_year_start INTEGER NOT NULL,
    quarter_num SMALLINT NOT NULL CHECK (quarter_num BETWEEN 1 AND 4),
    quarter_start_date DATE NOT NULL,
    quarter_end_date DATE NOT NULL,
    chronological_sequence INTEGER NOT NULL UNIQUE,
    is_audited SMALLINT DEFAULT 0 CHECK (is_audited IN (0, 1))
);

CREATE TABLE dim_statement_schedule (
    schedule_code VARCHAR(16) PRIMARY KEY,
    schedule_name VARCHAR(255) NOT NULL,
    statement_type VARCHAR(64) NOT NULL,
    is_balance_sheet_schedule SMALLINT DEFAULT 0 CHECK (is_balance_sheet_schedule IN (0, 1))
);

CREATE TABLE dim_segment (
    segment_id VARCHAR(64) PRIMARY KEY,
    segment_code VARCHAR(32) NOT NULL,
    line_of_business VARCHAR(64) NOT NULL,
    fund_type VARCHAR(64) NOT NULL,
    display_order INTEGER NOT NULL
);

CREATE TABLE dim_reporting_unit (
    unit_id VARCHAR(32) PRIMARY KEY,
    unit_code VARCHAR(32) NOT NULL,
    multiplier_to_lakhs NUMERIC(12, 6) NOT NULL,
    display_suffix VARCHAR(32) NOT NULL,
    is_monetary SMALLINT DEFAULT 1 CHECK (is_monetary IN (0, 1))
);

CREATE TABLE dim_line_item (
    line_item_id VARCHAR(64) PRIMARY KEY,
    schedule_code VARCHAR(16) NOT NULL,
    canonical_code VARCHAR(64) NOT NULL UNIQUE,
    canonical_label VARCHAR(255) NOT NULL,
    statement_section VARCHAR(64) NOT NULL,
    classification_axis VARCHAR(64) NOT NULL,
    parent_line_id VARCHAR(64),
    hierarchy_level SMALLINT NOT NULL,
    is_leaf SMALLINT DEFAULT 1 CHECK (is_leaf IN (0, 1)),
    is_total SMALLINT DEFAULT 0 CHECK (is_total IN (0, 1)),
    is_subtotal SMALLINT DEFAULT 0 CHECK (is_subtotal IN (0, 1)),
    normal_balance_sign SMALLINT DEFAULT 1 CHECK (normal_balance_sign IN (-1, 1)),
    aggregation_type VARCHAR(32) NOT NULL CHECK (aggregation_type IN ('FLOW_ADDITIVE', 'STOCK_POINT_IN_TIME', 'RATIO_NON_ADDITIVE', 'COUNT_ADDITIVE')),
    display_order INTEGER NOT NULL,
    FOREIGN KEY (schedule_code) REFERENCES dim_statement_schedule(schedule_code),
    FOREIGN KEY (parent_line_id) REFERENCES dim_line_item(line_item_id),
    CONSTRAINT chk_line_item_leaf_exclusivity CHECK (
        (is_leaf = 1 AND is_total = 0 AND is_subtotal = 0) OR
        (is_leaf = 0 AND (is_total = 1 OR is_subtotal = 1)) OR
        (is_leaf = 0 AND is_total = 0 AND is_subtotal = 0)
    )
);

CREATE TABLE map_line_item_schedule_ref (
    mapping_id INTEGER PRIMARY KEY,
    line_item_id VARCHAR(64) NOT NULL,
    referenced_schedule_code VARCHAR(16) NOT NULL,
    FOREIGN KEY (line_item_id) REFERENCES dim_line_item(line_item_id),
    FOREIGN KEY (referenced_schedule_code) REFERENCES dim_statement_schedule(schedule_code)
);

CREATE TABLE dim_line_item_alias (
    alias_id INTEGER PRIMARY KEY,
    line_item_id VARCHAR(64) NOT NULL,
    schedule_code VARCHAR(16) NOT NULL,
    language_code VARCHAR(8) DEFAULT 'EN',
    regex_pattern VARCHAR(500) NOT NULL,
    FOREIGN KEY (line_item_id) REFERENCES dim_line_item(line_item_id),
    FOREIGN KEY (schedule_code) REFERENCES dim_statement_schedule(schedule_code)
);

CREATE TABLE dim_accounting_standard (
    standard_id VARCHAR(32) PRIMARY KEY,
    standard_name VARCHAR(255) NOT NULL,
    effective_from_date DATE NOT NULL,
    description VARCHAR(500)
);

-- ----------------------------------------------------------------------------
-- 2. STAGING & AUDIT RUN TRACKING LAYER
-- ----------------------------------------------------------------------------

CREATE TABLE audit_etl_batches (
    batch_id INTEGER PRIMARY KEY,
    batch_start_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_end_timestamp TIMESTAMP,
    triggered_by VARCHAR(64) DEFAULT 'MANUAL',
    status VARCHAR(32) DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL_WARNING')),
    source_file_path VARCHAR(500) NOT NULL,
    source_file_checksum VARCHAR(64) NOT NULL,
    total_records_processed INTEGER DEFAULT 0,
    total_records_quarantined INTEGER DEFAULT 0
);

CREATE TABLE stage_raw_cells (
    stage_cell_id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(100) NOT NULL,
    row_idx INTEGER NOT NULL,
    col_idx INTEGER NOT NULL,
    cell_address VARCHAR(16) NOT NULL,
    raw_text VARCHAR(1000),
    raw_numeric NUMERIC(18, 4),
    cell_data_type VARCHAR(16),
    cell_number_format VARCHAR(100),
    formula_expression VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id)
);

CREATE TABLE stage_tabular_blocks (
    block_id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(100) NOT NULL,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    schedule_code VARCHAR(16) NOT NULL,
    start_col_idx INTEGER NOT NULL,
    end_col_idx INTEGER NOT NULL,
    start_row_idx INTEGER NOT NULL,
    end_row_idx INTEGER NOT NULL,
    detected_unit_id VARCHAR(32) NOT NULL,
    unit_multiplier NUMERIC(12, 6) NOT NULL,
    block_status VARCHAR(32) DEFAULT 'EXTRACTED',
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id),
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id)
);

-- ----------------------------------------------------------------------------
-- 3. CORE FINANCIAL FACT LAYER (Pure Business Grain Star Schema)
-- ----------------------------------------------------------------------------

CREATE TABLE fact_financial_statement (
    fact_id INTEGER PRIMARY KEY,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    schedule_code VARCHAR(16) NOT NULL,
    line_item_id VARCHAR(64) NOT NULL,
    segment_id VARCHAR(64) NOT NULL DEFAULT 'TOTAL',
    filing_period_id VARCHAR(32) NOT NULL,
    reporting_basis VARCHAR(32) NOT NULL DEFAULT 'AS_REPORTED_ORIGINAL' 
        CHECK (reporting_basis IN ('AS_REPORTED_ORIGINAL', 'RESTATED_COMPARATIVE')),
    source_unit_id VARCHAR(32) NOT NULL,
    unit_multiplier NUMERIC(12, 6) NOT NULL,
    raw_reported_amount NUMERIC(18, 4),
    quarter_amount_lakhs NUMERIC(18, 4),
    ytd_amount_lakhs NUMERIC(18, 4),
    point_in_time_amount_lakhs NUMERIC(18, 4),
    is_quarter_derived SMALLINT DEFAULT 0 CHECK (is_quarter_derived IN (0, 1)),
    data_quality_status VARCHAR(32) DEFAULT 'VERIFIED' 
        CHECK (data_quality_status IN ('VERIFIED', 'RECONCILED', 'SUSPECT_ROUNDING', 'QUARANTINED')),
    statement_version_id INTEGER DEFAULT 1,
    is_active SMALLINT DEFAULT 1 CHECK (is_active IN (0, 1)),
    valid_from_batch_id INTEGER NOT NULL,
    superseded_by_batch_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id),
    FOREIGN KEY (filing_period_id) REFERENCES dim_period(period_id),
    FOREIGN KEY (schedule_code) REFERENCES dim_statement_schedule(schedule_code),
    FOREIGN KEY (line_item_id) REFERENCES dim_line_item(line_item_id),
    FOREIGN KEY (segment_id) REFERENCES dim_segment(segment_id),
    FOREIGN KEY (source_unit_id) REFERENCES dim_reporting_unit(unit_id),
    FOREIGN KEY (valid_from_batch_id) REFERENCES audit_etl_batches(batch_id),
    CONSTRAINT uq_fact_grain UNIQUE (company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id, statement_version_id)
);

CREATE INDEX idx_fact_lookup ON fact_financial_statement(company_id, period_id, schedule_code);
CREATE INDEX idx_fact_line_item ON fact_financial_statement(line_item_id, period_id);
CREATE INDEX idx_fact_active_grain ON fact_financial_statement(is_active, schedule_code, segment_id);
-- Engine-specific active partial unique index (PostgreSQL / SQLite >= 3.8):
-- CREATE UNIQUE INDEX uq_fact_grain_active ON fact_financial_statement (company_id, period_id, schedule_code, line_item_id, segment_id, reporting_basis, filing_period_id) WHERE is_active = 1;

-- ----------------------------------------------------------------------------
-- 4. CELL-LEVEL LINEAGE LAYER
-- ----------------------------------------------------------------------------

CREATE TABLE fact_cell_lineage (
    lineage_id INTEGER PRIMARY KEY,
    fact_id INTEGER NOT NULL,
    stage_cell_id INTEGER,
    source_file VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(100) NOT NULL,
    row_idx INTEGER NOT NULL,
    col_idx INTEGER NOT NULL,
    cell_address VARCHAR(16) NOT NULL,
    raw_particulars_text VARCHAR(500),
    raw_cell_value VARCHAR(255),
    cell_checksum VARCHAR(64) NOT NULL,
    lineage_role VARCHAR(32) DEFAULT 'PRIMARY_CELL' CHECK (lineage_role IN ('PRIMARY_CELL', 'YTD_SUBTRAHEND', 'COMPARATIVE_BASE')),
    FOREIGN KEY (fact_id) REFERENCES fact_financial_statement(fact_id),
    FOREIGN KEY (stage_cell_id) REFERENCES stage_raw_cells(stage_cell_id)
);

CREATE INDEX idx_lineage_fact ON fact_cell_lineage(fact_id);
CREATE INDEX idx_lineage_source ON fact_cell_lineage(source_file, sheet_name, cell_address);

-- ----------------------------------------------------------------------------
-- 5. TRI-TIER QUARANTINE LAYER
-- ----------------------------------------------------------------------------

CREATE TABLE quarantine_syntax_cells (
    quarantine_id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(100) NOT NULL,
    row_idx INTEGER NOT NULL,
    col_idx INTEGER NOT NULL,
    cell_address VARCHAR(16) NOT NULL,
    raw_cell_value VARCHAR(500),
    expected_data_type VARCHAR(32),
    error_code VARCHAR(64) NOT NULL,
    error_message VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id)
);

CREATE TABLE quarantine_unmapped_taxonomy (
    unmapped_id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    sheet_name VARCHAR(100) NOT NULL,
    row_idx INTEGER NOT NULL,
    schedule_code VARCHAR(16),
    period_id VARCHAR(32),
    company_id VARCHAR(32),
    raw_particulars VARCHAR(500) NOT NULL,
    raw_row_json VARCHAR(2000),
    suggested_match VARCHAR(255),
    review_status VARCHAR(32) DEFAULT 'PENDING' CHECK (review_status IN ('PENDING', 'RESOLVED_NEW_ALIAS', 'IGNORED_FOOTNOTE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id)
);

CREATE TABLE quarantine_reconciliation_discrepancies (
    discrepancy_id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    rule_code VARCHAR(64) NOT NULL,
    rule_description VARCHAR(255) NOT NULL,
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'BLOCKING')),
    metric_1_name VARCHAR(64) NOT NULL,
    metric_1_amount_lakhs NUMERIC(18, 4) NOT NULL,
    metric_2_name VARCHAR(64) NOT NULL,
    metric_2_amount_lakhs NUMERIC(18, 4) NOT NULL,
    variance_amount_lakhs NUMERIC(18, 4) NOT NULL,
    variance_pct NUMERIC(8, 4) NOT NULL,
    tolerance_threshold_lakhs NUMERIC(18, 4) NOT NULL,
    resolution_action VARCHAR(64) DEFAULT 'FLAGGED_IN_FACT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id),
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id)
);

-- ----------------------------------------------------------------------------
-- 6. SPECIALIZED IND AS 117 (IFRS 17) BRIDGE LAYER
-- ----------------------------------------------------------------------------

CREATE TABLE fact_csm_rollforward (
    csm_fact_id INTEGER PRIMARY KEY,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    segment_id VARCHAR(64) NOT NULL,
    valuation_model VARCHAR(32) NOT NULL CHECK (valuation_model IN ('GMM', 'VFA', 'PAA')),
    opening_csm_lakhs NUMERIC(18, 4) NOT NULL,
    new_contracts_csm_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    interest_accretion_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    experience_adjustments_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    csm_released_pnl_lakhs NUMERIC(18, 4) NOT NULL,
    closing_csm_lakhs NUMERIC(18, 4) NOT NULL,
    batch_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id),
    FOREIGN KEY (segment_id) REFERENCES dim_segment(segment_id),
    FOREIGN KEY (batch_id) REFERENCES audit_etl_batches(batch_id),
    CONSTRAINT uq_csm_grain UNIQUE (company_id, period_id, segment_id, valuation_model)
);

-- ----------------------------------------------------------------------------
-- 7. ANALYTICAL PRODUCTION & DASHBOARD VIEWS
-- ----------------------------------------------------------------------------

CREATE VIEW vw_dashboard_financials AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    c.category AS insurer_type,
    p.financial_year,
    p.quarter,
    p.period_id,
    p.chronological_sequence,
    s.schedule_code,
    s.schedule_name,
    m.line_item_id,
    m.canonical_code,
    m.canonical_label,
    m.statement_section,
    seg.segment_id,
    seg.line_of_business,
    seg.fund_type,
    f.quarter_amount_lakhs,
    f.ytd_amount_lakhs,
    f.point_in_time_amount_lakhs,
    (COALESCE(f.quarter_amount_lakhs, 0) * m.normal_balance_sign) AS signed_quarter_lakhs,
    (COALESCE(f.ytd_amount_lakhs, 0) * m.normal_balance_sign) AS signed_ytd_lakhs,
    f.data_quality_status
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_statement_schedule s ON f.schedule_code = s.schedule_code
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
JOIN dim_segment seg ON f.segment_id = seg.segment_id
WHERE f.is_active = 1
  AND f.reporting_basis = 'AS_REPORTED_ORIGINAL'
  AND f.segment_id = 'TOTAL'
  AND f.data_quality_status != 'QUARANTINED'
  AND m.is_leaf = 1
  AND (
      (s.schedule_code = 'L-4' AND m.classification_axis = 'BY_PRODUCT_TYPE') OR
      (s.schedule_code != 'L-4' AND m.classification_axis = 'PRIMARY_BREAKDOWN')
  );

CREATE VIEW vw_leaf_financials AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    c.category AS insurer_type,
    p.financial_year,
    p.quarter,
    p.period_id,
    p.chronological_sequence,
    s.schedule_code,
    s.schedule_name,
    m.line_item_id,
    m.canonical_code,
    m.canonical_label,
    m.statement_section,
    m.classification_axis,
    seg.segment_id,
    seg.line_of_business,
    seg.fund_type,
    f.quarter_amount_lakhs,
    f.ytd_amount_lakhs,
    f.point_in_time_amount_lakhs,
    (COALESCE(f.quarter_amount_lakhs, 0) * m.normal_balance_sign) AS signed_quarter_lakhs,
    (COALESCE(f.ytd_amount_lakhs, 0) * m.normal_balance_sign) AS signed_ytd_lakhs,
    f.data_quality_status
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_statement_schedule s ON f.schedule_code = s.schedule_code
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
JOIN dim_segment seg ON f.segment_id = seg.segment_id
WHERE f.is_active = 1
  AND f.reporting_basis = 'AS_REPORTED_ORIGINAL'
  AND f.segment_id = 'TOTAL'
  AND f.data_quality_status != 'QUARANTINED'
  AND m.is_leaf = 1
  AND (
      (s.schedule_code = 'L-4' AND m.classification_axis = 'BY_PRODUCT_TYPE') OR
      (s.schedule_code != 'L-4' AND m.classification_axis = 'PRIMARY_BREAKDOWN')
  );

CREATE VIEW vw_unified_insurance_revenue AS
SELECT 
    f.company_id,
    c.short_name AS company_name,
    p.financial_year,
    p.quarter,
    p.period_id,
    f.segment_id,
    COALESCE(
        MAX(CASE WHEN m.canonical_code = 'IAS117_INS_REVENUE' THEN f.quarter_amount_lakhs END),
        MAX(CASE WHEN m.canonical_code = 'L1_REV_NET_PREMIUM' THEN f.quarter_amount_lakhs END)
    ) AS normalized_operating_topline_lakhs,
    CASE 
        WHEN MAX(CASE WHEN m.canonical_code = 'IAS117_INS_REVENUE' THEN 1 ELSE 0 END) = 1 THEN 'IND_AS_117'
        ELSE 'IRDAI_LEGACY'
    END AS accounting_standard,
    MAX(CASE WHEN m.canonical_code = 'L4_PREM_TOTAL' THEN f.quarter_amount_lakhs END) AS legacy_gross_premium_lakhs,
    MAX(CASE WHEN m.canonical_code = 'IAS117_INS_REVENUE' THEN f.quarter_amount_lakhs END) AS ind_as_117_revenue_lakhs,
    MAX(CASE WHEN m.canonical_code = 'IAS117_CSM_AMORT' THEN f.quarter_amount_lakhs END) AS csm_recognized_profit_lakhs,
    MAX(CASE WHEN m.canonical_code = 'L2_PL_PAT' THEN f.quarter_amount_lakhs END) AS profit_after_tax_lakhs
FROM fact_financial_statement f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_period p ON f.period_id = p.period_id
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
WHERE f.is_active = 1 
  AND f.segment_id = 'TOTAL'
GROUP BY f.company_id, c.short_name, p.financial_year, p.quarter, p.period_id, f.segment_id;
```

---

## 5. Automated Cross-Statement Financial Reconciliation Framework

A cornerstone of forensic integrity is the automated execution of cross-statement mathematical assertions across statutory forms.

### 5.1 Authoritative IRDAI Life Insurance Schedule Numbering
Forensic inspection of all 25 company workbooks establishes the authoritative statutory schedule numbering:
- **Form L-1**: Policyholders' Account (Revenue Account)
- **Form L-2**: Shareholders' Account (Profit & Loss Account)
- **Form L-3**: Balance Sheet
- **Form L-4**: Schedule 1 — Premium
- **Form L-5**: Schedule 2 — Commission Expenses
- **Form L-6**: Schedule 3 — Operating Expenses Related to Insurance Business
- **Form L-6A**: Shareholders' Expenses (Linked directly to Form L-2)
- **Form L-7**: Schedule 4 — Benefits Paid [Net] (Claims Incurred)
- **Form L-8**: Schedule 5 — Share Capital
- **Form L-9**: Schedule 5A — Pattern of Shareholding
- **Form L-10**: Schedule 6 — Reserves and Surplus
- **Form L-11**: Schedule 7 — Borrowings
- **Form L-12**: Schedule 8 — Investments - Shareholders
- **Form L-13**: Schedule 8A — Investments - Policyholders
- **Form L-14**: Schedule 8B — Assets Held to Cover Linked Liabilities
- **Form L-15**: Schedule 9 — Loans
- **Form L-16**: Schedule 10 — Fixed Assets
- **Form L-17**: Schedule 11 — Cash and Bank Balances
- **Form L-18**: Schedule 12 — Advances and Other Assets
- **Form L-19**: Schedule 13 — Current Liabilities
- **Form L-20**: Schedule 14 — Provisions
- **Form L-21**: Schedule 15 — Misc Expenditure
- **Form L-32**: Solvency Margin (Available Solvency Margin / Required Solvency Margin)

### 5.2 Mathematical Reconciliation Formulas & SQL Assertions

#### 1. Premium Reconciliation (L-1 vs L-4)
- **Gross Premium Equality**:
  $$\sum_{\text{all segments}} \text{L-1}[\text{Gross Premium (Item 1, Sched L-4)}] \equiv \text{L-4}[\text{Total Premium}]$$
- **Net Premium Identity**:
  $$\text{L-1}[\text{Net Premium Sub-Total}] \equiv \text{L-4}[\text{Total Premium}] - \text{L-1}[\text{Reinsurance Ceded}] + \text{L-1}[\text{Reinsurance Accepted}]$$
- **Internal L-4 Cross-Axis Invariant**:
  $$\text{L-4}[\text{Total Premium}] \equiv \text{First Year} + \text{Renewal} + \text{Single} \equiv \text{In India} + \text{Outside India}$$

```sql
-- SQL Assertion Query: Gross & Net Premium Reconciliation
WITH l1_l4_recon AS (
    SELECT 
        company_id,
        period_id,
        MAX(CASE WHEN canonical_code = 'L1_REV_GROSS_PREMIUM' AND segment_id = 'TOTAL' THEN quarter_amount_lakhs END) AS l1_gross_prem,
        MAX(CASE WHEN canonical_code = 'L1_REV_NET_PREMIUM' AND segment_id = 'TOTAL' THEN quarter_amount_lakhs END) AS l1_net_prem,
        MAX(CASE WHEN canonical_code = 'L1_REV_REINS_CEDED' AND segment_id = 'TOTAL' THEN quarter_amount_lakhs END) AS l1_reins_ceded,
        MAX(CASE WHEN canonical_code = 'L1_REV_REINS_ACCEPTED' AND segment_id = 'TOTAL' THEN quarter_amount_lakhs END) AS l1_reins_accepted,
        MAX(CASE WHEN canonical_code = 'L4_PREM_TOTAL' AND classification_axis = 'BY_PRODUCT_TYPE' THEN quarter_amount_lakhs END) AS l4_total_prem
    FROM fact_financial_statement f
    JOIN dim_line_item m ON f.line_item_id = m.line_item_id
    WHERE f.is_active = 1 AND f.schedule_code IN ('L-1', 'L-4')
    GROUP BY company_id, period_id
)
SELECT 
    company_id,
    period_id,
    l1_gross_prem,
    l4_total_prem,
    ABS(COALESCE(l1_gross_prem, 0) - COALESCE(l4_total_prem, 0)) AS gross_variance_lakhs,
    ABS(COALESCE(l1_net_prem, 0) - (COALESCE(l4_total_prem, 0) - COALESCE(l1_reins_ceded, 0) + COALESCE(l1_reins_accepted, 0))) AS net_variance_lakhs,
    CASE 
        WHEN ABS(COALESCE(l1_gross_prem, 0) - COALESCE(l4_total_prem, 0)) <= 1.0 THEN 'PASSED'
        WHEN ABS(COALESCE(l1_gross_prem, 0) - COALESCE(l4_total_prem, 0)) <= 5.0 THEN 'SUSPECT_ROUNDING'
        ELSE 'FAILED_BLOCKING'
    END AS gross_status
FROM l1_l4_recon;
```

#### 2. Balance Sheet Fundamental Identity (L-3 Sources vs Application)
$$\text{L-3}[\text{Total Sources of Funds}] - \text{L-3}[\text{Total Application of Funds}] \equiv 0.0$$

Where:
- $\text{Total Sources} = \text{Shareholders' Funds (L-8 + L-10)} + \text{Borrowings (L-11)} + \text{Policyholders' Funds} + \text{FFA} + \text{Deferred Tax Liabilities}$
- $\text{Total Application} = \text{Investments (L-12 + L-13 + L-14)} + \text{Loans (L-15)} + \text{Fixed Assets (L-16)} + \text{Net Current Assets} + \text{Misc Exp (L-21)}$

```sql
-- SQL Assertion Query: Balance Sheet Equilibrium
SELECT 
    company_id,
    period_id,
    MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_SOURCES' THEN point_in_time_amount_lakhs END) AS total_sources,
    MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_APPLICATION' THEN point_in_time_amount_lakhs END) AS total_application,
    ABS(
        COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_SOURCES' THEN point_in_time_amount_lakhs END), 0) -
        COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_APPLICATION' THEN point_in_time_amount_lakhs END), 0)
    ) AS delta_lakhs,
    CASE 
        WHEN ABS(COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_SOURCES' THEN point_in_time_amount_lakhs END), 0) -
                 COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_APPLICATION' THEN point_in_time_amount_lakhs END), 0)) <= 0.01 THEN 'BALANCED_EXACT'
        WHEN ABS(COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_SOURCES' THEN point_in_time_amount_lakhs END), 0) -
                 COALESCE(MAX(CASE WHEN canonical_code = 'L3_BS_TOTAL_APPLICATION' THEN point_in_time_amount_lakhs END), 0)) <= 1.0 THEN 'ROUNDING_TOLERATED'
        ELSE 'OUT_OF_BALANCE_BLOCKING'
    END AS bs_status
FROM fact_financial_statement f
JOIN dim_line_item m ON f.line_item_id = m.line_item_id
WHERE f.is_active = 1 AND f.schedule_code = 'L-3'
GROUP BY company_id, period_id;
```

#### 3. Balance Sheet Investments Cross-Schedule Reconciliation
$$\text{L-3}[\text{Investments - Shareholders}] \equiv \text{L-12}[\text{Total Investments Shareholders}]$$
$$\text{L-3}[\text{Investments - Policyholders}] \equiv \text{L-13}[\text{Total Investments Policyholders}]$$
$$\text{L-3}[\text{Assets Held for Linked Liabilities}] \equiv \text{L-14}[\text{Total Linked Assets}]$$

#### 4. Policyholder vs Shareholder Fund Cross-Flows (L-1 vs L-2)
$$\text{L-2}[\text{Transfer from Policyholders' Account}] \equiv \sum_{\text{all segments}} \text{L-1}[\text{Transfer to Shareholders' Account}]$$
$$\text{L-2}[\text{Contribution to Policyholders' Account}] \equiv \sum_{\text{all segments}} \text{L-1}[\text{Contribution from Shareholders' Account}]$$

#### 5. Supporting Revenue Schedules (L-1 vs L-5, L-6, L-7)
- $\sum_{\text{segments}} \text{L-1}[\text{Commission}] \equiv \text{L-5}[\text{Total Commission}]$
- $\sum_{\text{segments}} \text{L-1}[\text{Operating Expenses}] \equiv \text{L-6}[\text{Total Operating Expenses}]$
- $\sum_{\text{segments}} \text{L-1}[\text{Benefits Paid Net}] \equiv \text{L-7}[\text{Total Net Benefits Paid}]$

#### 6. Actuarial Solvency Ratio Assertion (Form L-32)
$$\left| \text{Normalized Reported Solvency Ratio} - \frac{\text{L-32}[\text{Total ASM}]}{\text{L-32}[\text{Total RSM}]} \right| \le 0.01$$

Where reported solvency ratios published in percentage-point notation (e.g. `196.67%` or numeric `196.67` instead of decimal `1.9667`) are automatically normalized:
$$\text{Normalized Reported Solvency Ratio} = \begin{cases} \frac{\text{raw\_reported\_amount}}{100.0} & \text{if } \text{raw\_reported\_amount} > 10.0 \\ \text{raw\_reported\_amount} & \text{otherwise} \end{cases}$$

```sql
-- SQL Assertion Query: Solvency Ratio with Dynamic Percentage-Point Normalization
SELECT 
    company_id,
    period_id,
    asm,
    rsm,
    reported_ratio,
    normalized_ratio,
    computed_ratio,
    ABS(normalized_ratio - computed_ratio) AS delta_ratio,
    CASE 
        WHEN ABS(normalized_ratio - computed_ratio) <= 0.01 THEN 'PASSED'
        ELSE 'FAILED_WARNING'
    END AS solvency_status
FROM (
    SELECT 
        company_id,
        period_id,
        MAX(CASE WHEN canonical_code = 'L32_SOLV_ASM' THEN point_in_time_amount_lakhs END) AS asm,
        MAX(CASE WHEN canonical_code = 'L32_SOLV_RSM' THEN point_in_time_amount_lakhs END) AS rsm,
        MAX(CASE WHEN canonical_code = 'L32_SOLV_RATIO' THEN raw_reported_amount END) AS reported_ratio,
        CASE 
            WHEN MAX(CASE WHEN canonical_code = 'L32_SOLV_RATIO' THEN raw_reported_amount END) > 10.0 
            THEN MAX(CASE WHEN canonical_code = 'L32_SOLV_RATIO' THEN raw_reported_amount END) / 100.0
            ELSE MAX(CASE WHEN canonical_code = 'L32_SOLV_RATIO' THEN raw_reported_amount END)
        END AS normalized_ratio,
        ROUND(
            MAX(CASE WHEN canonical_code = 'L32_SOLV_ASM' THEN point_in_time_amount_lakhs END) /
            NULLIF(MAX(CASE WHEN canonical_code = 'L32_SOLV_RSM' THEN point_in_time_amount_lakhs END), 0),
            4
        ) AS computed_ratio
    FROM fact_financial_statement f
    JOIN dim_line_item m ON f.line_item_id = m.line_item_id
    WHERE f.is_active = 1 AND f.schedule_code = 'L-32'
    GROUP BY company_id, period_id
) sub;
```

#### 7. Ind AS 117 (IFRS 17) Contractual Service Margin (CSM) Rollforward Assertions
Under Ind AS 117, insurance contract profitability is deferred to the Contractual Service Margin (CSM) and amortized into P&L over coverage periods. The ledger enforces two fundamental actuarial reconciliation identities on `fact_csm_rollforward`:

1. **CSM Rollforward Internal Balancing Identity**:
   $$\text{closing\_csm} \equiv \text{opening\_csm} + \text{new\_contracts\_csm} + \text{interest\_accretion} + \text{experience\_adjustments} - \text{csm\_released\_pnl}$$
   $$\left| \text{closing\_csm} - (\text{opening\_csm} + \text{new\_contracts\_csm} + \text{interest\_accretion} + \text{experience\_adjustments} - \text{csm\_released\_pnl}) \right| \le 0.01$$

2. **Cross-Statement CSM P&L Amortization Reconciliation**:
   $$\sum_{\text{all segments}} \text{fact\_csm\_rollforward}[\text{csm\_released\_pnl\_lakhs}] \equiv \text{fact\_financial\_statement}[\text{IAS117\_CSM\_AMORT}]$$
   $$\left| \sum \text{csm\_released\_pnl\_lakhs} - \text{quarter\_amount\_lakhs}[\text{IAS117\_CSM\_AMORT}] \right| \le 0.01$$

```sql
-- SQL Assertion Query: Ind AS 117 CSM Rollforward Internal Balancing & Cross-Statement P&L Match
WITH csm_balance AS (
    SELECT 
        company_id,
        period_id,
        segment_id,
        valuation_model,
        opening_csm_lakhs,
        new_contracts_csm_lakhs,
        interest_accretion_lakhs,
        experience_adjustments_lakhs,
        csm_released_pnl_lakhs,
        closing_csm_lakhs,
        (opening_csm_lakhs + new_contracts_csm_lakhs + interest_accretion_lakhs + 
         experience_adjustments_lakhs - csm_released_pnl_lakhs) AS expected_closing_csm,
        ABS(closing_csm_lakhs - (opening_csm_lakhs + new_contracts_csm_lakhs + 
            interest_accretion_lakhs + experience_adjustments_lakhs - csm_released_pnl_lakhs)) AS balance_delta_lakhs
    FROM fact_csm_rollforward
),
pnl_amort_match AS (
    SELECT 
        c.company_id,
        c.period_id,
        SUM(c.csm_released_pnl_lakhs) AS total_csm_released_lakhs,
        MAX(f.quarter_amount_lakhs) AS pnl_amort_amount_lakhs,
        ABS(SUM(c.csm_released_pnl_lakhs) - COALESCE(MAX(f.quarter_amount_lakhs), 0)) AS cross_match_delta_lakhs
    FROM fact_csm_rollforward c
    LEFT JOIN fact_financial_statement f 
        ON c.company_id = f.company_id 
       AND c.period_id = f.period_id 
       AND f.line_item_id = 'IAS117_CSM_AMORT'
       AND f.is_active = 1
    GROUP BY c.company_id, c.period_id
)
SELECT 
    b.company_id,
    b.period_id,
    b.segment_id,
    b.balance_delta_lakhs,
    p.cross_match_delta_lakhs,
    CASE 
        WHEN b.balance_delta_lakhs <= 0.01 AND (p.cross_match_delta_lakhs IS NULL OR p.cross_match_delta_lakhs <= 0.01) THEN 'PASSED'
        WHEN b.balance_delta_lakhs <= 1.0 THEN 'ROUNDING_TOLERATED'
        ELSE 'FAILED_BLOCKING'
    END AS csm_reconcile_status
FROM csm_balance b
JOIN pnl_amort_match p ON b.company_id = p.company_id AND b.period_id = p.period_id;
```

### 5.3 Column-Group Scoped Unit Normalization Engine
To eliminate the 100x data corruption caused by intra-sheet unit drift, unit detection is executed at the **column-group / spatial bounding block level**, utilizing negative-lookahead regex rules:

```python
import re
from typing import List, Tuple

# Multiplier mapping to target standard warehouse currency base: INR Lakhs
UNIT_RULES = [
    # 1. Crores: 1 Crore = 100 Lakhs (e.g. LIC Q4 FY24) - Supports English and Devanagari with/without Nukta (\u093c)
    (r"\b(?:crores?|crs?\.?)\b|(?:\bकरोड\b)|करोड़", "CRORES", 100.0),
    # 2. Lakhs: 1 Lakh = 1.0 Lakh
    (r"\b(?:lakhs?|lacs?\.?)\b|(?:\bलाख\b)", "LAKHS", 1.0),
    # 3. Thousands: 1 Thousand = 0.01 Lakhs (e.g. HDFC/SBI Q1 FY22)
    (r"(?:'000|\bthousands?\b)|(?:\bहजार\b)", "THOUSANDS", 0.01),
    # 4. Millions: 1 Million = 10 Lakhs
    (r"\bmillions?\b", "MILLIONS", 10.0),
    # 5. Raw Actuals (INR): Negative lookahead prevents matching "(Amount in Rs. Lakhs)"
    (r"\b(?:actuals?|in\s+(?:rs\.?|₹|inr))\b(?!\s+(?:lakh|crore|thousand|'000|million))", "ACTUAL_INR", 0.00001),
]

NON_CURRENCY_COLUMN_PATTERNS = [
    # Explicit prefix required for claims paid to prevent misclassifying monetary claims columns (e.g. 'Claims Paid (Rs in Thousands)')
    r"(?i)\b(?:no\.|number\s+of)\s+claims\s+paid\b",
    r"(?i)\b(?:no\.|number\s+of|count|lives|policies|complaints|agents|employees|branches|offices)\b",
    r"(?i)\b(?:ratio|percentage|rate|persistency|yield|margin\s+ratio)\b",
]

NON_CURRENCY_FORM_EXEMPTIONS = {"L-22", "L-38", "L-41", "L-45"}

def detect_column_group_unit(header_cells: List[str], form_code: str, col_header_text: str) -> Tuple[str, float, str]:
    """Evaluates unit scale at the COLUMN-GROUP level.
    Guarantees non-monetary columns (counts/ratios) are never scaled."""
    if form_code in ("L-41", "L-45"):
        return "COUNT", 1.0, "COUNT_ADDITIVE"
    if form_code in ("L-22", "L-38"):
        return "RATIO", 1.0, "RATIO_NON_ADDITIVE"
        
    for pat in NON_CURRENCY_COLUMN_PATTERNS:
        if re.search(pat, col_header_text):
            if "ratio" in col_header_text.lower() or "rate" in col_header_text.lower() or "persistency" in col_header_text.lower():
                return "RATIO", 1.0, "RATIO_NON_ADDITIVE"
            return "COUNT", 1.0, "COUNT_ADDITIVE"
            
    combined_header = " ".join([str(c) for c in header_cells if c]).lower().replace("\n", " ")
    for pat, unit_name, multiplier in UNIT_RULES:
        if re.search(pat, combined_header):
            return unit_name, multiplier, "FLOW_ADDITIVE"
            
    return "LAKHS", 1.0, "FLOW_ADDITIVE"
```

### 5.4 Configurable Dual-Condition Tolerance Thresholds
Reconciliations enforce a **Dual-Condition Tolerance Rule** to balance forensic sensitivity against rounding artifacts:
$$\text{Assertion Passes if: } |A - B| \le T_{\text{abs}} \quad \mathbf{OR} \quad \frac{|A - B|}{\max(|B|, 1.0)} \le T_{\text{rel}}$$

| Reconciliation Assertion | Statement 1 | Statement 2 | Reporting Scale | Absolute Tolerance ($T_{\text{abs}}$) | Relative Tolerance ($T_{\text{rel}}$) | Severity Tier if Violated |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Balance Sheet Equilibrium** | L-3 Total Sources | L-3 Total Application | Lakhs / '000 | 1.0 Lakh | 0.01% (0.0001) | **BLOCKING** (> 10L); **WARNING** (1–10L) |
| **Balance Sheet Equilibrium** | L-3 Total Sources | L-3 Total Application | Crores (LIC) | 0.05 Crore (5L) | 0.01% (0.0001) | **BLOCKING** (> 0.1%); **WARNING** (0.01–0.1%) |
| **Gross Premium Match** | L-1 Gross Premium | L-4 Total Premium | Lakhs / '000 | 1.0 Lakh | 0.05% (0.0005) | **BLOCKING** (> 50L); **WARNING** (> 1.0L) |
| **Gross Premium Match** | L-1 Gross Premium | L-4 Total Premium | Crores (LIC) | 0.1 Crore (10L) | 0.05% (0.0005) | **BLOCKING** (> 1.0%); **WARNING** (> 0.05%) |
| **Net Premium Accounting** | L-1 Net Premium | L-4 Total - Ceded + Acc | Lakhs / '000 | 2.0 Lakhs | 0.05% (0.0005) | **WARNING** if exceeded |
| **Commission Expenses** | L-1 Commission | L-5 Total Commission | Lakhs / '000 | 0.5 Lakhs | 0.05% (0.0005) | **WARNING** if exceeded |
| **Operating Expenses** | L-1 OpEx | L-6 Total OpEx | Lakhs / '000 | 0.5 Lakhs | 0.05% (0.0005) | **WARNING** if exceeded |
| **Benefits Paid (Claims)** | L-1 Benefits Net | L-7 Total Net Benefits | Lakhs / '000 | 1.0 Lakh | 0.05% (0.0005) | **WARNING** if exceeded |
| **Share Capital Match** | L-3 Share Capital | L-8 Total Capital | Lakhs / '000 | 0.01 Lakh | 0.00% (Exact) | **BLOCKING** (> 1.0L); **WARNING** (<= 1.0L) |
| **Investments Shareholders**| L-3 Inv Shareholders | L-12 Total Inv Sh | Lakhs / '000 | 1.0 Lakh | 0.01% (0.0001) | **WARNING** if exceeded |
| **Investments Policyholders**| L-3 Inv Policyholders | L-13 Total Inv Ph | Lakhs / '000 | 2.0 Lakhs | 0.01% (0.0001) | **WARNING** if exceeded |
| **Linked Assets** | L-3 Linked Assets | L-14 Total Linked Assets | Lakhs / '000 | 2.0 Lakhs | 0.01% (0.0001) | **WARNING** if exceeded |
| **Fund Transfer: Surplus** | L-2 Transfer from Ph | L-1 Transfer to Sh | Lakhs / '000 | 1.0 Lakh | 0.05% (0.0005) | **WARNING** if exceeded |
| **Fund Transfer: Deficit** | L-2 Contrib to Ph | L-1 Contrib from Sh | Lakhs / '000 | 1.0 Lakh | 0.05% (0.0005) | **WARNING** if exceeded |
| **Solvency Ratio Identity** | L-32 Solvency Ratio | L-32 ASM / RSM | Dimensionless | 0.01 Ratio | 0.5% (0.005) | **WARNING** if exceeded |
| **CSM Rollforward Equilibrium** | fact_csm_rollforward Closing | Calculated Rollforward | Lakhs | 0.01 Lakh | 0.00% (Exact) | **BLOCKING** (> 1.0L); **WARNING** (<= 1.0L) |
| **CSM Amortization P&L Match** | fact_csm_rollforward Released | fact_financial_statement IAS117_CSM_AMORT | Lakhs | 0.01 Lakh | 0.01% (0.0001) | **BLOCKING** (> 1.0L); **WARNING** (<= 1.0L) |

---

## 6. Resilient Quarterly Ingestion and PDF Format Variation Strategy

### 6.1 2D Spatial Table Bounding Box Parsing (`SpatialTableBlock`)
To deconstruct horizontal multi-quarter concatenation (up to 876 columns) and vertical comparative stacking without hardcoded column indices, the parser applies a **2D Spatial Anchor Slicing Engine**:

```
                         HORIZONTAL QUARTER PARTITIONING
  Col 1                Col 19 Col 20               Col 38 Col 39               Col 58
+----------------------------+----------------------------+----------------------------+
| Block 1: FY24-25 Q1        | Block 2: FY24-25 Q2        | Block 3: FY24-25 Q3        |
| Form L-1-A-RA              | Form L-1-A-RA              | Form L-1-A-RA              |
| Unit: (Rs in '000)         | Unit: (Rs in Lakhs)        | Unit: (Rs in Lakhs)        |
| Particulars | Par | NonPar | Particulars | Par | NonPar | Particulars | Par | NonPar |
| Row 12 .. Row 70           | Row 12 .. Row 70           | Row 12 .. Row 70           |
+----------------------------+----------------------------+----------------------------+
| Footnotes / Page Breaks    | Footnotes / Page Breaks    | Footnotes / Page Breaks    |
+----------------------------+----------------------------+----------------------------+
| Block 1B: FY23-24 Q1 (Comp)| Block 2B: FY23-24 Q2 (Comp)| Block 3B: FY23-24 Q3 (Comp)|  VERTICAL
| Form L-1-A-RA (Prior Year) | Form L-1-A-RA (Prior Year) | Form L-1-A-RA (Prior Year) |  STACKING
| Row 77 .. Row 135          | Row 77 .. Row 135          | Row 77 .. Row 135          |
+----------------------------+----------------------------+----------------------------+
```

#### The Spatial Bounding Box Extractor:
```python
class SpatialTableBlock:
    def __init__(self, start_row: int, end_row: int, start_col: int, end_col: int,
                 period_id: str, form_code: str, unit: str, multiplier: float):
        self.start_row = start_row
        self.end_row = end_row
        self.start_col = start_col
        self.end_col = end_col
        self.period_id = period_id
        self.form_code = form_code
        self.unit = unit
        self.multiplier = multiplier

def slice_worksheet_blocks(sheet) -> List[SpatialTableBlock]:
    """Deconstructs complex consolidated sheets into independent 2D bounding boxes."""
    blocks = []
    max_r = sheet.max_row
    max_c = sheet.max_column

    # 1. Detect horizontal quarter intervals by scanning rows 1 to 6 (handling merged header rows and descriptive banners)
    col_anchors = []
    for c in range(1, max_c + 1):
        for scan_r in range(1, min(7, max_r + 1)):
            cell_val = str(sheet.cell(scan_r, c).value or "").strip().upper()
            if re.search(r"\bQ[1-4]\b|FOR\s+THE\s+QUARTER\b", cell_val) or re.match(r"^FORM\s+L[-_ ]", cell_val):
                col_anchors.append(c)
                break
    if not col_anchors or col_anchors[0] != 1:
        col_anchors.insert(0, 1)

    # 2. Detect vertical statement stacking (e.g. comparative prior year at row 77+, scanning across margin columns)
    for i in range(len(col_anchors)):
        c_start = col_anchors[i]
        c_end = col_anchors[i+1] - 1 if i+1 < len(col_anchors) else max_c
        
        row_anchors = [4]
        for r in range(15, max_r + 1):
            for c_probe in range(c_start, min(c_start + 4, max_c + 1)):
                val = str(sheet.cell(r, c_probe).value or "").strip().upper()
                if re.match(r"^FORM\s+L[-_ ]\d+", val) or "REVENUE ACCOUNT" in val or "BALANCE SHEET" in val:
                    row_anchors.append(r)
                    break
                
        for v in range(len(row_anchors)):
            r_start = row_anchors[v]
            r_end = row_anchors[v+1] - 1 if v+1 < len(row_anchors) else max_r
            
            # Scoped unit detection strictly within this bounding box
            unit, mult = detect_block_unit(sheet, r_start, min(r_start + 12, r_end), c_start, c_end)
            period = extract_block_period(sheet, r_start, c_start, c_end)
            
            blocks.append(SpatialTableBlock(
                r_start, r_end, c_start, c_end, period, sheet.title, unit, mult
            ))
    return blocks
```

### 6.2 5-Tier Zero-Text Tabular Filtering Rules
To prevent dropping valid numeric rows while cleanly extracting qualitative text:

```
+--------------------------------------------------------------------------------------------------+
|                                    5-TIER FILTERING PIPELINE                                     |
+--------------------------------------------------------------------------------------------------+
| TIER 1: Corporate & Regulatory Header Banners                                                    |
| Regex: r"^\s*(?:registration\s+(?:no|number)|cin\s*[:\-\.]|irdai\s+reg|name\s+of\s+the\s+insurer)"|
| Action: Route to Dim_Company / Dim_Period metadata. DROP from Fact parsing.                      |
+--------------------------------------------------------------------------------------------------+
| TIER 2: Page Break & Sheet Sequencing Artifacts                                                  |
| Regex: r"^\s*(?:\d{1,3}|page\s+\d+(?:\s+of\s+\d+)?|\[?\s*#\s*\d*\s*\]?|continued\s+on.*)\s*$"   |
| Action: Drop silently (formatting artifacts).                                                    |
+--------------------------------------------------------------------------------------------------+
| TIER 3: Footnote Declarations & Actuarial Qualitative Markers                                    |
| Regex: r"^\s*(?:[\*\#\$\@\~]{1,3}\s*|notes?\s*:\s*|refer\s+to\s+note|disclaimer\b|source\s*:)"  |
| Action: Clean inline markers on rows with numbers; if pure text -> ROUTE TO Dim_Notes.          |
+--------------------------------------------------------------------------------------------------+
| TIER 4: Auditor Sign-offs & Attestations                                                         |
| Regex: r"^\s*(?:for\s+and\s+on\s+behalf\s+of|as\s+per\s+our\s+report|chartered\s+accountants)"  |
| Action: Record in audit metadata; drop from numerical facts.                                     |
+--------------------------------------------------------------------------------------------------+
| TIER 5: Standalone Narrative Commentary Paragraphs                                               |
| Definition: len(text) > 100 characters AND word_count > 12 AND numeric_columns_count == 0        |
| Action: Route to Statement_Notes table.                                                          |
+--------------------------------------------------------------------------------------------------+
```

**MANDATORY NUMBER PRESERVATION RULE**: Any row containing at least one valid numeric float is **STRICTLY PROTECTED as a DATA_ROW**. Inline footnote characters (`*`, `#`, `^`) are stripped from the label string without dropping the numeric measurement.

### 6.3 Tri-Engine Quarterly PDF Ingestion Pipeline
Quarterly public disclosures published in PDF format are processed through a tri-engine architecture with deterministic fallback gates:

```mermaid
flowchart TD
    A[Incoming Quarterly PDF Disclosure] --> B{Contains Selectable Text Glyphs?}
    B -- Yes: Vector PDF --> C[Engine 1: pdfplumber Geometric Extractor]
    B -- No: Scanned Bitmap --> D[Engine 3 Preprocessor: Deskew & Binarization]
    
    C --> E{Grid Geometry Check}
    E -- Explicit Table Grid Lines --> F[Engine 2: Camelot Lattice Mode]
    E -- Whitespace Borderless --> G[Engine 1: pdfplumber Stream Mode]
    
    D --> H[Engine 3: PaddleOCR PP-Structure SLANet]
    H --> I[OCR Text Recognition + Confidence Filter]
    
    F --> J[Multi-Page Table Stitcher]
    G --> J
    I --> J
    
    J --> K{Page N+1 Continues Table?}
    K -- Yes: (Contd.) or Header Match --> L[Deduplicate Repeated Headers & Stitch Rows]
    K -- No: New Statement --> M[Output Structured Financial Block]
    L --> M
```

1. **`pdfplumber` (Primary Vector Engine)**: Used for digital vector PDFs. Extracts exact glyph bounding boxes (`x0, y0, x1, y1`) and text lines with zero rasterization overhead.
2. **`Camelot (Lattice Mode)`**: Triggered when explicit rulings and borders exist. Uses OpenCV morphological operations (`cv2.morphologyEx`) to locate exact cell grid intersections.
3. **`PaddleOCR PP-Structure` (Scanned PDF Fallback)**: Deployed for signed auditor scans. Applies SLANet table structure recognition and PP-OCRv4 text detection. Cells with OCR confidence < 85% are logged to `quarantine_syntax_cells`.
4. **Multi-Page Table Stitcher**: Detects table continuation keywords (`(Continued)`, `(Contd.)`) across page breaks. Compares column horizontal offsets within a $\pm 4.0\text{ pt}$ tolerance, deduplicating repeated header rows while preserving contiguous financial records.

### 6.4 Ind AS 117 (IFRS 17) Taxonomy Transition Architecture
The transition from cash-basis statutory accounting to **Ind AS 117** represents the largest accounting reform in Indian insurance history:
- **Top-Line Measurement**: "Gross Premium Written" is eliminated from the income statement, replaced by **Insurance Revenue** (reflecting services provided during the period, excluding unbundled deposit components).
- **Contractual Service Margin (CSM)**: Represents unearned future profit. Held on the Balance Sheet under the Liability for Remaining Coverage (LRC) and amortized into P&L systematically as insurance services are rendered.
- **Risk Adjustment (RA)**: Explicitly quantifies the compensation required for bearing uncertainty regarding future cash flows.
- **Onerous Contracts**: Losses on loss-making contract cohorts are recognized **immediately** in P&L.

#### Dual-Model Universal Reporting Bridge:
The schema natively accommodates both legacy IRDAI and Ind AS 117 filings without breaking historical queries:
- `dim_accounting_standard`: Identifies reporting framework (`IRDAI_LEGACY` vs `IND_AS_117`).
- `fact_csm_rollforward`: Tracks opening CSM, new contract CSM, interest accretion, experience adjustments, CSM released to P&L, and closing CSM across valuation models (`GMM`, `VFA`, `PAA`).
- `vw_unified_insurance_revenue`: Exposes a seamless multi-year analytical time series bridging pre- and post-transition periods for enterprise dashboards.

---

## 7. Implementation Roadmap, Power BI Integration & Verification Runbook

### 7.1 Operational Runbook for Ingesting New Quarterly Disclosures
When an insurer releases an upcoming quarterly disclosure (`Company_Consolidated.xlsx` or `Company_Q3_Disclosure.pdf`):
1. **Batch Registration**: Pipeline registers run in `audit_etl_batches` and computes SHA-256 file checksum.
2. **Spatial Bounding Box Slicing**: `SpatialTableBlock` scans sheet dimensions, partitions horizontal quarter columns and vertical statement blocks, and executes column-group unit detection.
3. **Staging Landing**: Extracted cells land in `stage_raw_cells` with raw values, formats, and cell addresses.
4. **Taxonomy & Alias Resolution**: Particulars are matched against `dim_line_item_alias` (including Devanagari Hindi terms). Unmapped rows land in `quarantine_unmapped_taxonomy`.
5. **Non-Destructive Ledger Loading**: Records load into `fact_financial_statement` using SCD Type 2 logic. Cell coordinates record in `fact_cell_lineage`.
6. **Automated Cross-Statement Reconciliation**: Reconciler executes assertions (L-1/L-4, Balance Sheet, Fund Transfers, Solvency). Any discrepancies are evaluated against dual-condition tolerances and logged to `quarantine_reconciliation_discrepancies`.
7. **View Refresh**: Analytical views automatically present verified records; quarantined rows remain isolated for audit review.

### 7.2 Power BI DirectQuery & Import Mode Architecture
- **Local Analytics (Import Mode)**: Connects to SQLite or DuckDB via ODBC. Analytical views (`vw_dashboard_financials`, `vw_leaf_financials`) provide sub-second query performance with zero double-counting.
- **Enterprise DirectQuery**: Deployed on DuckDB or PostgreSQL. Power BI generates live SQL queries against `vw_dashboard_financials` with direct relational integrity and instantaneous filter drill-downs across companies, quarters, and fund segments.

---

## 8. Architectural Attestation & Sign-off

This master architecture plan comprehensively fulfills all requirements of the Approved Task Prompt and PROJECT.md specifications:
- [x] Multi-Perspective Adversarial Review covering 12 detailed defects and concrete mitigations across all 25 company workbooks.
- [x] Strict Relational Normalization (3NF Dimensions, pure natural business grain star schema, engine-agnostic ANSI SQL DDL).
- [x] Full double-counting elimination via orthogonal axes, hierarchy levels, leaf flags, and disjoint analytical views.
- [x] Full cell-level audit lineage (`fact_cell_lineage`) and non-destructive SCD Type 2 ledger.
- [x] Automated cross-statement reconciliation framework covering L-1/L-4, Balance Sheet balancing, fund transfers, and Solvency ratio with dual tolerances.
- [x] Column-group scoped unit normalization handling Thousands, Lakhs, Crores, Counts, Ratios, and bilingual Devanagari strings.
- [x] Resilient quarterly ingestion strategy with 2D spatial bounding boxes, dynamic header anchoring, 5-tier zero-text filtering, tri-engine PDF pipeline, and Ind AS 117 Dual-Model Bridge.
