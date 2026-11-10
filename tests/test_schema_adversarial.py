"""
Adversarial Test Harness for Life Insurance Hardened Database Architecture (v3.0)
Specialization: Database Schemas, SQL Constraints, Double-Counting Vulnerabilities,
Precision Degeneracy, and SCD Type 2 Non-Destructive Ledgers.

Executes tests against SQLite 3 and DuckDB in-memory engines.
"""

import sys
import os
import sqlite3
import duckdb
from decimal import Decimal
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Hardened Base DDL imported directly from verified architecture specification
from tests.verify_architecture_ddl import SQL_DDL as BASE_DDL


# Common Master Data
MASTER_DATA = """
INSERT INTO dim_company (company_id, company_name, short_name, irda_reg_no, category) VALUES
('LIC', 'Life Insurance Corporation of India', 'LIC', '512', 'Public PSU'),
('HDFC_LIFE', 'HDFC Life Insurance Co Ltd', 'HDFC Life', '101', 'Private');

INSERT INTO dim_period (period_id, financial_year, quarter, fiscal_year_start, quarter_num, quarter_start_date, quarter_end_date, chronological_sequence, is_audited) VALUES
('FY2023-24_Q1', 'FY2023-24', 'Q1', 2023, 1, '2023-04-01', '2023-06-30', 1, 0),
('FY2023-24_Q2', 'FY2023-24', 'Q2', 2023, 2, '2023-07-01', '2023-09-30', 2, 0),
('FY2024-25_Q2', 'FY2024-25', 'Q2', 2024, 2, '2024-07-01', '2024-09-30', 6, 0);

INSERT INTO dim_statement_schedule (schedule_code, schedule_name, statement_type, is_balance_sheet_schedule) VALUES
('L-1', 'Revenue Account', 'REVENUE', 0),
('L-2', 'Profit and Loss Account', 'PROFIT_LOSS', 0),
('L-3', 'Balance Sheet', 'BALANCE_SHEET', 1),
('L-4', 'Premium Schedule', 'REVENUE', 0);

INSERT INTO dim_segment (segment_id, segment_code, line_of_business, fund_type, display_order) VALUES
('TOTAL', 'TOTAL', 'TOTAL', 'TOTAL', 1),
('PAR_LIFE', 'PAR_LIFE', 'LIFE', 'PARTICIPATING', 2),
('NON_PAR', 'NON_PAR', 'LIFE', 'NON_PARTICIPATING', 3),
('LINKED', 'LINKED', 'LIFE', 'UNIT_LINKED', 4);

INSERT INTO dim_reporting_unit (unit_id, unit_code, multiplier_to_lakhs, display_suffix, is_monetary) VALUES
('LAKHS', 'LAKHS', 1.0, 'Lakhs', 1),
('CRORES', 'CRORES', 100.0, 'Crores', 1);

INSERT INTO audit_etl_batches (batch_id, status, source_file_path, source_file_checksum, total_records_processed) VALUES
(1001, 'SUCCESS', 'Batch1001.xlsx', 'hash1001', 100),
(1002, 'SUCCESS', 'Batch1002.xlsx', 'hash1002', 100);
"""

class AdversarialReport:
    def __init__(self):
        self.results = []
    
    def record(self, test_name, engine, status, details, risk_level="INFO"):
        self.results.append({
            "test_name": test_name,
            "engine": engine,
            "status": status,
            "details": details,
            "risk_level": risk_level
        })
        badge = f"[{status}]"
        print(f"{badge:8} [{engine:7}] {test_name}: {details}")

