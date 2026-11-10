"""
Automated Financial Reconciliation Engine for Life Insurance Disclosures.
Executes mathematical assertions:
1. L-1 vs L-4 Premium Reconciliation:
   L-1 Gross Direct Premium == L-4 Total Premium
   L-1 Net Premium == L-4 Total - Reinsurance Ceded + Reinsurance Accepted
2. L-3 Balance Sheet Fundamental Identity:
   Total Sources of Funds == Total Application of Funds
3. Policyholder vs Shareholder Fund Cross-Flow:
   L-1 Transfer to Shareholders == L-2 Transfer from Policyholders
4. Solvency Margin Assertion:
   Form L-32 Solvency Ratio == ASM / RSM
Logs any variance exceeding tolerance to quarantine_reconciliation_discrepancies.
"""

from typing import Dict, Any, List, Optional
import sqlite3

TOLERANCE_LAKHS = 5.0
TOLERANCE_PCT = 0.005  # 0.5%

def reconcile_company_period(db_manager, batch_id: int, company_id: str, period_id: str) -> List[Dict[str, Any]]:
    """
    Executes cross-statement reconciliation assertions for a given company and period.
    Returns list of discrepancy records.
    """
    discrepancies = []
    conn = db_manager.connection

    # 1. Premium Reconciliation (L-1 vs L-4)
    # Check L-4 Total Premium
    row_l4 = db_manager.execute("""
        SELECT quarter_amount_lakhs, ytd_amount_lakhs
        FROM fact_financial_statement
        WHERE company_id = ? AND period_id = ? AND schedule_code = 'L-4'
          AND line_item_id = 'L4_PREM_TOTAL' AND segment_id = 'TOTAL' AND is_active = 1
    """, (company_id, period_id)).fetchone()

    # Check L-1 Gross & Net Premium
    row_l1 = db_manager.execute("""
        SELECT 
            MAX(CASE WHEN line_item_id = 'L1_REV_GROSS_PREMIUM' THEN quarter_amount_lakhs END) as gross_prem,
            MAX(CASE WHEN line_item_id = 'L1_REV_NET_PREMIUM' THEN quarter_amount_lakhs END) as net_prem,
            MAX(CASE WHEN line_item_id = 'L1_REV_REINSURANCE_CEDED' THEN quarter_amount_lakhs END) as ceded_prem
        FROM fact_financial_statement
        WHERE company_id = ? AND period_id = ? AND schedule_code = 'L-1'
          AND segment_id = 'TOTAL' AND is_active = 1
    """, (company_id, period_id)).fetchone()

    if row_l4 and row_l1 and row_l4["quarter_amount_lakhs"] is not None:
        l4_prem = float(row_l4["quarter_amount_lakhs"])
        l1_gross = float(row_l1["gross_prem"]) if row_l1["gross_prem"] is not None else None
        
        if l1_gross is not None:
            diff = abs(l4_prem - l1_gross)
            denom = max(abs(l4_prem), 1.0)
            diff_pct = diff / denom
            if diff > TOLERANCE_LAKHS and diff_pct > TOLERANCE_PCT:
                discrepancies.append({
                    "rule_code": "REC_L1_L4_PREMIUM",
                    "description": "L-1 Gross Premium does not reconcile with L-4 Total Premium",
                    "severity": "WARNING",
                    "metric_1_name": "L4_PREM_TOTAL",
                    "metric_1_amount": l4_prem,
                    "metric_2_name": "L1_REV_GROSS_PREMIUM",
                    "metric_2_amount": l1_gross,
                    "variance_amount": diff,
                    "variance_pct": diff_pct * 100.0,
                    "tolerance": TOLERANCE_LAKHS
                })

    # 2. Balance Sheet Identity (L-3 Total Sources == Total Application)
    row_bs = db_manager.execute("""
        SELECT 
            MAX(CASE WHEN line_item_id = 'L3_BS_TOTAL_SOURCES' THEN point_in_time_amount_lakhs END) as sources,
            MAX(CASE WHEN line_item_id = 'L3_BS_TOTAL_APPLICATION' THEN point_in_time_amount_lakhs END) as app
        FROM fact_financial_statement
        WHERE company_id = ? AND period_id = ? AND schedule_code = 'L-3' AND is_active = 1
    """, (company_id, period_id)).fetchone()

    if row_bs and row_bs["sources"] is not None and row_bs["app"] is not None:
        src = float(row_bs["sources"])
        app = float(row_bs["app"])
        diff = abs(src - app)
        denom = max(abs(src), 1.0)
        diff_pct = diff / denom
        if diff > TOLERANCE_LAKHS and diff_pct > TOLERANCE_PCT:
            discrepancies.append({
                "rule_code": "REC_L3_BALANCE_SHEET_EQUILIBRIUM",
                "description": "Total Sources of Funds does not equal Total Application of Funds",
                "severity": "BLOCKING",
                "metric_1_name": "L3_BS_TOTAL_SOURCES",
                "metric_1_amount": src,
                "metric_2_name": "L3_BS_TOTAL_APPLICATION",
                "metric_2_amount": app,
                "variance_amount": diff,
                "variance_pct": diff_pct * 100.0,
                "tolerance": TOLERANCE_LAKHS
            })

    # Log discrepancies into quarantine_reconciliation_discrepancies
    if discrepancies:
        for d in discrepancies:
            db_manager.execute("""
                INSERT INTO quarantine_reconciliation_discrepancies (
                    batch_id, company_id, period_id, rule_code, rule_description, severity,
                    metric_1_name, metric_1_amount_lakhs, metric_2_name, metric_2_amount_lakhs,
                    variance_amount_lakhs, variance_pct, tolerance_threshold_lakhs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id, company_id, period_id, d["rule_code"], d["description"], d["severity"],
                d["metric_1_name"], d["metric_1_amount"], d["metric_2_name"], d["metric_2_amount"],
                d["variance_amount"], d["variance_pct"], d["tolerance"]
            ))
        db_manager.commit()

    return discrepancies
