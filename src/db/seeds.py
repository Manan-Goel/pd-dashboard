"""
Seed Data Generator and Master Dimension Population for Life Insurance Warehouse.
Populates standard dimensions:
- dim_reporting_unit
- dim_statement_schedule
- dim_segment
- dim_accounting_standard
- dim_company & dim_company_alias
- dim_period (FY21-22 Q1 to FY25-26 Q4)
- dim_line_item & dim_line_item_alias (Canonical taxonomy for L-1, L-2, L-3, L-4, L-32)
"""

from typing import List, Tuple

REPORTING_UNITS = [
    ("LAKHS", "LAKHS", 1.0, "Lakhs", 1),
    ("THOUSANDS", "THOUSANDS", 0.01, "'000", 1),
    ("CRORES", "CRORES", 100.0, "Crores", 1),
    ("MILLIONS", "MILLIONS", 10.0, "Millions", 1),
    ("BILLIONS", "BILLIONS", 10000.0, "Billions", 1),
    ("ACTUAL_INR", "ACTUAL_INR", 0.00001, "INR", 1),
    ("COUNT", "COUNT", 1.0, "Nos", 0),
    ("PERCENT", "PERCENT", 1.0, "%", 0),
    ("RATIO", "RATIO", 1.0, "Ratio", 0),
]

ACCOUNTING_STANDARDS = [
    ("IRDAI_LEGACY", "IRDAI Legacy Regulatory Accounting Standard", "2000-01-01", "Cash and regulatory accounting basis"),
    ("IND_AS_117", "Indian Accounting Standard 117 (Insurance Contracts)", "2024-04-01", "IFRS 17 equivalent standard"),
]

