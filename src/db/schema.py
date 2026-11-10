"""
ANSI SQL DDL and Views for Life Insurance Data Warehouse (v3.0)
"""

SQL_DDL = """
-- Dimension Tables
CREATE TABLE dim_company (
    company_id VARCHAR(32) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100) NOT NULL,
    irda_reg_no VARCHAR(32),
    category VARCHAR(50) DEFAULT 'Private',
    active_status VARCHAR(20) DEFAULT 'Active',
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
    quarter_num SMALLINT NOT NULL,
    quarter_start_date DATE NOT NULL,
    quarter_end_date DATE NOT NULL,
    chronological_sequence INTEGER NOT NULL UNIQUE,
    is_audited SMALLINT DEFAULT 0
);

CREATE TABLE dim_statement_schedule (
    schedule_code VARCHAR(16) PRIMARY KEY,
    schedule_name VARCHAR(255) NOT NULL,
    statement_type VARCHAR(64) NOT NULL,
    is_balance_sheet_schedule SMALLINT DEFAULT 0
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
    is_monetary SMALLINT DEFAULT 1
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
    is_leaf SMALLINT DEFAULT 1,
    is_total SMALLINT DEFAULT 0,
    is_subtotal SMALLINT DEFAULT 0,
    normal_balance_sign SMALLINT DEFAULT 1,
    aggregation_type VARCHAR(32) NOT NULL,
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

-- Staging & Audit Run Tracking Layer
CREATE TABLE audit_etl_batches (
    batch_id INTEGER PRIMARY KEY,
    batch_start_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_end_timestamp TIMESTAMP,
    triggered_by VARCHAR(64) DEFAULT 'MANUAL',
    status VARCHAR(32) DEFAULT 'RUNNING',
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

-- Core Financial Fact Layer (Pure Business Grain)
CREATE TABLE fact_financial_statement (
    fact_id INTEGER PRIMARY KEY,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    schedule_code VARCHAR(16) NOT NULL,
    line_item_id VARCHAR(64) NOT NULL,
    segment_id VARCHAR(64) NOT NULL DEFAULT 'TOTAL',
    filing_period_id VARCHAR(32) NOT NULL,
    reporting_basis VARCHAR(32) NOT NULL DEFAULT 'AS_REPORTED_ORIGINAL',
    source_unit_id VARCHAR(32) NOT NULL,
    unit_multiplier NUMERIC(12, 6) NOT NULL,
    raw_reported_amount NUMERIC(18, 4),
    quarter_amount_lakhs NUMERIC(18, 4),
    ytd_amount_lakhs NUMERIC(18, 4),
    point_in_time_amount_lakhs NUMERIC(18, 4),
    is_quarter_derived SMALLINT DEFAULT 0,
    data_quality_status VARCHAR(32) DEFAULT 'VERIFIED',
    statement_version_id INTEGER DEFAULT 1,
    is_active SMALLINT DEFAULT 1,
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

-- Cell-Level Lineage Layer
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
    lineage_role VARCHAR(32) DEFAULT 'PRIMARY_CELL',
    FOREIGN KEY (fact_id) REFERENCES fact_financial_statement(fact_id),
    FOREIGN KEY (stage_cell_id) REFERENCES stage_raw_cells(stage_cell_id)
);

-- Tri-Tier Quarantine Layer
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
    review_status VARCHAR(32) DEFAULT 'PENDING',
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
    severity VARCHAR(16) NOT NULL,
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

-- Specialized Ind AS 117 Bridge Layer
CREATE TABLE fact_csm_rollforward (
    csm_fact_id INTEGER PRIMARY KEY,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    segment_id VARCHAR(64) NOT NULL,
    valuation_model VARCHAR(32) NOT NULL,
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

-- Analytical Views
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


-- Curated Master Table for 64 Standardized Financial Metrics
CREATE TABLE IF NOT EXISTS fact_company_quarterly_metrics (
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    financial_year VARCHAR(16) NOT NULL,
    quarter VARCHAR(8) NOT NULL,
    -- 1) Financial Year Premium (First Year Regular)
    financial_year_premium NUMERIC(18, 4),
    -- 2 & 6) Total Single Premium
    total_single_premium NUMERIC(18, 4),
    -- 3) Renewal Premium
    renewal_premium NUMERIC(18, 4),
    -- 4) Total Individual Premium
    total_individual_premium NUMERIC(18, 4),
    -- 5) Total Group Premium
    total_group_premium NUMERIC(18, 4),
    -- 7) Total Non-Single Premium
    total_non_single_premium NUMERIC(18, 4),
    -- 8) Group Non-Single Premium
    group_non_single_premium NUMERIC(18, 4),
    -- 9) Group Yearly Renewal Premium
    group_yearly_renewal_premium NUMERIC(18, 4),
    -- 10) Individual Single Premium
    individual_single_premium NUMERIC(18, 4),
    -- 11) Individual Non-Single Premium
    individual_non_single_premium NUMERIC(18, 4),
    -- 12) Group Single Premium
    group_single_premium NUMERIC(18, 4),
    -- 13) Gross Written Premium (FY + Single + Renewal)
    gross_written_premium NUMERIC(18, 4),
    -- 14) Average Premium Growth in % vs Prior Year Same Quarter
    avg_premium_growth_pct NUMERIC(8, 4),
    -- 15) Policy Sales Growth in % vs Prior Year Same Quarter
    policy_sales_growth_pct NUMERIC(8, 4),
    -- 16) Number of Claims
    number_of_claims INTEGER,
    -- 17) Death Claims Amount
    death_claims_amount NUMERIC(18, 4),
    -- 18) Maturity Amount
    maturity_amount NUMERIC(18, 4),
    -- 19) Total Claim Amount (Death + Maturity)
    total_claim_amount NUMERIC(18, 4),
    -- 20) Commission Expense
    comm_expense NUMERIC(18, 4),
    -- 21) Operating Expenses (Opex)
    opex_expense NUMERIC(18, 4),
    -- 22) Total Expense (Comm + Opex)
    total_expense NUMERIC(18, 4),
    -- 23) CAGR %
    cagr_pct NUMERIC(8, 4),
    -- 24) Total Premium = Total Individual + Total Group
    total_premium NUMERIC(18, 4),
    -- 25) Total Sum Assured (in Lakhs)
    total_sum_assured NUMERIC(18, 4),
    -- 26) Average Sum Assured Growth in % vs Prior Year
    avg_sum_assured_growth_pct NUMERIC(8, 4),
    -- 27) Total Policies
    total_policies INTEGER,
    -- 28) Average Ticket Size / Avg of Policies (in INR)
    avg_ticket_size_inr NUMERIC(18, 4),
    -- 29) Number of Lives Covered Under Group Schemes
    group_lives_covered INTEGER,
    -- 30) Market Share % for Sum Assured, Premium, and Policies
    market_share_premium_pct NUMERIC(8, 4),
    market_share_sum_assured_pct NUMERIC(8, 4),
    market_share_policies_pct NUMERIC(8, 4),
    -- 31) Business Profit (Policyholders' Surplus / Deficit)
    business_profit NUMERIC(18, 4),
    -- 32) Profit Before Tax and Profit After Tax
    profit_before_tax NUMERIC(18, 4),
    profit_after_tax NUMERIC(18, 4),
    -- 33) AUM CAGR %
    aum_cagr NUMERIC(8, 4),
    -- 34) Linked and Non-Linked AUM
    linked_aum NUMERIC(18, 4),
    non_linked_aum NUMERIC(18, 4),
    -- 35) Solvency Ratio
    solvency_ratio NUMERIC(8, 4),
    -- 36) Policy Sales Growth for Group and Individual Policies Separately
    group_policy_growth_pct NUMERIC(8, 4),
    individual_policy_growth_pct NUMERIC(8, 4),
    -- 37) Surrenders / Withdrawals
    surrenders NUMERIC(18, 4),
    -- 38) Conservation Ratio %
    conservation_ratio NUMERIC(8, 4),
    -- 39) Total Complaints
    total_complaints INTEGER,
    -- 40) Total Number of Policies (NOP)
    total_nop INTEGER,
    -- 41) Persistency Ratios: 13th to 61st Month (Count & Premium)
    persistency_13m_count NUMERIC(8, 4),
    persistency_13m_prem NUMERIC(8, 4),
    persistency_25m_count NUMERIC(8, 4),
    persistency_25m_prem NUMERIC(8, 4),
    persistency_37m_count NUMERIC(8, 4),
    persistency_37m_prem NUMERIC(8, 4),
    persistency_49m_count NUMERIC(8, 4),
    persistency_49m_prem NUMERIC(8, 4),
    persistency_61m_count NUMERIC(8, 4),
    persistency_61m_prem NUMERIC(8, 4),
    -- 42) Different Sales Business Channels for Premium
    channel_agency_prem NUMERIC(18, 4),
    channel_banca_prem NUMERIC(18, 4),
    channel_broker_prem NUMERIC(18, 4),
    channel_direct_prem NUMERIC(18, 4),
    channel_web_aggregator_prem NUMERIC(18, 4),
    channel_other_prem NUMERIC(18, 4),
    -- 43) Geographical Summary (detailed breakdown in fact_geographical_distribution)
    geographical_summary TEXT,
    -- 44) Major Banking Partners
    major_banking_partners TEXT,
    -- 45) Company Top Products
    company_top_products TEXT,
    -- 46) Number of Banca Partners
    number_banca_partners INTEGER,
    -- 47) Number of Banca Branches
    number_banca_branches INTEGER,
    -- 48) Bank Productivity in INR
    bank_productivity_inr NUMERIC(18, 4),
    -- 49) Number of Offices / Branches of Company
    number_offices_branches INTEGER,
    -- 50) Number of Web Aggregators
    number_web_aggregators INTEGER,
    -- 51) Number of Individual Agents
    number_individual_agents INTEGER,
    -- 52) Agent Productivity in INR
    agent_productivity_inr NUMERIC(18, 4),
    -- 53) Number of Brokers
    number_brokers INTEGER,
    -- 54) Broker Productivity in INR
    broker_productivity_inr NUMERIC(18, 4),
    -- 55) Share Capital and Share Premium
    share_capital NUMERIC(18, 4),
    share_premium NUMERIC(18, 4),
    -- 56) Profit or Loss Carried Forward (negative for loss)
    profit_loss_carried_forward NUMERIC(18, 4),
    -- 57) Net Worth
    net_worth NUMERIC(18, 4),
    -- 58) Average Return on Equity (ROE %)
    roe_pct NUMERIC(8, 4),
    -- 59) Product Mix % (Par %, Non-Par %, Linked %)
    product_mix_pct TEXT,
    -- 60) Latest Channel Wise Product Mix
    channel_product_mix TEXT,
    -- 61) Financial Performance Overview
    financial_performance TEXT,
    -- 62) Embedded Value
    embedded_value NUMERIC(18, 4),
    -- 63) VNB Growth %
    vnb_growth NUMERIC(8, 4),
    -- 64) Company Website Link
    company_website_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, period_id),
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id)
);

-- Dimension/Fact Table for Geographical Distribution (Field 43)
CREATE TABLE IF NOT EXISTS fact_geographical_distribution (
    geo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    region_type VARCHAR(32) NOT NULL, -- 'STATE', 'UNION_TERRITORY', 'NRI', 'TOTAL'
    region_name VARCHAR(100) NOT NULL,
    rural_policies INTEGER DEFAULT 0,
    rural_premium_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    rural_sum_assured_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    urban_policies INTEGER DEFAULT 0,
    urban_premium_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    urban_sum_assured_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    total_policies INTEGER DEFAULT 0,
    total_premium_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    total_sum_assured_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id),
    CONSTRAINT uq_geo_grain UNIQUE (company_id, period_id, region_name)
);

-- Dimension/Fact Table for Persistency Cohorts (Field 41)
CREATE TABLE IF NOT EXISTS fact_persistency_cohorts (
    persistency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    cohort_month VARCHAR(16) NOT NULL, -- '13th', '25th', '37th', '49th', '61st'
    premium_basis_type VARCHAR(32) NOT NULL, -- 'REGULAR_PREMIUM', 'SINGLE_PREMIUM'
    basis_metric VARCHAR(32) NOT NULL, -- 'PREMIUM_PERCENT', 'COUNT_PERCENT'
    persistency_ratio_pct NUMERIC(8, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id),
    CONSTRAINT uq_persistency_grain UNIQUE (company_id, period_id, cohort_month, premium_basis_type, basis_metric)
);

-- Dimension/Fact Table for Intermediary Channels (Field 42)
CREATE TABLE IF NOT EXISTS fact_intermediary_channel_metrics (
    channel_fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(32) NOT NULL,
    period_id VARCHAR(32) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    policies_count INTEGER DEFAULT 0,
    premium_lakhs NUMERIC(18, 4) DEFAULT 0.0,
    intermediary_count INTEGER DEFAULT 0,
    productivity_inr NUMERIC(18, 4) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES dim_company(company_id),
    FOREIGN KEY (period_id) REFERENCES dim_period(period_id),
    CONSTRAINT uq_channel_grain UNIQUE (company_id, period_id, channel_name)
);
"""
