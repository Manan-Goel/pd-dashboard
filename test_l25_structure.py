import openpyxl
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-25 (i)"]

def clean_val(v):
    if v is None: return 0.0
    s = str(v).strip().replace(',', '')
    if s in ('', '-', 'NA', 'Nil', 'NIL', '.'): return 0.0
    try: return float(s)
    except: return 0.0

def clean_int(v):
    return int(round(clean_val(v)))

# Scan blocks in L-25 (i)
blocks = []
current_fy = None
for c in range(1, ws.max_column + 1):
    v1 = ws.cell(1, c).value
    v2 = ws.cell(2, c).value
    if v1 and re.search(r'202[0-9]-[0-9]{2}', str(v1)):
        current_fy = "FY" + re.search(r'202[0-9]-[0-9]{2}', str(v1)).group(0)
    q_match = None
    for val in [v2, v1]:
        if val and re.search(r'\bQ[1-4]\b', str(val), re.I):
            q_match = re.search(r'\bQ[1-4]\b', str(val), re.I).group(0).upper()
            break
    if q_match:
        blocks.append({'fy': current_fy, 'q': q_match, 'col': c})

print(f"L-25 (i) total blocks: {len(blocks)}")

# In L-25 (i), let's see which column holds Total New Business or Total Premium
# In row 11:
# Col 3: New Business - Rural (Policies, Premium, SA)
# Col 6: New Business - Urban (Policies, Premium, SA)
# Col 9: Total New Business (Policies, Premium, SA)
# Col 12: Renewal (Policies, Premium, SA)
# Col 15: Total Premium (Policies, Premium, SA)

for b in blocks[:4]:
    sc = b['col']
    # Check row 11 and 12
    cols_summary = []
    for c in range(sc, min(sc + 18, ws.max_column + 1)):
        r11 = str(ws.cell(11, c).value or '').replace('\n', ' ')
        r12 = str(ws.cell(12, c).value or '').replace('\n', ' ')
        if r11 or r12:
            cols_summary.append(f"C{c}: {r11} | {r12}")
    print(f"\nBlock {b['fy']} {b['q']} (start col {sc}):")
    for cs in cols_summary[:6]:
        print(f"  {cs}")

wb.close()