STATEMENT_SCHEDULES = [
    ("L-1", "Revenue Account (Policyholders' Account)", "REVENUE_ACCOUNT", 0),
    ("L-2", "Profit & Loss Account (Shareholders' Account)", "PROFIT_AND_LOSS", 0),
    ("L-3", "Balance Sheet", "BALANCE_SHEET", 1),
    ("L-4", "Premium Schedule", "SCHEDULE_PREMIUM", 0),
    ("L-5", "Commission Schedule", "SCHEDULE_COMMISSION", 0),
    ("L-6", "Operating Expenses Schedule", "SCHEDULE_EXPENSES", 0),
    ("L-6A", "Commission & Expenses Breakdown Schedule", "SCHEDULE_EXPENSES_BREAKDOWN", 0),
    ("L-7", "Benefits Paid Schedule", "SCHEDULE_BENEFITS", 0),
    ("L-8", "Share Capital Schedule", "SCHEDULE_CAPITAL", 1),
    ("L-9", "Shareholding Pattern Schedule", "SCHEDULE_SHAREHOLDING", 1),
    ("L-9A", "Shareholding Pattern - Indian & Foreign", "SCHEDULE_SHAREHOLDING_SPLIT", 1),
    ("L-10", "Reserves and Surplus Schedule", "SCHEDULE_RESERVES", 1),
    ("L-11", "Borrowings Schedule", "SCHEDULE_BORROWINGS", 1),
    ("L-12", "Investments (Shareholders) Schedule", "SCHEDULE_INVESTMENTS_SH", 1),
    ("L-13", "Investments (Policyholders) Schedule", "SCHEDULE_INVESTMENTS_PH", 1),
    ("L-14", "Investments - Assets to Cover Linked Liabilities", "SCHEDULE_INVESTMENTS_LINKED", 1),
    ("L-14A", "Investments other than Equity & MF", "SCHEDULE_INVESTMENTS_DEBT", 1),
    ("L-15", "Loans Schedule", "SCHEDULE_LOANS", 1),
    ("L-16", "Fixed Assets Schedule", "SCHEDULE_FIXED_ASSETS", 1),
    ("L-17", "Cash and Bank Balances Schedule", "SCHEDULE_CASH", 1),
    ("L-18", "Advances & Other Assets Schedule", "SCHEDULE_ADVANCES", 1),
    ("L-19", "Current Liabilities Schedule", "SCHEDULE_CURRENT_LIABILITIES", 1),
    ("L-20", "Provisions Schedule", "SCHEDULE_PROVISIONS", 1),
    ("L-21", "Miscellaneous Expenditure Schedule", "SCHEDULE_MISC_EXPENDITURE", 1),
    ("L-22", "Analytical Ratios", "DISCLOSURE_RATIOS", 0),
    ("L-23", "Receipts and Payments Account", "CASH_FLOW", 0),
    ("L-24", "Valuation of Net Liabilities", "ACTUARIAL_VALUATION", 1),
    ("L-25", "Geographical Distribution of Business", "OPERATIONAL_GEOGRAPHY", 0),
    ("L-25 (i)", "Geographical Distribution of Business - State-wise", "OPERATIONAL_GEOGRAPHY", 0),
    ("L-25 (ii)", "Geographical Distribution of Business - Tier-wise", "OPERATIONAL_GEOGRAPHY", 0),
    ("L-26", "Investment Assets (Life Insurers)", "INVESTMENTS_SUMMARY", 1),
    ("L-27", "Investments - Unit Linked Business", "INVESTMENTS_LINKED", 1),
    ("L-28", "Statement of NAV of Segregated Funds", "INVESTMENTS_NAV", 1),
    ("L-29", "Details regarding Debt Securities", "INVESTMENTS_DEBT", 1),
    ("L-30", "Related Party Transactions", "DISCLOSURE_RELATED_PARTIES", 0),
    ("L-31", "Board of Directors & Key Management Persons", "GOVERNANCE_KMP", 0),
    ("L-32", "Available Solvency Margin and Solvency Ratio", "SOLVENCY_MARGIN", 0),
    ("L-33", "Non-Performing Assets (NPAs)", "INVESTMENTS_NPA", 1),
    ("L-34", "Statement of Investment and Income on Investment", "INVESTMENTS_INCOME", 0),
    ("L-35", "Statement of Down Graded Investments", "INVESTMENTS_DOWNGRADED", 1),
    ("L-36", "Premium and number of lives covered by policy type", "OPERATIONAL_POLICIES", 0),
    ("L-37", "Business Acquisition through Channels - Group", "CHANNELS_GROUP", 0),
    ("L-38", "Business Acquisition through Channels - Individuals", "CHANNELS_INDIVIDUAL", 0),
    ("L-39", "Data on Settlement of Claims", "OPERATIONAL_CLAIMS_ANNUAL", 0),
    ("L-40", "Quarterly Claims Data", "OPERATIONAL_CLAIMS_QUARTERLY", 0),
    ("L-41", "Grievance Disposal", "OPERATIONAL_GRIEVANCE", 0),
    ("L-42", "Valuation Basis", "ACTUARIAL_BASIS", 0),
    ("L-43", "Voting Activity under Stewardship Code", "STEWARDSHIP_VOTING", 0),
    ("L-44", "Embedded Value", "EMBEDDED_VALUE", 0),
    ("L-45", "Offices and Other Information", "OPERATIONAL_OFFICES", 0),
    ("L-1A", "Revenue Account Supplementary", "REVENUE_ACCOUNT", 0),
    ("L-3S", "Balance Sheet Segmental", "BALANCE_SHEET", 1),
    ("L-4A", "Premium Supplementary", "SCHEDULE_PREMIUM", 0),
    ("L-8A", "Share Capital Supplementary", "SCHEDULE_CAPITAL", 1),
    ("L-9B", "Shareholding Pattern Promoter Details", "SCHEDULE_SHAREHOLDING", 1),
    ("L-10A", "Reserves and Surplus Supplementary", "SCHEDULE_RESERVES", 1),
    ("L-10B", "Reserves Breakdown", "SCHEDULE_RESERVES", 1),
    ("L-27T", "Investments Unit Linked Supplementary", "INVESTMENTS_LINKED", 1),
    ("L-47", "Additional Statutory Disclosure", "OPERATIONAL_DISCLOSURE", 0),
]

SEGMENTS = [
    ("TOTAL", "TOTAL", "Total Business", "ALL_FUNDS", 1),
    ("PAR_LIFE", "PAR_LIFE", "Life", "PARTICIPATING", 10),
    ("PAR_PENSION", "PAR_PENSION", "Pension", "PARTICIPATING", 11),
    ("PAR_VAR", "PAR_VAR", "Variable Insurance", "PARTICIPATING", 12),
    ("NON_PAR_LIFE", "NON_PAR_LIFE", "Life", "NON_PARTICIPATING", 20),
    ("NON_PAR_PENSION", "NON_PAR_PENSION", "Pension", "NON_PARTICIPATING", 21),
    ("NON_PAR_ANNUITY", "NON_PAR_ANNUITY", "Annuity", "NON_PARTICIPATING", 22),
    ("NON_PAR_HEALTH", "NON_PAR_HEALTH", "Health", "NON_PARTICIPATING", 23),
    ("NON_PAR_VAR", "NON_PAR_VAR", "Variable Insurance", "NON_PARTICIPATING", 24),
    ("LINKED_LIFE", "LINKED_LIFE", "Life", "UNIT_LINKED", 30),
    ("LINKED_PENSION", "LINKED_PENSION", "Pension", "UNIT_LINKED", 31),
    ("LINKED_HEALTH", "LINKED_HEALTH", "Health", "UNIT_LINKED", 32),
    ("GROUP", "GROUP", "Group Business", "ALL_FUNDS", 40),
]

