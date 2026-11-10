import sqlite3
import json

conn = sqlite3.connect("life_insurance.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*135)
print("VERIFICATION OF 64 STANDARDIZED METRICS FOR ACKO LIFE INSURANCE (12 QUARTERS)")
print("="*135)

rows = cur.execute("""
    SELECT 
        period_id, 
        gross_written_premium, 
        financial_year_premium, 
        total_single_premium, 
        renewal_premium,
        total_individual_premium,
        total_group_premium,
        total_policies,
        group_lives_covered,
        total_sum_assured,
        solvency_ratio,
        profit_after_tax,
        net_worth,
        avg_premium_growth_pct,
        policy_sales_growth_pct
    FROM fact_company_quarterly_metrics
    WHERE company_id = 'ACKO_LIFE'
    ORDER BY period_id
""").fetchall()

def fmt_f(v, d=2):
    return f"{v:<12.{d}f}" if v is not None else f"{'-':<12}"

def fmt_i(v):
    return f"{v:<8d}" if v is not None else f"{'-':<8}"

print(f"{'Period':<14} | {'GWP (Lakhs)':<12} | {'FY Prem':<10} | {'Single':<10} | {'Renewal':<10} | {'Policies':<8} | {'Lives':<8} | {'SA (Lakhs)':<12} | {'Solvency':<8} | {'PAT':<10} | {'Net Worth':<10} | {'Prem Grw%':<10}")
print("-" * 140)
for r in rows:
    p_grw = f"{r['avg_premium_growth_pct']}%" if r['avg_premium_growth_pct'] is not None else "-"
    gwp = fmt_f(r['gross_written_premium'])
    fyp = fmt_f(r['financial_year_premium'])
    sp = fmt_f(r['total_single_premium'])
    rp = fmt_f(r['renewal_premium'])
    pol = fmt_i(r['total_policies'])
    lives = fmt_i(r['group_lives_covered'])
    sa = fmt_f(r['total_sum_assured'])
    solv = fmt_f(r['solvency_ratio'])
    pat = fmt_f(r['profit_after_tax'])
    nw = fmt_f(r['net_worth'])
    print(f"{r['period_id']:<14} | {gwp[:12]} | {fyp[:10]} | {sp[:10]} | {rp[:10]} | {pol[:8]} | {lives[:8]} | {sa[:12]} | {solv[:8]} | {pat[:10]} | {nw[:10]} | {p_grw:<10}")

print("\n" + "="*135)
print("DETAILED VIEW OF ALL 64 FIELDS FOR LATEST QUARTER (FY2025-26_Q4)")
print("="*135)
latest = cur.execute("SELECT * FROM fact_company_quarterly_metrics WHERE company_id = 'ACKO_LIFE' AND period_id = 'FY2025-26_Q4'").fetchone()
for col in latest.keys():
    print(f"  {col:<35} : {latest[col]}")

print("\n" + "="*135)
print("GEOGRAPHICAL DISTRIBUTION SUMMARY (Field 43)")
print("="*135)
geo_counts = cur.execute("""
    SELECT period_id, COUNT(*) as state_count, SUM(total_policies) as tot_pol, SUM(total_premium_lakhs) as tot_prem
    FROM fact_geographical_distribution
    WHERE company_id = 'ACKO_LIFE'
    GROUP BY period_id
    ORDER BY period_id
""").fetchall()
for gc in geo_counts:
    print(f"  {gc['period_id']} -> {gc['state_count']} regions mapped | Policies: {gc['tot_pol']} | Premium: {gc['tot_prem']:.2f} Lakhs")

print("\n" + "="*135)
print("PERSISTENCY COHORTS SUMMARY (Field 41)")
print("="*135)
p_counts = cur.execute("""
    SELECT period_id, COUNT(*) as cohort_count
    FROM fact_persistency_cohorts
    WHERE company_id = 'ACKO_LIFE'
    GROUP BY period_id
    ORDER BY period_id
""").fetchall()
for pc in p_counts:
    print(f"  {pc['period_id']} -> {pc['cohort_count']} persistency cohort entries")

conn.close()
