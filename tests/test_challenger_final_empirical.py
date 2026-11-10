"""
Empirical Adversarial Challenge Test Harness for Life Insurance Architecture (v3.0)
Agent: challenger_final
Roles: critic, specialist

Conducts code-executing adversarial challenge to verify:
1. SCD Type 2 Non-Destructive Ledger & Natural Key Versioning
2. Zero Double-Counting Guarantee (vw_dashboard_financials and vw_leaf_financials)
3. Devanagari Crores Regex with Nukta (\\u093c) and bilingual unit detection
4. Multi-engine ANSI SQL execution across SQLite 3 and DuckDB
"""

import sys
import os
import re
import sqlite3
import duckdb
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import base DDL from verified architecture
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.verify_architecture_ddl import SQL_DDL

# Unit rules from Section 5.3 of Master Architecture Plan
UNIT_RULES = [
    (r"\b(?:crores?|crs?\.?)\b|(?:\bकरोड\b)|करोड़", "CRORES", 100.0),
    (r"\b(?:lakhs?|lacs?\.?)\b|(?:\bलाख\b)", "LAKHS", 1.0),
    (r"(?:'000|\bthousands?\b)|(?:\bहजार\b)", "THOUSANDS", 0.01),
    (r"\bmillions?\b", "MILLIONS", 10.0),
    (r"\b(?:actuals?|in\s+(?:rs\.?|₹|inr))\b(?!\s+(?:lakh|crore|thousand|'000|million))", "ACTUAL_INR", 0.00001),
]

NON_CURRENCY_COLUMN_PATTERNS = [
    r"(?i)\b(?:no\.|number\s+of)\s+claims\s+paid\b",
    r"(?i)\b(?:no\.|number\s+of|count|lives|policies|complaints|agents|employees|branches|offices)\b",
    r"(?i)\b(?:ratio|percentage|rate|persistency|yield|margin\s+ratio)\b",
]

NON_CURRENCY_FORM_EXEMPTIONS = {"L-22", "L-38", "L-41", "L-45"}

def detect_column_group_unit(header_cells, form_code, col_header_text):
    if form_code in ("L-41", "L-45"):
        return "COUNT", 1.0, "COUNT_ADDITIVE"
    if form_code in ("L-22", "L-38"):
        return "RATIO", 1.0, "RATIO_NON_ADDITIVE"
    for pat in NON_CURRENCY_COLUMN_PATTERNS:
        if re.search(pat, col_header_text):
            if "claim" in col_header_text.lower() or "count" in col_header_text.lower() or "no." in col_header_text.lower():
                return "COUNT", 1.0, "COUNT_ADDITIVE"
            return "RATIO", 1.0, "RATIO_NON_ADDITIVE"
    full_text = " ".join(header_cells) + " " + col_header_text
    for pattern, unit_id, mult in UNIT_RULES:
        if re.search(pattern, full_text, re.IGNORECASE):
            return unit_id, mult, "FLOW_ADDITIVE"
    return "LAKHS", 1.0, "FLOW_ADDITIVE"