COMPANIES = [
    ("ACKO_LIFE", "Acko Life Insurance Limited", "Acko Life", "164", "Private"),
    ("ADITYA_BIRLA_LIFE", "Aditya Birla Sun Life Insurance Company Limited", "Aditya Birla Sun Life", "109", "Private"),
    ("AGEAS_FEDERAL_LIFE", "Ageas Federal Life Insurance Company Limited", "Ageas Federal Life", "135", "Private"),
    ("AVIVA_LIFE", "Aviva Life Insurance Company India Limited", "Aviva Life", "122", "Private"),
    ("AXIS_MAX_LIFE", "Max Life Insurance Company Limited", "Axis Max Life", "104", "Private"),
    ("BAJAJ_LIFE", "Bajaj Allianz Life Insurance Company Limited", "Bajaj Allianz Life", "116", "Private"),
    ("BANDHAN_LIFE", "Bandhan Life Insurance Limited", "Bandhan Life", "138", "Private"),
    ("BHARTI_AXA_LIFE", "Bharti AXA Life Insurance Company Limited", "Bharti AXA Life", "130", "Private"),
    ("CANARA_HSBC_LIFE", "Canara HSBC Life Insurance Company Limited", "Canara HSBC Life", "136", "Private"),
    ("CREDITACCESS_LIFE", "CreditAccess Life Insurance Limited", "CreditAccess Life", "163", "Private"),
    ("EDELWEISS_LIFE", "Edelweiss Tokio Life Insurance Company Limited", "Edelweiss Tokio Life", "147", "Private"),
    ("GENERALI_CENTRAL_LIFE", "Generali Central Life Insurance Limited", "Generali Central Life", "133", "Private"),
    ("GO_DIGIT_LIFE", "Go Digit Life Insurance Limited", "Go Digit Life", "165", "Private"),
    ("HDFC_LIFE", "HDFC Life Insurance Company Limited", "HDFC Life", "101", "Private"),
    ("ICICI_PRUDENTIAL_LIFE", "ICICI Prudential Life Insurance Company Limited", "ICICI Prudential Life", "105", "Private"),
    ("INDIAFIRST_LIFE", "IndiaFirst Life Insurance Company Limited", "IndiaFirst Life", "143", "Private"),
    ("INDUSIND_NIPPON_LIFE", "Nippon Life India Insurance Limited", "IndusInd Nippon Life", "121", "Private"),
    ("KOTAK_LIFE", "Kotak Mahindra Life Insurance Company Limited", "Kotak Mahindra Life", "107", "Private"),
    ("LIC", "Life Insurance Corporation of India", "LIC", "512", "Public PSU"),
    ("PNB_METLIFE", "PNB MetLife India Insurance Company Limited", "PNB MetLife", "117", "Private"),
    ("PRAMERICA_LIFE", "Pramerica Life Insurance Limited", "Pramerica Life", "140", "Private"),
    ("SBI_LIFE", "SBI Life Insurance Company Limited", "SBI Life", "111", "Private"),
    ("SHRIRAM_LIFE", "Shriram Life Insurance Company Limited", "Shriram Life", "128", "Private"),
    ("SUD_LIFE", "Star Union Dai-ichi Life Insurance Company Limited", "SUD Life", "142", "Private"),
    ("TATA_AIA_LIFE", "Tata AIA Life Insurance Company Limited", "Tata AIA Life", "110", "Private"),
]

COMPANY_ALIASES = [
    (1, "HDFC_LIFE", "Exide Life Insurance Company Limited", "2000", "2022"),
    (2, "SBI_LIFE", "Sahara India Life Insurance Company Limited", "2004", "2023"),
    (3, "BANDHAN_LIFE", "Aegon Life Insurance Company Limited", "2008", "2024"),
    (4, "AXIS_MAX_LIFE", "Max Life Insurance Company Limited", "2000", "2024"),
    (5, "AGEAS_FEDERAL_LIFE", "IDBI Federal Life Insurance Company Limited", "2008", "2020"),
    (6, "GENERALI_CENTRAL_LIFE", "Future Generali India Life Insurance Company Limited", "2007", "2022"),
]

def generate_periods():
    """Generates standard calendar quarters for FY2021-22 through FY2026-27."""
    periods = []
    seq = 1
    years = [
        ("FY2021-22", 2021),
        ("FY2022-23", 2022),
        ("FY2023-24", 2023),
        ("FY2024-25", 2024),
        ("FY2025-26", 2025),
        ("FY2026-27", 2026),
    ]
    q_data = [
        ("Q1", 1, "-04-01", "-06-30", 0),
        ("Q2", 2, "-07-01", "-09-30", 0),
        ("Q3", 3, "-10-01", "-12-31", 0),
        ("Q4", 4, "-01-01", "-03-31", 1), # Q4 is audited
    ]
    for fy, yr in years:
        for q_name, q_num, s_dt, e_dt, aud in q_data:
            period_id = f"{fy}_{q_name}"
            actual_yr = yr if q_num != 4 else yr + 1
            start_date = f"{actual_yr if q_num != 4 else yr}{s_dt}"
            end_date = f"{actual_yr}{e_dt}"
            periods.append((period_id, fy, q_name, yr, q_num, start_date, end_date, seq, aud))
            seq += 1
    return periods

