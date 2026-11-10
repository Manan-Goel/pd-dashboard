import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws_l4 = wb['L-4']
print("L-4 Q2 (Cols 8-14):")
for r in range(10, 20):
    vals = [f"C{c}:{ws_l4.cell(r, c).value}" for c in range(8, 15) if ws_l4.cell(r, c).value is not None]
    print(f"R{r:2d}: " + " | ".join(vals))

ws_l36 = wb['L-36']
print("\nL-36 Q2 (Cols 21-40) rows with values > 0:")
for r in range(10, ws_l36.max_row + 1):
    vals = [(c, ws_l36.cell(r, c).value) for c in range(21, 41) if ws_l36.cell(r, c).value not in (None, '-', 'NA', 0, '0')]
    if vals:
        c2 = ws_l36.cell(r, 2).value or ''
        c3 = ws_l36.cell(r, 3).value or ''
        print(f"R{r:3d} [{c2} {c3}]: {vals}")

wb.close()
