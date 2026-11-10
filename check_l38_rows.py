import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-38"]

print("L-38 Rows 1-34:")
for r in range(1, min(ws.max_row + 1, 35)):
    row_text = []
    for c in range(1, 15):
        val = ws.cell(r, c).value
        if val is not None and str(val).strip() != '':
            row_text.append(f"C{c}:{str(val).strip()[:35]}")
    if row_text:
        print(f"R{r:2d}: " + " | ".join(row_text[:6]))

wb.close()
