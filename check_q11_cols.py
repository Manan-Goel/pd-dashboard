import openpyxl
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

print("Cols 201 to 226 in L-36 (Rows 8 to 14):")
for c in range(201, 226):
    vals = [f"R{r}:{ws.cell(r, c).value}" for r in range(8, 15) if ws.cell(r, c).value is not None]
    if vals:
        print(f"Col {c:3d}: " + " | ".join(vals))

wb.close()