LINE_ITEMS = [
    # L-4 Premium Schedule (Product breakdown)
    ("L4_PREM_FIRST_YEAR", "L-4", "L4_PREM_FIRST_YEAR", "First year premiums", "PREMIUM", "BY_PRODUCT_TYPE", "L4_PREM_TOTAL", 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 10),
    ("L4_PREM_RENEWAL", "L-4", "L4_PREM_RENEWAL", "Renewal premiums", "PREMIUM", "BY_PRODUCT_TYPE", "L4_PREM_TOTAL", 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 20),
    ("L4_PREM_SINGLE", "L-4", "L4_PREM_SINGLE", "Single premiums", "PREMIUM", "BY_PRODUCT_TYPE", "L4_PREM_TOTAL", 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 30),
    ("L4_PREM_TOTAL", "L-4", "L4_PREM_TOTAL", "Total Premium", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 40),
    ("L4_PREM_GROSS", "L-4", "L4_PREM_GROSS", "Gross Premium", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 42),
    ("L4_PREM_REINSURANCE_ACCEPTED", "L-4", "L4_PREM_REINSURANCE_ACCEPTED", "Reinsurance Accepted", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 44),
    ("L4_PREM_REINSURANCE_CEDED", "L-4", "L4_PREM_REINSURANCE_CEDED", "Reinsurance Ceded", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 1, 0, 0, -1, "FLOW_ADDITIVE", 46),
    ("L4_PREM_NET", "L-4", "L4_PREM_NET", "Net Premium", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 48),
    # L-4 Geographic breakdown (Secondary axis)
    ("L4_PREM_GEO_INDIA", "L-4", "L4_PREM_GEO_INDIA", "In India", "PREMIUM", "BY_GEOGRAPHY", "L4_PREM_GEO_TOTAL", 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 50),
    ("L4_PREM_GEO_OUTSIDE", "L-4", "L4_PREM_GEO_OUTSIDE", "Outside India", "PREMIUM", "BY_GEOGRAPHY", "L4_PREM_GEO_TOTAL", 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 60),
    ("L4_PREM_GEO_TOTAL", "L-4", "L4_PREM_GEO_TOTAL", "Total Premium (Geographic)", "PREMIUM", "BY_GEOGRAPHY", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 70),

    # L-1 Revenue Account (Policyholders' Account)
    ("L1_REV_GROSS_PREMIUM", "L-1", "L1_REV_GROSS_PREMIUM", "Gross Premium", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 100),
    ("L1_REV_REINSURANCE_CEDED", "L-1", "L1_REV_REINSURANCE_CEDED", "Reinsurance ceded", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, -1, "FLOW_ADDITIVE", 110),
    ("L1_REV_REINSURANCE_ACCEPTED", "L-1", "L1_REV_REINSURANCE_ACCEPTED", "Reinsurance accepted", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 120),
    ("L1_REV_NET_PREMIUM", "L-1", "L1_REV_NET_PREMIUM", "Net Premium Earned", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 130),
    ("L1_REV_INVESTMENT_INCOME", "L-1", "L1_REV_INVESTMENT_INCOME", "Income from Investments", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 140),
    ("L1_REV_PROFIT_LOSS_INVESTMENTS", "L-1", "L1_REV_PROFIT_LOSS_INVESTMENTS", "Profit / Loss on sale of investments", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 145),
    ("L1_REV_OTHER_INCOME", "L-1", "L1_REV_OTHER_INCOME", "Other Income", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 150),
    ("L1_REV_TOTAL_INCOME", "L-1", "L1_REV_TOTAL_INCOME", "Total Income (A)", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 160),
    ("L1_REV_COMMISSION", "L-1", "L1_REV_COMMISSION", "Commission", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 170),
    ("L1_REV_OPERATING_EXPENSES", "L-1", "L1_REV_OPERATING_EXPENSES", "Operating Expenses related to Insurance Business", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 180),
    ("L1_REV_GST_ULIP", "L-1", "L1_REV_GST_ULIP", "Goods and Services Tax on ULIP Charges", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 185),
    ("L1_REV_BENEFITS_PAID", "L-1", "L1_REV_BENEFITS_PAID", "Benefits Paid (Net)", "BENEFITS", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 190),
    ("L1_REV_CHANGE_VALUATION", "L-1", "L1_REV_CHANGE_VALUATION", "Change in valuation of liability in respect of life policies", "PROVISIONS", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 200),
    ("L1_REV_BAD_DEBTS", "L-1", "L1_REV_BAD_DEBTS", "Bad debts written off", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 201),
    ("L1_REV_PROV_DOUBTFUL_DEBTS", "L-1", "L1_REV_PROV_DOUBTFUL_DEBTS", "Provision for doubtful debts", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 202),
    ("L1_REV_PROVISIONS_OTHER", "L-1", "L1_REV_PROVISIONS_OTHER", "Provisions (other than taxation)", "PROVISIONS", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 203),
    ("L1_REV_PROVISION_TAX", "L-1", "L1_REV_PROVISION_TAX", "Provision for tax", "TAX", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 204),
    ("L1_REV_TOTAL_EXPENSES", "L-1", "L1_REV_TOTAL_EXPENSES", "Total Expenses (B)", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 205),
    ("L1_REV_SURPLUS_DEFICIT", "L-1", "L1_REV_SURPLUS_DEFICIT", "Surplus / (Deficit)", "PROFITABILITY", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 210),
    ("L1_REV_TRANSFER_SH", "L-1", "L1_REV_TRANSFER_SH", "Amount transferred to Shareholders' Account", "APPROPRIATION", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 220),

    # L-2 Profit and Loss Account (Shareholders' Account)
    ("L2_PL_TRANSFER_PH", "L-2", "L2_PL_TRANSFER_PH", "Amount transferred from Policyholders' Account", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 300),
    ("L2_PL_INVESTMENT_INCOME", "L-2", "L2_PL_INVESTMENT_INCOME", "Income from Investments (Shareholders)", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 310),
    ("L2_PL_OTHER_INCOME", "L-2", "L2_PL_OTHER_INCOME", "Other Income", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 320),
    ("L2_PL_TOTAL_INCOME", "L-2", "L2_PL_TOTAL_INCOME", "Total (A)", "INCOME", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 330),
    ("L2_PL_EXPENSES", "L-2", "L2_PL_EXPENSES", "Expense other than insurance business", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 340),
    ("L2_PL_BAD_DEBTS", "L-2", "L2_PL_BAD_DEBTS", "Bad debts written off", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 341),
    ("L2_PL_PROV_DOUBTFUL", "L-2", "L2_PL_PROV_DOUBTFUL", "Provision for doubtful debts", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 342),
    ("L2_PL_TOTAL_EXPENSES", "L-2", "L2_PL_TOTAL_EXPENSES", "Total Expenses (B)", "EXPENSES", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 345),
    ("L2_PL_PBT", "L-2", "L2_PL_PBT", "Profit / (Loss) Before Tax", "PROFITABILITY", "PRIMARY_BREAKDOWN", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 350),
    ("L2_PL_PROVISION_TAX", "L-2", "L2_PL_PROVISION_TAX", "Provision for Taxation", "TAX", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 360),
    ("L2_PL_PAT", "L-2", "L2_PL_PAT", "Profit / (Loss) After Tax", "PROFITABILITY", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 370),

    # L-3 Balance Sheet
    ("L3_BS_SHARE_CAPITAL", "L-3", "L3_BS_SHARE_CAPITAL", "Share Capital", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_SOURCES", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 400),
    ("L3_BS_RESERVES", "L-3", "L3_BS_RESERVES", "Reserves and Surplus", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_SOURCES", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 410),
    ("L3_BS_BORROWINGS", "L-3", "L3_BS_BORROWINGS", "Borrowings", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_SOURCES", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 420),
    ("L3_BS_POLICY_LIABILITIES", "L-3", "L3_BS_POLICY_LIABILITIES", "Policy Liabilities", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_SOURCES", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 430),
    ("L3_BS_LINKED_LIABILITIES", "L-3", "L3_BS_LINKED_LIABILITIES", "Provision for Linked Liabilities", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_SOURCES", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 440),
    ("L3_BS_TOTAL_SOURCES", "L-3", "L3_BS_TOTAL_SOURCES", "Total Sources of Funds", "SOURCES_OF_FUNDS", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "POINT_IN_TIME_STOCK", 450),
    ("L3_BS_INVESTMENTS_SH", "L-3", "L3_BS_INVESTMENTS_SH", "Investments - Shareholders", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 460),
    ("L3_BS_INVESTMENTS_PH", "L-3", "L3_BS_INVESTMENTS_PH", "Investments - Policyholders", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 470),
    ("L3_BS_INVESTMENTS_LINKED", "L-3", "L3_BS_INVESTMENTS_LINKED", "Assets to Cover Linked Liabilities", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 480),
    ("L3_BS_LOANS", "L-3", "L3_BS_LOANS", "Loans", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 490),
    ("L3_BS_FIXED_ASSETS", "L-3", "L3_BS_FIXED_ASSETS", "Fixed Assets", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 500),
    ("L3_BS_CASH_BANK", "L-3", "L3_BS_CASH_BANK", "Cash and Bank Balances", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 510),
    ("L3_BS_ADVANCES_OTHER_ASSETS", "L-3", "L3_BS_ADVANCES_OTHER_ASSETS", "Advances and Other Assets", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 515),
    ("L3_BS_NET_CURRENT_ASSETS", "L-3", "L3_BS_NET_CURRENT_ASSETS", "Net Current Assets", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", "L3_BS_TOTAL_APPLICATION", 2, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 520),
    ("L3_BS_TOTAL_APPLICATION", "L-3", "L3_BS_TOTAL_APPLICATION", "Total Application of Funds", "APPLICATION_OF_FUNDS", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "POINT_IN_TIME_STOCK", 530),

    # L-32 Solvency Margin
    ("L32_SOLV_AVAILABLE_ASSETS", "L-32", "L32_SOLV_AVAILABLE_ASSETS", "Total Available Solvency Margin (ASM)", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 600),
    ("L32_SOLV_REQUIRED_MARGIN", "L-32", "L32_SOLV_REQUIRED_MARGIN", "Total Required Solvency Margin (RSM)", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 610),
    ("L32_SOLV_RATIO", "L-32", "L32_SOLV_RATIO", "Solvency Ratio (ASM/RSM)", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "RATIO_NON_ADDITIVE", 620),
    ("L32_SOLV_EXCESS_PH", "L-32", "L32_SOLV_EXCESS_PH", "Excess in Policyholders' funds", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 621),
    ("L32_SOLV_EXCESS_SH", "L-32", "L32_SOLV_EXCESS_SH", "Excess in Shareholders' funds", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 622),
    ("L32_SOLV_MATH_RESERVES", "L-32", "L32_SOLV_MATH_RESERVES", "Mathematical reserves", "SOLVENCY", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "POINT_IN_TIME_STOCK", 623),

    # L-9 Pattern of Shareholding
    ("L9_SHARES_INDIAN", "L-9", "L9_SHARES_INDIAN", "Indian Shareholding (Number of Shares)", "SHAREHOLDING", "PRIMARY_BREAKDOWN", "L9_SHARES_TOTAL", 2, 1, 0, 0, 1, "COUNT_ADDITIVE", 800),
    ("L9_SHARES_FOREIGN", "L-9", "L9_SHARES_FOREIGN", "Foreign Shareholding (Number of Shares)", "SHAREHOLDING", "PRIMARY_BREAKDOWN", "L9_SHARES_TOTAL", 2, 1, 0, 0, 1, "COUNT_ADDITIVE", 810),
    ("L9_SHARES_OTHERS", "L-9", "L9_SHARES_OTHERS", "Other Shareholding (Number of Shares)", "SHAREHOLDING", "PRIMARY_BREAKDOWN", "L9_SHARES_TOTAL", 2, 1, 0, 0, 1, "COUNT_ADDITIVE", 820),
    ("L9_SHARES_TOTAL", "L-9", "L9_SHARES_TOTAL", "Total Number of Shares", "SHAREHOLDING", "PRIMARY_BREAKDOWN", None, 1, 0, 1, 0, 1, "COUNT_ADDITIVE", 830),

    # Ind AS 117 Bridge Metrics
    ("IAS117_INS_REVENUE", "L-1", "IAS117_INS_REVENUE", "Insurance Revenue (Ind AS 117)", "IND_AS_117", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 700),
    ("IAS117_INS_SERVICE_EXP", "L-1", "IAS117_INS_SERVICE_EXP", "Insurance Service Expenses (Ind AS 117)", "IND_AS_117", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 710),
    ("IAS117_CSM_AMORT", "L-1", "IAS117_CSM_AMORT", "CSM Released to P&L (Ind AS 117)", "IND_AS_117", "PRIMARY_BREAKDOWN", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 720),
]

LINE_ITEM_ALIASES = [
    # L-4
    (1, "L4_PREM_FIRST_YEAR", "L-4", r"^first\s*year\s*premiums?"),
    (2, "L4_PREM_RENEWAL", "L-4", r"^renewal\s*premiums?"),
    (3, "L4_PREM_SINGLE", "L-4", r"^single\s*premiums?"),
    (4, "L4_PREM_TOTAL", "L-4", r"^total\s*premiums?$|^total$"),
    (5, "L4_PREM_GEO_INDIA", "L-4", r"^in\s*india$"),
    (6, "L4_PREM_GEO_OUTSIDE", "L-4", r"^outside\s*india$"),
    (7, "L4_PREM_GROSS", "L-4", r"^gross\b|^gross\s*premiums?"),
    (8, "L4_PREM_REINSURANCE_ACCEPTED", "L-4", r"^reinsurance\s*accepted"),
    (9, "L4_PREM_REINSURANCE_CEDED", "L-4", r"^reinsurance\s*ceded"),
    (10, "L4_PREM_NET", "L-4", r"^net\s*premiums?|^premiums?\s*earned\s*[-–—]?\s*net"),

    # L-1
    (20, "L1_REV_GROSS_PREMIUM", "L-1", r"^gross\s*premiums?$|^premium$|^premiums?$"),
    (21, "L1_REV_REINSURANCE_CEDED", "L-1", r"^reinsurance\s*ceded$"),
    (22, "L1_REV_REINSURANCE_ACCEPTED", "L-1", r"^reinsurance\s*accepted$"),
    (23, "L1_REV_NET_PREMIUM", "L-1", r"^premiums?\s*earned\s*[-–—]?\s*net$|^net\s*premiums?$"),
    (24, "L1_REV_INVESTMENT_INCOME", "L-1", r"^income\s*from\s*investments?$"),
    (25, "L1_REV_PROFIT_LOSS_INVESTMENTS", "L-1", r"(?:profit|loss)\s*on\s*sale.*investments?"),
    (26, "L1_REV_OTHER_INCOME", "L-1", r"^other\s*income$"),
    (27, "L1_REV_TOTAL_INCOME", "L-1", r"^total\s*\(?a\)?$|^total\s*income$"),
    (28, "L1_REV_COMMISSION", "L-1", r"^commission$"),
    (29, "L1_REV_OPERATING_EXPENSES", "L-1", r"^operating\s*expenses"),
    (30, "L1_REV_GST_ULIP", "L-1", r"goods\s*and\s*services\s*tax.*ulip|^gst.*ulip"),
    (31, "L1_REV_PROVISIONS_OTHER", "L-1", r"^provisions?\s*\(other\s*than\s*taxation\)|^provisions?$"),
    (32, "L1_REV_BAD_DEBTS", "L-1", r"^bad\s*debts\s*written\s*off"),
    (33, "L1_REV_PROV_DOUBTFUL_DEBTS", "L-1", r"^provision\s*for\s*doubtful\s*debts?"),
    (34, "L1_REV_TOTAL_EXPENSES", "L-1", r"^total\s*\(?b\)?$|^total\s*expenses$|^sub\s*[-–—]?\s*total$"),
    (35, "L1_REV_BENEFITS_PAID", "L-1", r"^benefits\s*paid"),
    (36, "L1_REV_CHANGE_VALUATION", "L-1", r"^change\s*in\s*valuation"),
    (37, "L1_REV_SURPLUS_DEFICIT", "L-1", r"^surplus\s*\/?\s*\(?deficit\)?"),
    (38, "L1_REV_TRANSFER_SH", "L-1", r"^(?:amount\s*)?transferred\s*to\s*shareholders"),
    (39, "L1_REV_PROVISION_TAX", "L-1", r"^provision\s*for\s*tax"),

    # L-2
    (40, "L2_PL_TRANSFER_PH", "L-2", r"^(?:amount\s*)?transferred\s*from\s*policyholders"),
    (41, "L2_PL_INVESTMENT_INCOME", "L-2", r"^income\s*from\s*investments?"),
    (42, "L2_PL_OTHER_INCOME", "L-2", r"^other\s*income$"),
    (43, "L2_PL_TOTAL_INCOME", "L-2", r"^total\s*\(?a\)?$"),
    (44, "L2_PL_EXPENSES", "L-2", r"^expense\s*other\s*than"),
    (45, "L2_PL_BAD_DEBTS", "L-2", r"^bad\s*debts\s*written\s*off"),
    (46, "L2_PL_PROV_DOUBTFUL", "L-2", r"^provision\s*for\s*doubtful\s*debts?"),
    (47, "L2_PL_TOTAL_EXPENSES", "L-2", r"^total\s*\(?b\)?$"),
    (48, "L2_PL_PBT", "L-2", r"^profit\s*\/?\s*\(?loss\)?\s*before\s*tax"),
    (49, "L2_PL_PROVISION_TAX", "L-2", r"^provision\s*for\s*tax"),
    (50, "L2_PL_PAT", "L-2", r"^profit\s*\/?\s*\(?loss\)?\s*after\s*tax"),

    # L-3
    (60, "L3_BS_SHARE_CAPITAL", "L-3", r"^share\s*capital$"),
    (61, "L3_BS_RESERVES", "L-3", r"^reserves\s*and\s*surplus$"),
    (62, "L3_BS_BORROWINGS", "L-3", r"^borrowings$"),
    (63, "L3_BS_POLICY_LIABILITIES", "L-3", r"^policy\s*liabilities$"),
    (64, "L3_BS_LINKED_LIABILITIES", "L-3", r"^provision\s*for\s*linked\s*liabilities$"),
    (65, "L3_BS_TOTAL_SOURCES", "L-3", r"^total\s*(?:sources\s*of\s*funds)?$"),
    (66, "L3_BS_INVESTMENTS_SH", "L-3", r"^investments?\s*[-–—]?\s*shareholders"),
    (67, "L3_BS_INVESTMENTS_PH", "L-3", r"^investments?\s*[-–—]?\s*policyholders"),
    (68, "L3_BS_INVESTMENTS_LINKED", "L-3", r"^assets\s*held\s*to\s*cover\s*linked\s*liabilities|^investments?\s*[-–—]?\s*unit\s*linked"),
    (69, "L3_BS_LOANS", "L-3", r"^loans$"),
    (70, "L3_BS_FIXED_ASSETS", "L-3", r"^fixed\s*assets$"),
    (71, "L3_BS_CASH_BANK", "L-3", r"^cash\s*and\s*bank\s*balances?$"),
    (72, "L3_BS_ADVANCES_OTHER_ASSETS", "L-3", r"^advances\s*and\s*other\s*assets$"),
    (73, "L3_BS_NET_CURRENT_ASSETS", "L-3", r"^net\s*current\s*assets$"),
    (74, "L3_BS_TOTAL_APPLICATION", "L-3", r"^total\s*(?:application\s*of\s*funds)?$"),

    # L-32
    (80, "L32_SOLV_AVAILABLE_ASSETS", "L-32", r"^total\s*asm|^available\s*assets|^available\s*solvency\s*margin"),
    (81, "L32_SOLV_REQUIRED_MARGIN", "L-32", r"^total\s*rsm|^required\s*solvency\s*margin"),
    (82, "L32_SOLV_RATIO", "L-32", r"^solvency\s*ratio"),
    (83, "L32_SOLV_EXCESS_PH", "L-32", r"excess\s*in\s*policyholders"),
    (84, "L32_SOLV_EXCESS_SH", "L-32", r"excess\s*in\s*shareholders"),
    (85, "L32_SOLV_MATH_RESERVES", "L-32", r"^mathematical\s*reserves?"),

    # L-9
    (90, "L9_SHARES_INDIAN", "L-9", r"^indian"),
    (91, "L9_SHARES_FOREIGN", "L-9", r"^foreign"),
    (92, "L9_SHARES_OTHERS", "L-9", r"^others?$"),
    (93, "L9_SHARES_TOTAL", "L-9", r"^total\s*(?:number\s*of\s*shares)?$|^total$"),
]

def seed_database(db_manager):
    """Inserts all master dimensions into the database."""
    conn = db_manager.connection
    if db_manager.engine == "sqlite":
        db_manager.execute("PRAGMA foreign_keys = OFF;")

    try:
        # 1. Units
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_reporting_unit (unit_id, unit_code, multiplier_to_lakhs, display_suffix, is_monetary) VALUES (?, ?, ?, ?, ?)",
            REPORTING_UNITS
        )

        # 2. Accounting Standards
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_accounting_standard (standard_id, standard_name, effective_from_date, description) VALUES (?, ?, ?, ?)",
            ACCOUNTING_STANDARDS
        )

        # 3. Statement Schedules
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_statement_schedule (schedule_code, schedule_name, statement_type, is_balance_sheet_schedule) VALUES (?, ?, ?, ?)",
            STATEMENT_SCHEDULES
        )

        # 4. Segments
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_segment (segment_id, segment_code, line_of_business, fund_type, display_order) VALUES (?, ?, ?, ?, ?)",
            SEGMENTS
        )

        # 5. Companies
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_company (company_id, company_name, short_name, irda_reg_no, category) VALUES (?, ?, ?, ?, ?)",
            COMPANIES
        )

        # 6. Company Aliases
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_company_alias (alias_id, company_id, alias_name, effective_from_year, effective_to_year) VALUES (?, ?, ?, ?, ?)",
            COMPANY_ALIASES
        )

        # 7. Periods
        periods = generate_periods()
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_period (period_id, financial_year, quarter, fiscal_year_start, quarter_num, quarter_start_date, quarter_end_date, chronological_sequence, is_audited) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            periods
        )

        # 8. Line Items
        db_manager.executemany(
            """INSERT OR IGNORE INTO dim_line_item (
                line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total,
                is_subtotal, normal_balance_sign, aggregation_type, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            LINE_ITEMS
        )

        # 9. Line Item Aliases
        db_manager.executemany(
            "INSERT OR IGNORE INTO dim_line_item_alias (alias_id, line_item_id, schedule_code, regex_pattern) VALUES (?, ?, ?, ?)",
            LINE_ITEM_ALIASES
        )

        db_manager.commit()
    finally:
        if db_manager.engine == "sqlite":
            db_manager.execute("PRAGMA foreign_keys = ON;")
            db_manager.commit()
    print("Database seeding completed successfully.")
