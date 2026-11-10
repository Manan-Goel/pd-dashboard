import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-25 (i)"]

print("L-25 (i) rows 10-60:")
for r in range(10, 60):
    val_state = ws.cell(r, 2).value
    val_sl = ws.cell(r, 1).value
    if val_state or val_sl:
        # Check non-empty columns
        non_empty = [f"C{c}:{ws.cell(r, c).value}" for c in range(1, 15) if ws.cell(r, c).value is not None]
        print(f"R{r:2d}: " + " | ".join(non_empty[:6]))

wb.close()
