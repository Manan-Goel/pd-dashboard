import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

section_rows = [11, 12, 21, 30, 38, 48, 58, 67, 76, 92, 93, 102, 111, 120]

print("Section Header Rows across quarters in L-36:")
for r in section_rows:
    c2 = ws.cell(r, 2).value or ''
    c3 = ws.cell(r, 3).value or ''
    title = f"{c2} {c3}".strip()
    
    # check values for Q3 (cols 44-47), Q4 (cols 64-67), Q5 (cols 84-87), Q8 (cols 144-147)
    vals = []
    for q_idx in range(12):
        # find column for quarter
        col_start = 4 + q_idx * 20
        p = ws.cell(r, col_start).value
        pol = ws.cell(r, col_start + 1).value
        lives = ws.cell(r, col_start + 2).value
        sa = ws.cell(r, col_start + 3).value
        if any(v not in (None, '-', 'NA') for v in [p, pol, lives, sa]):
            vals.append(f"Q{q_idx+1}: prem={p}, pol={pol}, lives={lives}, sa={sa}")
            
    print(f"\nR{r:3d} [{title}]:")
    for v in vals:
        print(f"   {v}")

wb.close()
