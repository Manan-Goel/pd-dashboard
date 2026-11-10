import openpyxl

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def inspect_sheet(sheet_name, max_rows=60):
    ws = wb[sheet_name]
    print(f"\n{'='*20} SHEET: {sheet_name} (max_row={ws.max_row}, max_column={ws.max_column}) {'='*20}")
    for r in range(1, min(ws.max_row + 1, max_rows)):
        row_vals = [ws.cell(r, c).value for c in range(1, min(ws.max_column + 1, 15))]
        # filter out trailing Nones
        while row_vals and row_vals[-1] is None:
            row_vals.pop()
        if any(row_vals):
            # Print row if not entirely empty
            non_empty_indices = [f"C{i+1}:{v}" for i, v in enumerate(row_vals) if v is not None]
            print(f"Row {r:3d}: " + " | ".join(str(v)[:30] for v in non_empty_indices[:8]))

inspect_sheet("L-4", 45)
inspect_sheet("L-36", 45)
inspect_sheet("L-38", 45)
inspect_sheet("L-22", 45)
inspect_sheet("L-25 (i)", 45)
inspect_sheet("L-41", 40)
inspect_sheet("L-45", 35)

wb.close()
