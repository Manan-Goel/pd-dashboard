import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def dump_sheet_columns(sheet_name, max_r=25):
    ws = wb[sheet_name]
    print(f"\n==================== {sheet_name} Headers & Sample Rows ====================")
    for r in range(1, max_r + 1):
        vals = [ws.cell(r, c).value for c in range(1, 35)]
        non_empty = [(c, str(v).replace('\n', ' ')[:30]) for c, v in enumerate(vals, 1) if v is not None and str(v).strip() != '']
        if non_empty:
            print(f"R{r:2d}: " + " | ".join(f"C{c}:{v}" for c, v in non_empty[:10]))

dump_sheet_columns("L-36", 25)
dump_sheet_columns("L-37", 25)
dump_sheet_columns("L-38", 25)
dump_sheet_columns("L-22", 30)

wb.close()
