with open("src/db/schema.py", "r", encoding="utf-8") as f:
    content = f.read()

curated_ddl = """

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

# Insert curated_ddl right before the closing triple quotes of SQL_DDL
assert '"""' in content
# Find the last triple quotes
idx = content.rfind('"""')
new_content = content[:idx] + curated_ddl + content[idx:]

with open("src/db/schema.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully updated src/db/schema.py")
