import openpyxl
import sys

sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-36"]

# Check Q11 (cols 201-226) and Q12 (cols 227-251)
for q_name, sc, ec in [('Q11', 201, 226), ('Q12', 227, 251)]:
    print(f"\n--- Checking {q_name} in L-36 (cols {sc}..{ec}) ---")
    for r in range(8, 14):
        vals = [f"C{c}:{ws.cell(r, c).value}" for c in range(sc, min(sc + 12, ec + 1)) if ws.cell(r, c).value is not None]
        if vals:
            print(f"R{r:2d}: " + " | ".join(vals))
            
    # Check rows with values in Q11/Q12
    non_zeros = []
    for r in range(11, ws.max_row + 1):
        for c in range(sc, ec + 1):
            v = ws.cell(r, c).value
            if v not in (None, '-', 'NA', 0, '0'):
                c2 = str(ws.cell(r, 2).value or '')
                c3 = str(ws.cell(r, 3).value or '')
                c_part = str(ws.cell(r, sc + 2).value or '') # particulars in block
                non_zeros.append((r, c, f"{c2} {c3} | {c_part}", v))
    print(f"Found {len(non_zeros)} non-zero cells in {q_name}:")
    for nz in non_zeros[:15]:
        print(f"  Row {nz[0]}, Col {nz[1]}: {nz[2][:40]} = {nz[3]}")

wb.close()
