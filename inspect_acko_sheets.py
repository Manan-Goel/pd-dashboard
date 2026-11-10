import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", read_only=True)
sheet_names = wb.sheetnames
print(f"Total sheets: {len(sheet_names)}")
print("Sheets:", sheet_names)

# Inspect key sheets relevant to the 64 fields:
# L-1 (Revenue A/c), L-2 (P&L A/c), L-3 (Balance Sheet), L-4 (Premium), L-5 (Commission), L-6 (Opex), L-7 (Benefits Paid / Claims)
# L-8 (Share Capital), L-9 (Reserves), L-10 (Borrowings)
# L-22 (Analytical Ratios), L-25 (i) (Geographical), L-25 (ii)
# L-32 (Solvency), L-36 (Business Details), L-37 (Channels), L-38 (Intermediary/Productivity)
# L-41 (Grievances), L-44 / L-45 (Offices, Company Info)
wb.close()
