import openpyxl
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

print("Row 30, 46, 79 across cols 227 to 240 for Q12:")
for r in [10, 11, 29, 30, 45, 46, 78, 79]:
    vals = [f"C{c}:{ws.cell(r, c).value}" for c in range(227, 241) if ws.cell(r, c).value is not None]
    print(f"R{r:2d}: " + " | ".join(vals))

wb.close()
