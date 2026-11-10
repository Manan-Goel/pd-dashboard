import openpyxl
import re

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-22"]

print("Searching L-22 for Persistency, Conservation, ROE, etc...")
for r in range(1, ws.max_row + 1):
    val = ws.cell(r, 2).value
    val1 = ws.cell(r, 1).value
    if val or val1:
        text = f"{val1 or ''} {val or ''}"
        if any(w in text.lower() for w in ['persistency', 'conservation', 'roe', 'return on equity', 'growth', 'expense', 'ratio']):
            # Print row and the Q1, Q2, etc. values if any
            vals = [str(ws.cell(r, c).value) for c in [3, 10, 17, 24] if ws.cell(r, c).value is not None]
            print(f"R{r:3d}: {text[:50]} -> sample vals: {vals[:4]}")

wb.close()