def run_adversarial_suite():
    report = AdversarialReport()
    print("=" * 90)
    print("COMMENCING EMPIRICAL ADVERSARIAL STRESS-TEST SUITE ACROSS SQLITE & DUCKDB")
    print("=" * 90)

    # We will test on both SQLite and DuckDB
    for engine_name in ["SQLite", "DuckDB"]:
        print(f"\n>>> ENGINE UNDER TEST: {engine_name} <<<")
        if engine_name == "SQLite":
            conn = sqlite3.connect(":memory:")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(BASE_DDL)
            conn.executescript(MASTER_DATA)
            cursor = conn.cursor()
            execute_fn = cursor.execute
            executemany_fn = cursor.executemany
            commit_fn = conn.commit
            fetchall_fn = cursor.fetchall
            fetchone_fn = cursor.fetchone
        else:
            conn = duckdb.connect(":memory:")
            conn.execute(BASE_DDL)
            conn.execute(MASTER_DATA)
            execute_fn = conn.execute
            executemany_fn = conn.executemany
            commit_fn = lambda: None
            fetchall_fn = lambda: conn.fetchall()
            fetchone_fn = lambda: conn.fetchone()

        # =====================================================================
        # CATEGORY 1: DOUBLE COUNTING & ORTHOGONAL HIERARCHY VULNERABILITY
        # =====================================================================

        # Setup test data for Form L-4:
        # 3 Product leaves (100k, 300k, 100k = 500k)
        # 1 Product total (500k, is_total=1, is_leaf=0)
        # 2 Geo leaves (450k, 50k = 500k, axis=BY_GEOGRAPHY)
        # 1 Summary grand total (500k, axis=SUMMARY_TOTAL, is_total=1, is_leaf=0)
        line_items_l4 = [
            ("L4_FY", "L-4", "L4_FY", "First Year", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 1),
            ("L4_RN", "L-4", "L4_RN", "Renewal", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 2),
            ("L4_SG", "L-4", "L4_SG", "Single", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 3),
            ("L4_TOT_PROD", "L-4", "L4_TOT_PROD", "Total Product", "PREMIUM", "BY_PRODUCT_TYPE", None, 1, 0, 1, 0, 1, "FLOW_ADDITIVE", 4),
            ("L4_GEO_IN", "L-4", "L4_GEO_IN", "In India", "PREMIUM", "BY_GEOGRAPHY", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 5),
            ("L4_GEO_OUT", "L-4", "L4_GEO_OUT", "Outside India", "PREMIUM", "BY_GEOGRAPHY", None, 1, 1, 0, 0, 1, "FLOW_ADDITIVE", 6),
            ("L4_GRAND_TOT", "L-4", "L4_GRAND_TOT", "Summary Total", "PREMIUM", "SUMMARY_TOTAL", None, 0, 0, 1, 0, 1, "FLOW_ADDITIVE", 7),
        ]
        for item in line_items_l4:
            execute_fn("""
                INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                           classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                           normal_balance_sign, aggregation_type, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, item)
        commit_fn()

        # Insert facts for L-4
        l4_facts = [
            (101, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 1001),
            (102, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_RN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 300000.0, 300000.0, 1001),
            (103, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_SG', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 1001),
            (104, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_TOT_PROD', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 500000.0, 500000.0, 1001),
            (105, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GEO_IN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 450000.0, 450000.0, 1001),
            (106, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GEO_OUT', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 50000.0, 50000.0, 1001),
            (107, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GRAND_TOT', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 500000.0, 500000.0, 1001),
        ]
        for f in l4_facts:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, f)
        commit_fn()

        # Test 1.1: Naive fact sum vs vw_dashboard_financials in L-4
        execute_fn("SELECT SUM(quarter_amount_lakhs) FROM fact_financial_statement WHERE schedule_code = 'L-4' AND company_id = 'HDFC_LIFE';")
        naive_sum = float(fetchone_fn()[0])
        execute_fn("SELECT SUM(signed_quarter_lakhs) FROM vw_dashboard_financials WHERE schedule_code = 'L-4' AND company_id = 'HDFC_LIFE';")
        view_sum = float(fetchone_fn()[0])

        if naive_sum == 2000000.0 and view_sum == 500000.0:
            report.record("L4_Orthogonal_Double_Count_Prevention", engine_name, "PASS",
                          f"Naive sum was 2,000,000 Lakhs (400% inflated); vw_dashboard_financials filtered down to exact 500,000 Lakhs.")
        else:
            report.record("L4_Orthogonal_Double_Count_Prevention", engine_name, "FAIL",
                          f"Expected 500,000, got view={view_sum}, naive={naive_sum}", "CRITICAL")

        # Test 1.2: Adversarial Multi-Axis Clash within vw_dashboard_financials
        # What if a schedule contains BOTH 'PRIMARY_BREAKDOWN' and 'BY_PRODUCT_TYPE' items that overlap?
        # Note: vw_dashboard_financials filter: m.classification_axis IN ('PRIMARY_BREAKDOWN', 'BY_PRODUCT_TYPE')
        # If someone marks an elemental metric as PRIMARY_BREAKDOWN and the sub-products as BY_PRODUCT_TYPE in the SAME schedule,
        # vw_dashboard_financials will sum BOTH!
        # Let's test this vulnerability:
        execute_fn("""
            INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                       classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                       normal_balance_sign, aggregation_type, display_order)
            VALUES ('L4_TOTAL_AS_PRIMARY_LEAF', 'L-4', 'L4_TOTAL_AS_PRIMARY_LEAF', 'Total Prem Leaf Mistagged', 'PREMIUM',
                    'PRIMARY_BREAKDOWN', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 8);
        """)
        execute_fn("""
            INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                  filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                  raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
            VALUES (108, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_TOTAL_AS_PRIMARY_LEAF', 'TOTAL', 'FY2023-24_Q2',
                    'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 500000.0, 500000.0, 1001);
        """)
        commit_fn()
        execute_fn("SELECT SUM(signed_quarter_lakhs) FROM vw_dashboard_financials WHERE schedule_code = 'L-4' AND company_id = 'HDFC_LIFE';")
        mistagged_sum = float(fetchone_fn()[0])
        # Clean up fact 108 and line item
        execute_fn("DELETE FROM fact_financial_statement WHERE fact_id = 108;")
        execute_fn("DELETE FROM dim_line_item WHERE line_item_id = 'L4_TOTAL_AS_PRIMARY_LEAF';")
        commit_fn()

        if mistagged_sum == 1000000.0:
            report.record("Axis_Coexistence_Vulnerability", engine_name, "VULN_EXPOSED",
                          f"vw_dashboard_financials filters IN ('PRIMARY_BREAKDOWN', 'BY_PRODUCT_TYPE'). If both axes contain is_leaf=1 in the same schedule, sum doubled to {mistagged_sum} Lakhs.", "HIGH")
        else:
            report.record("Axis_Coexistence_Vulnerability", engine_name, "PASS", f"Schedule-axis isolation prevented double counting; sum remained {mistagged_sum} Lakhs.")

        # Test 1.3: Segment-Level Double-Counting Stress Test
        # In reality, statements contain facts broken down by segment ('PAR_LIFE', 'NON_PAR', 'LINKED')
        # AND a consolidated total ('TOTAL').
        # If both are active in fact_financial_statement, does vw_dashboard_financials filter segment_id?
        # Let's insert segment breakdown for L4_FY: PAR=40k, NON_PAR=30k, LINKED=30k (Sum = 100k = TOTAL)
        execute_fn("""
            INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                  filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                  raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id) VALUES
            (109, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'PAR_LIFE', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 40000.0, 40000.0, 1001),
            (110, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'NON_PAR', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 30000.0, 30000.0, 1001),
            (111, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'LINKED', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 30000.0, 30000.0, 1001);
        """)
        commit_fn()
        execute_fn("SELECT SUM(signed_quarter_lakhs) FROM vw_dashboard_financials WHERE schedule_code = 'L-4' AND company_id = 'HDFC_LIFE';")
        segment_inflated_sum = float(fetchone_fn()[0])
        # Clean up facts 109, 110, 111
        execute_fn("DELETE FROM fact_financial_statement WHERE fact_id IN (109, 110, 111);")
        commit_fn()

        if segment_inflated_sum == 600000.0:
            report.record("Segment_Summation_Trap", engine_name, "VULN_EXPOSED",
                          f"vw_dashboard_financials lacks segment_id isolation: when both TOTAL and constituent segments coexist, total summed to {segment_inflated_sum} (inflated by 100k segment sum). Queries MUST filter segment_id.", "HIGH")
        else:
            report.record("Segment_Summation_Trap", engine_name, "PASS", f"Segment isolation verified; sum remained {segment_inflated_sum} Lakhs.")

        # Test 1.4: Comparative Restatements Coexistence
        # If both AS_REPORTED_ORIGINAL and RESTATED_COMPARATIVE are is_active=1 in fact_financial_statement,
        # Does vw_dashboard_financials filter reporting_basis?
        # Recall: vw_financial_metrics_primary filters f.reporting_basis = 'AS_REPORTED_ORIGINAL'.
        # But vw_dashboard_financials does NOT!
        execute_fn("""
            INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                  filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                  raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id) VALUES
            (112, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2024-25_Q2', 'RESTATED_COMPARATIVE', 'LAKHS', 1.0, 105000.0, 105000.0, 1002);
        """)
        commit_fn()
        execute_fn("SELECT SUM(signed_quarter_lakhs) FROM vw_dashboard_financials WHERE schedule_code = 'L-4' AND company_id = 'HDFC_LIFE';")
        comparative_inflated_sum = float(fetchone_fn()[0])
        # Clean up fact 112
        execute_fn("DELETE FROM fact_financial_statement WHERE fact_id = 112;")
        commit_fn()

        if comparative_inflated_sum == 605000.0:
            report.record("Comparative_Basis_Coexistence_Vulnerability", engine_name, "VULN_EXPOSED",
                          f"vw_dashboard_financials does NOT filter reporting_basis='AS_REPORTED_ORIGINAL'. When restated comparative was present, sum inflated from 500k to {comparative_inflated_sum} Lakhs.", "HIGH")
        else:
            report.record("Comparative_Basis_Coexistence_Vulnerability", engine_name, "PASS", f"Comparative basis isolation verified; sum remained {comparative_inflated_sum} Lakhs.")

        # Test 1.5: Existence of vw_leaf_financials
        # Document references 'vw_leaf_financials', check if it is compiled
        has_vw_leaf = False
        try:
            execute_fn("SELECT * FROM vw_leaf_financials LIMIT 1;")
            has_vw_leaf = True
        except Exception as e:
            has_vw_leaf = False

        if not has_vw_leaf:
            report.record("Missing_View_vw_leaf_financials", engine_name, "DEFECT_FOUND",
                          "vw_leaf_financials is referenced in documentation (Section 1.2, 3.3) but absent from ANSI DDL specification.", "MEDIUM")
        else:
            report.record("Missing_View_vw_leaf_financials", engine_name, "PASS", "vw_leaf_financials compiled cleanly.")

        # Test 1.6: Metadata Mutual Exclusivity Check (is_leaf vs is_total / is_subtotal)
        # Attempt to insert an invalid line item where is_leaf = 1 AND is_total = 1
        meta_contradiction_threw = False
        try:
            execute_fn("""
                INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                           classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                           normal_balance_sign, aggregation_type, display_order)
                VALUES ('L4_CONTRADICTORY', 'L-4', 'L4_CONTRADICTORY', 'Contradictory Leaf Total', 'PREMIUM',
                        'PRIMARY_BREAKDOWN', NULL, 1, 1, 1, 0, 1, 'FLOW_ADDITIVE', 99);
            """)
            commit_fn()
            # Clean up
            execute_fn("DELETE FROM dim_line_item WHERE line_item_id = 'L4_CONTRADICTORY';")
            commit_fn()
        except Exception as e:
            meta_contradiction_threw = True

        if not meta_contradiction_threw:
            report.record("Metadata_Flag_Contradiction_Vulnerability", engine_name, "VULN_EXPOSED",
                          "dim_line_item lacks CHECK constraint enforcing mutual exclusivity between is_leaf=1 and is_total=1 / is_subtotal=1. Corrupt metadata can silently infiltrate leaf views.", "MEDIUM")
        else:
            report.record("Metadata_Flag_Contradiction_Vulnerability", engine_name, "PASS",
                          "CHECK constraint blocked contradictory hierarchy flags.")

        # Test 1.7: 4-Level Multi-Tier Hierarchical Rollup & Signed Balances in L-1
        # Leaves: First Year (50k), Renewal (150k), Single (100k), Reins Ceded (20k, sign -1), Reins Acc (5k, sign 1), Inv Income (40k, sign 1), Inv Gain (10k, sign 1)
        # Expected Net Total = (50+150+100) - 20 + 5 + 40 + 10 = 335,000 Lakhs
        # Subtotals inserted: Gross Prem (300k, is_subtotal=1, is_leaf=0), Net Prem (285k, is_subtotal=1, is_leaf=0), Grand Total (335k, is_total=1, is_leaf=0)
        l1_hierarchy_items = [
            ("L1_FY", "L-1", "L1_FY", "First Year", "PREMIUM", "PRIMARY_BREAKDOWN", None, 3, 1, 0, 0, 1, "FLOW_ADDITIVE", 1),
            ("L1_RN", "L-1", "L1_RN", "Renewal", "PREMIUM", "PRIMARY_BREAKDOWN", None, 3, 1, 0, 0, 1, "FLOW_ADDITIVE", 2),
            ("L1_SG", "L-1", "L1_SG", "Single", "PREMIUM", "PRIMARY_BREAKDOWN", None, 3, 1, 0, 0, 1, "FLOW_ADDITIVE", 3),
            ("L1_SUB_GROSS", "L-1", "L1_SUB_GROSS", "Gross Premium Subtotal", "PREMIUM", "PRIMARY_BREAKDOWN", None, 2, 0, 0, 1, 1, "FLOW_ADDITIVE", 4),
            ("L1_RCEDED", "L-1", "L1_RCEDED", "Reins Ceded", "PREMIUM", "PRIMARY_BREAKDOWN", None, 2, 1, 0, 0, -1, "FLOW_ADDITIVE", 5),
            ("L1_RACC", "L-1", "L1_RACC", "Reins Accepted", "PREMIUM", "PRIMARY_BREAKDOWN", None, 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 6),
            ("L1_SUB_NET", "L-1", "L1_SUB_NET", "Net Premium Subtotal", "PREMIUM", "PRIMARY_BREAKDOWN", None, 1, 0, 0, 1, 1, "FLOW_ADDITIVE", 7),
            ("L1_INV_INC", "L-1", "L1_INV_INC", "Investment Income", "INVESTMENT", "PRIMARY_BREAKDOWN", None, 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 8),
            ("L1_INV_GAIN", "L-1", "L1_INV_GAIN", "Profit on Sale", "INVESTMENT", "PRIMARY_BREAKDOWN", None, 2, 1, 0, 0, 1, "FLOW_ADDITIVE", 9),
            ("L1_TOTAL_INC", "L-1", "L1_TOTAL_INC", "Total Policyholders Income", "SUMMARY", "PRIMARY_BREAKDOWN", None, 0, 0, 1, 0, 1, "FLOW_ADDITIVE", 10),
        ]
        for itm in l1_hierarchy_items:
            execute_fn("""
                INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                           classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                           normal_balance_sign, aggregation_type, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, itm)
        commit_fn()

        l1_facts = [
            (301, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 50000.0, 50000.0, 1001),
            (302, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_RN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 150000.0, 150000.0, 1001),
            (303, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_SG', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 1001),
            (304, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_SUB_GROSS', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 300000.0, 300000.0, 1001),
            (305, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_RCEDED', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 20000.0, 20000.0, 1001),
            (306, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_RACC', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 5000.0, 5000.0, 1001),
            (307, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_SUB_NET', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 285000.0, 285000.0, 1001),
            (308, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_INV_INC', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 40000.0, 40000.0, 1001),
            (309, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_INV_GAIN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 10000.0, 10000.0, 1001),
            (310, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-1', 'L1_TOTAL_INC', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 335000.0, 335000.0, 1001),
        ]
        for f in l1_facts:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, f)
        commit_fn()

        execute_fn("SELECT SUM(quarter_amount_lakhs) FROM fact_financial_statement WHERE schedule_code = 'L-1' AND company_id = 'HDFC_LIFE';")
        l1_naive = float(fetchone_fn()[0])
        execute_fn("SELECT SUM(signed_quarter_lakhs) FROM vw_dashboard_financials WHERE schedule_code = 'L-1' AND company_id = 'HDFC_LIFE';")
        l1_view_signed = float(fetchone_fn()[0])

        # l1_naive sums all raw numbers: 50+150+100+300+20+5+285+40+10+335 = 1,295,000 Lakhs!
        # l1_view_signed sums signed leaves: 50 + 150 + 100 - 20 + 5 + 40 + 10 = 335,000 Lakhs!
        if l1_view_signed == 335000.0 and l1_naive == 1295000.0:
            report.record("Multi_Tier_Hierarchy_Signed_Balance_Rollup", engine_name, "PASS",
                          f"Naive sum was 1,295,000 Lakhs (386% inflated); vw_dashboard_financials signed leaves sum yielded exact 335,000 Lakhs matching Total Income.")
        else:
            report.record("Multi_Tier_Hierarchy_Signed_Balance_Rollup", engine_name, "FAIL",
                          f"Expected 335,000 Lakhs, got view={l1_view_signed}, naive={l1_naive}", "HIGH")

        # =====================================================================
        # CATEGORY 2: CONSTRAINT STRESS & NATURAL BUSINESS GRAIN UNIQUENESS
        # =====================================================================

        # Test 2.1: Duplicate Insertion on Pure Business Grain
        dup_threw = False
        try:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (999, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 1001);
            """)
            commit_fn()
        except Exception as e:
            dup_threw = True
            try:
                if engine_name == "DuckDB":
                    conn.rollback()
            except Exception:
                pass

        if dup_threw:
            report.record("Constraint_Grain_Uniqueness", engine_name, "PASS",
                          "Attempt to insert identical natural business grain was strictly rejected by uq_fact_grain.")
        else:
            report.record("Constraint_Grain_Uniqueness", engine_name, "FAIL",
                          "Duplicate active fact on identical natural grain was accepted without error!", "CRITICAL")

        # Test 2.2: SCD Type 2 Amendment Simulation vs Table Constraint uq_fact_grain
        # Scenario: An amended filing arrives for the same filing_period_id.
        # Step 1: Update active record to is_active = 0, superseded_by_batch_id = 1002
        execute_fn("UPDATE fact_financial_statement SET is_active = 0, superseded_by_batch_id = 1002 WHERE fact_id = 101;")
        commit_fn()

        # Step 2: Ingest amended record version 2 with statement_version_id = 2, is_active = 1
        # BUT with SAME filing_period_id and business grain!
        scd2_threw = False
        try:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, statement_version_id,
                                                      is_active, valid_from_batch_id)
                VALUES (120, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL',
                        'LAKHS', 1.0, 102000.0, 102000.0, 2, 1, 1002);
            """)
            commit_fn()
        except Exception as e:
            scd2_threw = True
            err_msg = str(e)

        # Re-activate fact 101 for subsequent tests
        execute_fn("UPDATE fact_financial_statement SET is_active = 1, superseded_by_batch_id = NULL WHERE fact_id = 101;")
        commit_fn()

        if scd2_threw:
            report.record("SCD2_Grain_Conflict_Vulnerability", engine_name, "VULN_EXPOSED",
                          f"SCD Type 2 versioning FAILS on re-filing within same filing_period_id: uq_fact_grain is a table-wide UNIQUE constraint without statement_version_id. Error: {err_msg[:80]}", "CRITICAL")
        else:
            report.record("SCD2_Grain_Conflict_Vulnerability", engine_name, "PASS",
                          "SCD Type 2 row successfully inserted alongside superseded row.")

        # Test 2.3: Foreign Key Integrity Check
        fk_threw = False
        try:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (998, 'NON_EXISTENT_COMPANY', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100.0, 100.0, 1001);
            """)
            commit_fn()
        except Exception as e:
            fk_threw = True

        if fk_threw:
            report.record("FK_Integrity_Check", engine_name, "PASS", "Foreign key constraint prevented orphaned fact insertion.")
        else:
            report.record("FK_Integrity_Check", engine_name, "FAIL", "Orphaned fact with invalid company_id was inserted!", "HIGH")

        # =====================================================================
        # CATEGORY 3: NUMERIC PRECISION STRESS (NUMERIC(18, 4))
        # =====================================================================

        # Test 3.1: ₹500,000 Crores = 50,000,000,000.0000 Lakhs
        # Scale: 50 Billion Lakhs = 50,000,000,000.1234
        mega_val = Decimal("50000000000.1234")
        execute_fn("""
            INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                       classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                       normal_balance_sign, aggregation_type, display_order)
            VALUES ('L1_MEGA_LIC', 'L-1', 'L1_MEGA_LIC', 'Mega Asset Valuation', 'POLICYHOLDERS',
                    'PRIMARY_BREAKDOWN', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 99);
        """)
        execute_fn("""
            INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                  filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                  raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
            VALUES (201, 'LIC', 'FY2023-24_Q2', 'L-1', 'L1_MEGA_LIC', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL',
                    'LAKHS', 1.0, 50000000000.1234, 50000000000.1234, 1001);
        """)
        commit_fn()

        execute_fn("SELECT quarter_amount_lakhs FROM fact_financial_statement WHERE fact_id = 201;")
        stored_val = fetchone_fn()[0]

        # Precision arithmetic test
        execute_fn("SELECT quarter_amount_lakhs + 0.0001 FROM fact_financial_statement WHERE fact_id = 201;")
        added_val = fetchone_fn()[0]

        if engine_name == "DuckDB":
            # In DuckDB, stored_val is Decimal
            is_exact = (Decimal(str(stored_val)) == mega_val)
            report.record("Extreme_Monetary_Precision_50B_Lakhs", engine_name, "PASS" if is_exact else "FAIL",
                          f"DuckDB stored exact fixed-point Decimal: {stored_val}. Result after +0.0001: {added_val}")
        else:
            # In SQLite, stored as REAL (IEEE 754 float)
            delta = abs(float(stored_val) - float(mega_val))
            # 50,000,000,000.1234 has 15 significant decimal digits. In float64, mantissa is 53 bits (15-17 digits).
            if delta < 1e-3:
                report.record("Extreme_Monetary_Precision_50B_Lakhs", engine_name, "PASS_WITH_RESERVATION",
                              f"SQLite stored {stored_val} (float delta={delta:.6e}). SQLite uses REAL affinity instead of arbitrary precision DECIMAL.")
            else:
                report.record("Extreme_Monetary_Precision_50B_Lakhs", engine_name, "FAIL",
                              f"SQLite float representation degraded: delta = {delta}", "HIGH")

        # Test 3.2: Maximum NUMERIC(18, 4) Limit Testing (99,999,999,999,999.9999)
        max_limit_val = Decimal("99999999999999.9999") # 18 digits (14 integer + 4 fractional)
        max_threw = False
        try:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (202, 'LIC', 'FY2023-24_Q2', 'L-1', 'L1_MEGA_LIC', 'PAR_LIFE', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL',
                        'LAKHS', 1.0, 99999999999999.9999, 99999999999999.9999, 1001);
            """)
            commit_fn()
            execute_fn("SELECT quarter_amount_lakhs FROM fact_financial_statement WHERE fact_id = 202;")
            res_max = fetchone_fn()[0]
            report.record("Numeric_18_4_Upper_Boundary", engine_name, "PASS",
                          f"Successfully stored 18-digit boundary figure: {res_max}")
        except Exception as e:
            max_threw = True
            report.record("Numeric_18_4_Upper_Boundary", engine_name, "FAIL",
                          f"Failed to store boundary 99,999,999,999,999.9999: {e}", "HIGH")

        # Test 3.3: Numeric Overflow (19 digits - 15 integer + 4 fractional: 100,000,000,000,000.0000)
        overflow_threw = False
        try:
            execute_fn("""
                INSERT INTO fact_financial_statement (fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                                                      filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                                                      raw_reported_amount, quarter_amount_lakhs, valid_from_batch_id)
                VALUES (203, 'LIC', 'FY2023-24_Q2', 'L-1', 'L1_MEGA_LIC', 'NON_PAR', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL',
                        'LAKHS', 1.0, 100000000000000.0000, 100000000000000.0000, 1001);
            """)
            commit_fn()
        except Exception as e:
            overflow_threw = True

        if engine_name == "DuckDB":
            if overflow_threw:
                report.record("Numeric_18_4_Overflow_Rejection", engine_name, "PASS",
                              "DuckDB strictly rejected 19-digit number exceeding DECIMAL(18, 4) bounds.")
            else:
                report.record("Numeric_18_4_Overflow_Rejection", engine_name, "FAIL",
                              "DuckDB allowed overflow beyond DECIMAL(18, 4)!", "MEDIUM")
        else:
            # SQLite does not enforce fixed DECIMAL bounds; it stores as REAL or INTEGER
            if not overflow_threw:
                report.record("Numeric_18_4_Overflow_Rejection", engine_name, "INFO",
                              "SQLite dynamic typing accepted 19 digits by promoting to 64-bit IEEE float (no decimal overflow error in SQLite).")

        # =====================================================================
        # CATEGORY 4: NON-DESTRUCTIVE LEDGER & SCD TYPE 2 AUDITABILITY
        # =====================================================================

        # Test 4.1: Cell-Level Lineage Integrity
        execute_fn("""
            INSERT INTO fact_cell_lineage (lineage_id, fact_id, source_file, sheet_name, row_idx, col_idx, cell_address,
                                           raw_particulars_text, raw_cell_value, cell_checksum, lineage_role)
            VALUES (501, 101, 'HDFC_Consolidated.xlsx', 'L-4', 12, 4, 'D12', 'First Year Premiums', '100000.00', 'sha256_mock_hash', 'PRIMARY_CELL');
        """)
        commit_fn()

        execute_fn("""
            SELECT f.company_id, f.period_id, m.canonical_label, f.quarter_amount_lakhs, l.source_file, l.sheet_name, l.cell_address
            FROM fact_financial_statement f
            JOIN dim_line_item m ON f.line_item_id = m.line_item_id
            JOIN fact_cell_lineage l ON f.fact_id = l.fact_id
            WHERE f.fact_id = 101;
        """)
        lineage_row = fetchone_fn()
        if lineage_row and lineage_row[4] == 'HDFC_Consolidated.xlsx' and lineage_row[6] == 'D12':
            report.record("Audit_Lineage_Traceability", engine_name, "PASS",
                          f"Successfully joined fact to raw spreadsheet coordinates: {lineage_row[4]}:{lineage_row[5]}!{lineage_row[6]}")
        else:
            report.record("Audit_Lineage_Traceability", engine_name, "FAIL", "Failed to retrieve 8-coordinate cell lineage.", "HIGH")

        # Clean up connection
        conn.close()

    print("\n" + "=" * 90)
    print("ALL EMPIRICAL TESTS COMPLETED. SUMMARY OF FINDINGS:")
    print("=" * 90)
    pass_cnt = sum(1 for r in report.results if "PASS" in r["status"])
    vuln_cnt = sum(1 for r in report.results if "VULN" in r["status"] or "DEFECT" in r["status"] or "FAIL" in r["status"])
    print(f"Total Tests Executed: {len(report.results)}")
    print(f"Passed: {pass_cnt}")
    print(f"Vulnerabilities / Defects Discovered: {vuln_cnt}")
    print("=" * 90)
    return report

if __name__ == "__main__":
    report = run_adversarial_suite()