class EmpiricalChallengeHarness:
    def __init__(self):
        self.results = []

    def record(self, test_id, category, status, message, details=None):
        self.results.append({
            "test_id": test_id,
            "category": category,
            "status": status,
            "message": message,
            "details": details or {}
        })
        badge = f"[{status}]"
        print(f"{badge:10} | {category:15} | {test_id}: {message}")
        if details:
            for k, v in details.items():
                print(f"             -> {k}: {v}")

    def run_all(self):
        print("=" * 90)
        print("EMPIRICAL ADVERSARIAL CHALLENGE HARNESS - LIFE INSURANCE ARCHITECTURE v3.0")
        print("=" * 90)

        self.test_scd2_multi_version_ledger()
        self.test_zero_double_counting_views()
        self.test_devanagari_crores_regex()
        self.test_non_currency_and_form_exemptions()

        print("\n" + "=" * 90)
        print("CHALLENGE HARNESS EXECUTION SUMMARY:")
        print("=" * 90)
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] in ("FAIL", "VULN_EXPOSED"))
        print(f"Total Challenges Executed: {total}")
        print(f"Passed: {passed}")
        print(f"Failed / Vulnerabilities: {failed}")
        print("=" * 90)
        return failed == 0

    def setup_database(self, engine_name):
        if engine_name == "SQLite":
            conn = sqlite3.connect(":memory:")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.executescript(SQL_DDL)
            cursor = conn.cursor()
            execute_fn = cursor.execute
            executemany_fn = cursor.executemany
            commit_fn = conn.commit
            fetchone_fn = cursor.fetchone
            fetchall_fn = cursor.fetchall
            close_fn = conn.close
        else:
            conn = duckdb.connect(":memory:")
            conn.execute(SQL_DDL)
            execute_fn = conn.execute
            executemany_fn = conn.executemany
            commit_fn = lambda: None
            fetchone_fn = lambda: conn.fetchone()
            fetchall_fn = lambda: conn.fetchall()
            close_fn = conn.close

        # Seed minimal master dimensions
        execute_fn("""
            INSERT INTO dim_company (company_id, company_name, short_name, irda_reg_no, category) VALUES
            ('LIC', 'Life Insurance Corporation of India', 'LIC', '512', 'Public PSU'),
            ('HDFC_LIFE', 'HDFC Life Insurance Co Ltd', 'HDFC Life', '101', 'Private');
        """)
        execute_fn("""
            INSERT INTO dim_period (period_id, financial_year, quarter, fiscal_year_start, quarter_num, quarter_start_date, quarter_end_date, chronological_sequence, is_audited) VALUES
            ('FY2023-24_Q2', 'FY2023-24', 'Q2', 2023, 2, '2023-07-01', '2023-09-30', 2, 0),
            ('FY2024-25_Q2', 'FY2024-25', 'Q2', 2024, 2, '2024-07-01', '2024-09-30', 6, 0);
        """)
        execute_fn("""
            INSERT INTO dim_statement_schedule (schedule_code, schedule_name, statement_type, is_balance_sheet_schedule) VALUES
            ('L-1', 'Revenue Account', 'REVENUE', 0),
            ('L-4', 'Premium Schedule', 'REVENUE', 0);
        """)
        execute_fn("""
            INSERT INTO dim_segment (segment_id, segment_code, line_of_business, fund_type, display_order) VALUES
            ('TOTAL', 'TOTAL', 'TOTAL', 'TOTAL', 1),
            ('PAR_LIFE', 'PAR_LIFE', 'LIFE', 'PARTICIPATING', 2),
            ('NON_PAR', 'NON_PAR', 'LIFE', 'NON_PARTICIPATING', 3),
            ('LINKED', 'LINKED', 'LIFE', 'UNIT_LINKED', 4),
            ('HEALTH', 'HEALTH', 'HEALTH', 'NON_PARTICIPATING', 5),
            ('PENSION', 'PENSION', 'PENSION', 'PARTICIPATING', 6);
        """)
        execute_fn("""
            INSERT INTO dim_reporting_unit (unit_id, unit_code, multiplier_to_lakhs, display_suffix, is_monetary) VALUES
            ('LAKHS', 'LAKHS', 1.0, 'Lakhs', 1),
            ('CRORES', 'CRORES', 100.0, 'Crores', 1);
        """)
        execute_fn("""
            INSERT INTO audit_etl_batches (batch_id, status, source_file_path, source_file_checksum, total_records_processed) VALUES
            (1001, 'SUCCESS', 'Batch1001.xlsx', 'hash1001', 100),
            (1002, 'SUCCESS', 'Batch1002.xlsx', 'hash1002', 100),
            (1003, 'SUCCESS', 'Batch1003.xlsx', 'hash1003', 100);
        """)
        execute_fn("""
            INSERT INTO dim_line_item (line_item_id, schedule_code, canonical_code, canonical_label, statement_section,
                                       classification_axis, parent_line_id, hierarchy_level, is_leaf, is_total, is_subtotal,
                                       normal_balance_sign, aggregation_type, display_order) VALUES
            ('L4_FY', 'L-4', 'L4_FY', 'First Year Premium', 'PREMIUM', 'BY_PRODUCT_TYPE', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 1),
            ('L4_RN', 'L-4', 'L4_RN', 'Renewal Premium', 'PREMIUM', 'BY_PRODUCT_TYPE', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 2),
            ('L4_SG', 'L-4', 'L4_SG', 'Single Premium', 'PREMIUM', 'BY_PRODUCT_TYPE', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 3),
            ('L4_TOT_PROD', 'L-4', 'L4_TOT_PROD', 'Total Premium by Product', 'PREMIUM', 'BY_PRODUCT_TYPE', NULL, 1, 0, 1, 0, 1, 'FLOW_ADDITIVE', 4),
            ('L4_GEO_IN', 'L-4', 'L4_GEO_IN', 'In India Premium', 'PREMIUM', 'BY_GEOGRAPHY', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 5),
            ('L4_GEO_OUT', 'L-4', 'L4_GEO_OUT', 'Outside India Premium', 'PREMIUM', 'BY_GEOGRAPHY', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 6),
            ('L4_GRAND_TOT', 'L-4', 'L4_GRAND_TOT', 'Total Premium', 'PREMIUM', 'SUMMARY_TOTAL', NULL, 0, 0, 1, 0, 1, 'FLOW_ADDITIVE', 7),
            ('L4_SUSPECT', 'L-4', 'L4_SUSPECT', 'Suspect Premium Under Quarantine', 'PREMIUM', 'BY_PRODUCT_TYPE', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 8),
            ('L1_PREM_NET', 'L-1', 'L1_REV_NET_PREMIUM', 'Net Premium Earned', 'POLICYHOLDERS', 'PRIMARY_BREAKDOWN', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 1),
            ('L1_INV_INC', 'L-1', 'L1_REV_INV_INC', 'Investment Income', 'POLICYHOLDERS', 'PRIMARY_BREAKDOWN', NULL, 1, 1, 0, 0, 1, 'FLOW_ADDITIVE', 2),
            ('L1_TOT_INC', 'L-1', 'L1_REV_TOTAL_INC', 'Total Income Policyholders', 'POLICYHOLDERS', 'PRIMARY_BREAKDOWN', NULL, 0, 0, 1, 0, 1, 'FLOW_ADDITIVE', 3);
        """)
        commit_fn()
        return conn, execute_fn, commit_fn, fetchone_fn, fetchall_fn, close_fn

    # -------------------------------------------------------------------------
    # CHALLENGE 1: SCD TYPE 2 NON-DESTRUCTIVE LEDGER
    # -------------------------------------------------------------------------
    def test_scd2_multi_version_ledger(self):
        print("\n--- Running Challenge 1: SCD Type 2 Non-Destructive Ledger ---")
        for engine in ["SQLite", "DuckDB"]:
            conn, execute_fn, commit_fn, fetchone_fn, fetchall_fn, close_fn = self.setup_database(engine)
            try:
                # 1. Insert Initial Version (v1)
                execute_fn("""
                    INSERT INTO fact_financial_statement (
                        fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                        filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                        raw_reported_amount, quarter_amount_lakhs, statement_version_id,
                        is_active, valid_from_batch_id
                    ) VALUES (
                        1001, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL',
                        'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0,
                        100000.0, 100000.0, 1, 1, 1001
                    );
                """)
                commit_fn()

                # Verify v1 exists and is active
                execute_fn("SELECT statement_version_id, is_active, quarter_amount_lakhs FROM fact_financial_statement WHERE fact_id = 1001;")
                row_v1 = fetchone_fn()
                assert row_v1[0] == 1 and row_v1[1] == 1 and float(row_v1[2]) == 100000.0

                # 2. Supersede Version 1 -> Inactive
                execute_fn("UPDATE fact_financial_statement SET is_active = 0, superseded_by_batch_id = 1002 WHERE fact_id = 1001;")
                commit_fn()

                # 3. Insert Version 2 (v2) with EXACT SAME natural business keys
                # Natural Keys: company_id='HDFC_LIFE', period_id='FY2023-24_Q2', schedule_code='L-4',
                #               line_item_id='L4_FY', segment_id='TOTAL', filing_period_id='FY2023-24_Q2',
                #               reporting_basis='AS_REPORTED_ORIGINAL'
                execute_fn("""
                    INSERT INTO fact_financial_statement (
                        fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                        filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                        raw_reported_amount, quarter_amount_lakhs, statement_version_id,
                        is_active, valid_from_batch_id
                    ) VALUES (
                        1002, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL',
                        'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0,
                        105000.0, 105000.0, 2, 1, 1002
                    );
                """)
                commit_fn()

                # 4. Supersede Version 2 -> Inactive, and Insert Version 3 (v3)
                execute_fn("UPDATE fact_financial_statement SET is_active = 0, superseded_by_batch_id = 1003 WHERE fact_id = 1002;")
                execute_fn("""
                    INSERT INTO fact_financial_statement (
                        fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                        filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                        raw_reported_amount, quarter_amount_lakhs, statement_version_id,
                        is_active, valid_from_batch_id
                    ) VALUES (
                        1003, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL',
                        'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0,
                        108000.0, 108000.0, 3, 1, 1003
                    );
                """)
                commit_fn()

                # Check all 3 versions coexist in physical table
                execute_fn("""
                    SELECT statement_version_id, is_active, quarter_amount_lakhs, valid_from_batch_id, superseded_by_batch_id
                    FROM fact_financial_statement
                    WHERE company_id = 'HDFC_LIFE' AND line_item_id = 'L4_FY'
                    ORDER BY statement_version_id ASC;
                """)
                rows = fetchall_fn()
                assert len(rows) == 3, f"Expected 3 versions coexisting, got {len(rows)}"
                assert rows[0][0] == 1 and rows[0][1] == 0 and rows[0][4] == 1002
                assert rows[1][0] == 2 and rows[1][1] == 0 and rows[1][4] == 1003
                assert rows[2][0] == 3 and rows[2][1] == 1 and rows[2][4] is None

                # Query views: ensure only active v3 (108,000 Lakhs) is visible
                execute_fn("""
                    SELECT quarter_amount_lakhs FROM vw_dashboard_financials
                    WHERE company_id = 'HDFC_LIFE' AND line_item_id = 'L4_FY';
                """)
                active_view_rows = fetchall_fn()
                assert len(active_view_rows) == 1, f"Expected 1 active row in view, got {len(active_view_rows)}"
                assert float(active_view_rows[0][0]) == 108000.0, f"Expected 108000, got {active_view_rows[0][0]}"

                # 5. Adversarial: Attempt duplicate insertion of an existing version (v3 again)
                threw_dup_version = False
                try:
                    execute_fn("""
                        INSERT INTO fact_financial_statement (
                            fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                            filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                            raw_reported_amount, quarter_amount_lakhs, statement_version_id,
                            is_active, valid_from_batch_id
                        ) VALUES (
                            1004, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL',
                            'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0,
                            108000.0, 108000.0, 3, 1, 1003
                        );
                    """)
                    commit_fn()
                except Exception:
                    threw_dup_version = True
                    if engine == "DuckDB":
                        try:
                            conn.rollback()
                        except Exception:
                            pass

                assert threw_dup_version, "Constraint uq_fact_grain failed to reject duplicate (business_grain + statement_version_id)!"

                self.record(
                    f"SCD2_MultiVersion_Ledger_{engine}",
                    "SCD2_LEDGER",
                    "PASS",
                    f"Successfully tested 3 successive versions for identical natural grain; verified full audit trail and clean active view isolation.",
                    {"Engine": engine, "Versions_Stored": 3, "Active_Version": 3, "Active_Amount": 108000.0}
                )
            except Exception as e:
                self.record(
                    f"SCD2_MultiVersion_Ledger_{engine}",
                    "SCD2_LEDGER",
                    "FAIL",
                    f"SCD Type 2 test encountered unexpected error: {e}",
                    {"Engine": engine, "Error": str(e)}
                )
            finally:
                close_fn()

    # -------------------------------------------------------------------------
    # CHALLENGE 2: ZERO DOUBLE-COUNTING GUARANTEE
    # -------------------------------------------------------------------------
    def test_zero_double_counting_views(self):
        print("\n--- Running Challenge 2: Zero Double-Counting Guarantee ---")
        for engine in ["SQLite", "DuckDB"]:
            conn, execute_fn, commit_fn, fetchone_fn, fetchall_fn, close_fn = self.setup_database(engine)
            try:
                # Insert comprehensive test dataset for Form L-4:
                # Leaves under BY_PRODUCT_TYPE (TOTAL segment):
                #   L4_FY = 100,000
                #   L4_RN = 300,000
                #   L4_SG = 100,000
                # Subtotal/Total under BY_PRODUCT_TYPE (TOTAL segment):
                #   L4_TOT_PROD = 500,000 (is_total=1, is_leaf=0)
                # Leaves under BY_GEOGRAPHY (TOTAL segment):
                #   L4_GEO_IN = 450,000 (is_leaf=1)
                #   L4_GEO_OUT = 50,000 (is_leaf=1)
                # Summary Total (TOTAL segment):
                #   L4_GRAND_TOT = 500,000 (is_total=1, is_leaf=0)
                # Segment Constituent Leaves for L4_FY (PAR_LIFE=40k, NON_PAR=30k, LINKED=20k, HEALTH=5k, PENSION=5k -> Sum = 100k):
                # Comparative Period Restatements (RESTATED_COMPARATIVE) for L4_FY = 102k:
                # Quarantined fact row for L4_RN = 999,999:

                facts = [
                    # 1. Standard Leaves (Product Axis, TOTAL Segment, Original) -> True total = 500,000
                    (2001, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 'VERIFIED', 1, 1001),
                    (2002, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_RN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 300000.0, 300000.0, 'VERIFIED', 1, 1001),
                    (2003, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_SG', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 100000.0, 100000.0, 'VERIFIED', 1, 1001),

                    # 2. Product Totals & Geo Breakdown (Double Counting Trap 1)
                    (2004, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_TOT_PROD', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 500000.0, 500000.0, 'VERIFIED', 1, 1001),
                    (2005, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GEO_IN', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 450000.0, 450000.0, 'VERIFIED', 1, 1001),
                    (2006, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GEO_OUT', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 50000.0, 50000.0, 'VERIFIED', 1, 1001),
                    (2007, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_GRAND_TOT', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 500000.0, 500000.0, 'VERIFIED', 1, 1001),

                    # 3. Constituent Segment Breakdown for L4_FY (Double Counting Trap 2: Segments)
                    (2008, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'PAR_LIFE', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 40000.0, 40000.0, 'VERIFIED', 1, 1001),
                    (2009, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'NON_PAR', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 30000.0, 30000.0, 'VERIFIED', 1, 1001),
                    (2010, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'LINKED', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 20000.0, 20000.0, 'VERIFIED', 1, 1001),
                    (2011, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'HEALTH', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 5000.0, 5000.0, 'VERIFIED', 1, 1001),
                    (2012, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'PENSION', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 5000.0, 5000.0, 'VERIFIED', 1, 1001),

                    # 4. Comparative Restatement for Q2 FY24 filed in Q2 FY25 (Double Counting Trap 3: Restatement)
                    (2013, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_FY', 'TOTAL', 'FY2024-25_Q2', 'RESTATED_COMPARATIVE', 'LAKHS', 1.0, 102000.0, 102000.0, 'VERIFIED', 1, 1002),

                    # 5. Quarantined Corrupted Fact (Double Counting Trap 4: Quarantine Leakage)
                    (2014, 'HDFC_LIFE', 'FY2023-24_Q2', 'L-4', 'L4_SUSPECT', 'TOTAL', 'FY2023-24_Q2', 'AS_REPORTED_ORIGINAL', 'LAKHS', 1.0, 999999.0, 999999.0, 'QUARANTINED', 1, 1003),
                ]

                for f in facts:
                    execute_fn("""
                        INSERT INTO fact_financial_statement (
                            fact_id, company_id, period_id, schedule_code, line_item_id, segment_id,
                            filing_period_id, reporting_basis, source_unit_id, unit_multiplier,
                            raw_reported_amount, quarter_amount_lakhs, data_quality_status,
                            statement_version_id, valid_from_batch_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, f)
                commit_fn()

                # Calculate Naive Raw Sum in fact_financial_statement
                execute_fn("""
                    SELECT SUM(quarter_amount_lakhs) FROM fact_financial_statement
                    WHERE company_id = 'HDFC_LIFE' AND schedule_code = 'L-4';
                """)
                naive_sum = float(fetchone_fn()[0])
                # Expected naive sum:
                # 100k + 300k + 100k + 500k + 450k + 50k + 500k (2000k)
                # + 40k + 30k + 20k + 5k + 5k (100k segments)
                # + 102k (comparative)
                # + 999,999 (quarantined)
                # = 3,201,999 Lakhs (over 640% inflated!)

                # Query hardened view 1: vw_dashboard_financials
                execute_fn("""
                    SELECT SUM(signed_quarter_lakhs), COUNT(*) FROM vw_dashboard_financials
                    WHERE company_id = 'HDFC_LIFE' AND schedule_code = 'L-4';
                """)
                dash_row = fetchone_fn()
                dash_sum = float(dash_row[0])
                dash_count = int(dash_row[1])

                # Query hardened view 2: vw_leaf_financials
                execute_fn("""
                    SELECT SUM(signed_quarter_lakhs), COUNT(*) FROM vw_leaf_financials
                    WHERE company_id = 'HDFC_LIFE' AND schedule_code = 'L-4';
                """)
                leaf_row = fetchone_fn()
                leaf_sum = float(leaf_row[0])
                leaf_count = int(leaf_row[1])

                # Both views must equal EXACTLY 500,000 Lakhs and exactly 3 leaf rows (L4_FY, L4_RN, L4_SG)
                assert dash_sum == 500000.0, f"vw_dashboard_financials sum was {dash_sum}, expected 500,000.0"
                assert leaf_sum == 500000.0, f"vw_leaf_financials sum was {leaf_sum}, expected 500,000.0"
                assert dash_count == 3, f"vw_dashboard_financials count was {dash_count}, expected 3"
                assert leaf_count == 3, f"vw_leaf_financials count was {leaf_count}, expected 3"

                self.record(
                    f"Zero_Double_Counting_{engine}",
                    "DOUBLE_COUNTING",
                    "PASS",
                    f"Naive sum of {naive_sum:,.0f} Lakhs (>640% inflated) was completely filtered down to exact 500,000 Lakhs across both vw_dashboard_financials and vw_leaf_financials.",
                    {
                        "Engine": engine,
                        "Naive_Fact_Sum": naive_sum,
                        "vw_dashboard_sum": dash_sum,
                        "vw_leaf_sum": leaf_sum,
                        "Active_Leaf_Count": dash_count,
                        "Segment_Leakage": 0.0,
                        "Comparative_Restatement_Leakage": 0.0,
                        "Hierarchy_Total_Leakage": 0.0,
                        "Quarantine_Leakage": 0.0
                    }
                )
            except Exception as e:
                self.record(
                    f"Zero_Double_Counting_{engine}",
                    "DOUBLE_COUNTING",
                    "FAIL",
                    f"Zero double counting verification failed: {e}",
                    {"Engine": engine, "Error": str(e)}
                )
            finally:
                close_fn()

    # -------------------------------------------------------------------------
    # CHALLENGE 3: DEVANAGARI CRORES REGEX & NUKTA TEST
    # -------------------------------------------------------------------------
    def test_devanagari_crores_regex(self):
        print("\n--- Running Challenge 3: Devanagari Crores Regex & Nukta ---")
        crores_regex_str, unit_name, multiplier = UNIT_RULES[0]
        crores_regex = re.compile(crores_regex_str, re.IGNORECASE)

        # Matrix of test strings observed in IRDAI filings and Hindi quarterly disclosures
        nukta_char = "\u093c"
        test_cases = [
            ("(राशि करोड़ रुपये में)", True, "Devanagari with Nukta U+093C in parentheses"),
            ("राशि करोड़ रुपये में", True, "Devanagari with Nukta U+093C without parentheses"),
            ("राशि करोड रुपये में", True, "Devanagari without Nukta"),
            ("(राशि करोड में)", True, "Short Devanagari without Nukta"),
            ("(राशि करोड़ में)", True, "Short Devanagari with Nukta"),
            ("करोड़", True, "Exact Devanagari with Nukta"),
            ("करोड", True, "Exact Devanagari without Nukta"),
            ("\u0915\u0930\u094b\u0921\u093c", True, "Explicit Unicode codepoint sequence with Nukta"),
            ("(Rs. in Crores)", True, "English standard Crores"),
            ("(₹ in Crs.)", True, "English abbreviated Crs with rupee symbol"),
            ("Amount in Crores", True, "English plain header"),
            ("Total Premium (Crores)", True, "English schedule header"),
            ("(राशि करोड़ रुपये में / Rs. in Crores)", True, "Bilingual joint header with Nukta"),
            ("(राशि करोड रुपये में / Rs. in Crores)", True, "Bilingual joint header without Nukta"),
            ("(Rs. in Lakhs)", False, "English Lakhs - should NOT match Crores"),
            ("(राशि लाख रुपये में)", False, "Devanagari Lakhs - should NOT match Crores"),
            ("(Rs. in Thousands)", False, "English Thousands - should NOT match Crores"),
            ("(₹ in '000)", False, "Thousands apostrophe - should NOT match Crores"),
        ]

        all_passed = True
        failed_cases = []
        for text, should_match, desc in test_cases:
            match = bool(crores_regex.search(text))
            if match != should_match:
                all_passed = False
                failed_cases.append((text, should_match, match, desc))

        if all_passed:
            self.record(
                "Devanagari_Crores_Regex_Nukta",
                "UNIT_REGEX",
                "PASS",
                f"Devanagari Crores regex passed all {len(test_cases)} adversarial test strings including Nukta U+093C variants.",
                {"Total_Tested": len(test_cases), "Pattern": crores_regex_str}
            )
        else:
            self.record(
                "Devanagari_Crores_Regex_Nukta",
                "UNIT_REGEX",
                "FAIL",
                f"Devanagari Crores regex failed on {len(failed_cases)} test cases.",
                {"Failed_Cases": failed_cases}
            )

        # Integration test with detect_column_group_unit
        unit_id, mult, agg_type = detect_column_group_unit(["(राशि करोड़ रुपये में)"], "L-4", "Total Premium")
        assert unit_id == "CRORES" and mult == 100.0, f"Expected CRORES/100.0, got {unit_id}/{mult}"

        unit_id_en, mult_en, _ = detect_column_group_unit(["(Rs. in Crores)"], "L-1", "Net Premium")
        assert unit_id_en == "CRORES" and mult_en == 100.0, f"Expected CRORES/100.0, got {unit_id_en}/{mult_en}"

        self.record(
            "Detect_Column_Group_Unit_Integration",
            "UNIT_ENGINE",
            "PASS",
            "detect_column_group_unit correctly resolved Devanagari with Nukta to CRORES with 100.0 multiplier.",
            {"Detected_Unit": unit_id, "Multiplier": mult}
        )

    # -------------------------------------------------------------------------
    # CHALLENGE 4: NON-CURRENCY & ACTUARIAL EXEMPTIONS
    # -------------------------------------------------------------------------
    def test_non_currency_and_form_exemptions(self):
        print("\n--- Running Challenge 4: Non-Currency and Form Exemptions ---")
        # 1. Claims Paid Monetary vs Claims Paid Count
        # Monetary: "Claims Paid (Rs in Thousands)" -> must scale by 0.01
        unit_id_mon, mult_mon, agg_mon = detect_column_group_unit(["Claims Paid (Rs in Thousands)"], "L-7", "Claims Paid")
        assert unit_id_mon == "THOUSANDS" and mult_mon == 0.01, f"Expected THOUSANDS/0.01, got {unit_id_mon}/{mult_mon}"

        # Count: "Number of claims paid" -> must be COUNT, multiplier 1.0
        unit_id_cnt, mult_cnt, agg_cnt = detect_column_group_unit(["Schedule Data"], "L-7", "Number of claims paid")
        assert unit_id_cnt == "COUNT" and mult_cnt == 1.0, f"Expected COUNT/1.0, got {unit_id_cnt}/{mult_cnt}"

        # 2. Form L-38 Persistency Ratio Exemption
        unit_id_l38, mult_l38, agg_l38 = detect_column_group_unit(["(Amount in Rs. Lakhs)"], "L-38", "13th Month Persistency")
        assert unit_id_l38 == "RATIO" and mult_l38 == 1.0 and agg_l38 == "RATIO_NON_ADDITIVE", f"Form L-38 persistency ratio failed: got {unit_id_l38}/{mult_l38}/{agg_l38}"

        # 3. Form L-41 Grievances / Complaints Exemption
        unit_id_l41, mult_l41, agg_l41 = detect_column_group_unit(["(Amount in Rs. Lakhs)"], "L-41", "Complaints Outstanding")
        assert unit_id_l41 == "COUNT" and mult_l41 == 1.0 and agg_l41 == "COUNT_ADDITIVE", f"Form L-41 failed: got {unit_id_l41}/{mult_l41}/{agg_l41}"

        self.record(
            "Non_Currency_Exemptions",
            "NON_CURRENCY",
            "PASS",
            "Verified non-currency protection: Claims Paid monetary preserved at 0.01 multiplier, Claims count set to COUNT, Form L-38 persistency recognized as RATIO.",
            {"Claims_Paid_Monetary": f"{unit_id_mon} ({mult_mon})", "Claims_Count": f"{unit_id_cnt} ({mult_cnt})", "L38_Persistency": f"{unit_id_l38} ({mult_l38})"}
        )


if __name__ == "__main__":
    harness = EmpiricalChallengeHarness()
    success = harness.run_all()
    sys.exit(0 if success else 1)
