import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def check_all_quarter_values(sheet_name, row_target, col_step, max_blocks=12):
    ws = wb[sheet_name]
    print(f"\n--- Checking {sheet_name} across quarters ---")
    # find row matching row_target
    matched_row = None
    for r in range(1, ws.max_row + 1):
        for c in range(1, 5):
            val = str(ws.cell(r, c).value or '')
            if row_target.lower() in val.lower():
                matched_row = r
                break
        if matched_row:
            break
            
    print(f"Matched row {matched_row} for target '{row_target}'")
    if matched_row:
        # print non-empty values in that row
        vals = [(c, ws.cell(matched_row, c).value) for c in range(1, ws.max_column + 1) if ws.cell(matched_row, c).value is not None]
        print(f"Values ({len(vals)} non-empty): {vals[:15]}")

check_all_quarter_values("L-4", "TOTAL PREMIUM", 1)
check_all_quarter_values("L-1", "Premiums earned", 1)
check_all_quarter_values("L-2", "Profit After Tax", 1)
check_all_quarter_values("L-32", "Solvency Ratio", 1)
check_all_quarter_values("L-38", "Corporate Agents-Banks", 1)
check_all_quarter_values("L-38", "Direct Business", 1)

wb.close()
