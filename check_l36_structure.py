import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

# Block FY2023-24 Q1 is cols 1..20
for c in range(1, 21):
    texts = [f"R{r}:{ws.cell(r, c).value}" for r in range(7, 13) if ws.cell(r, c).value is not None]
    if texts:
        print(f"Col {c:2d}: " + " | ".join(texts))

# Inspect lines in L-36 that have totals or individual/group headings
print("\nL-36 Key Headings (Rows 10 to 135):")
for r in range(10, min(ws.max_row + 1, 135)):
    c2 = str(ws.cell(r, 2).value or '').strip()
    c3 = str(ws.cell(r, 3).value or '').strip()
    if c2 or c3:
        if any(w in (c2 + " " + c3).lower() for w in ['total', 'individual', 'group', 'single', 'renewal', 'first year']):
            # Print row with Q3 or Q4 values
            # Let's check Col 4, 5, 6, 7 (Q1) and Col 24, 25, 26, 27 (Q2) or later
            v_sample = [f"C{c}:{ws.cell(r, c).value}" for c in [4, 5, 6, 7, 44, 45, 46, 47, 84, 85, 86, 87] if ws.cell(r, c).value is not None]
            print(f"R{r:3d}: C2='{c2}' | C3='{c3}' -> " + " | ".join(v_sample[:4]))

wb.close()
