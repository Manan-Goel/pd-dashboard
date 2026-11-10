import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

print("L-36 Rows 80-140:")
for r in range(80, min(ws.max_row + 1, 140)):
    c1 = str(ws.cell(r, 1).value or '')
    c2 = str(ws.cell(r, 2).value or '')
    c3 = str(ws.cell(r, 3).value or '')
    text = f"{c1} {c2} {c3}".strip()
    if text:
        # print row with some values
        vals = [f"C{c}:{ws.cell(r, c).value}" for c in [4, 5, 6, 7, 44, 45, 46, 47] if ws.cell(r, c).value is not None]
        print(f"R{r:3d}: {text[:45]} -> " + " | ".join(vals[:4]))

wb.close()
