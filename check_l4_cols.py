import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-4"]

for c in range(1, ws.max_column + 1):
    vals = [f"R{r}:{ws.cell(r, c).value}" for r in range(1, 13) if ws.cell(r, c).value is not None]
    if vals:
        print(f"Col {c:2d}: " + " | ".join(vals))

wb.close()
