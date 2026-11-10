import openpyxl
import re

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def inspect_schedule_data(sheet_name, max_rows=30):
    ws = wb[sheet_name]
    print(f"\n==================== {sheet_name} ====================")
    for r in range(1, min(ws.max_row + 1, max_rows)):
        vals = [ws.cell(r, c).value for c in range(1, min(ws.max_column + 1, 30))]
        # show row if there's any text or number
        if any(v is not None and str(v).strip() != '' for v in vals):
            s = f"R{r:2d}: "
            items = []
            for c_idx, v in enumerate(vals, 1):
                if v is not None and str(v).strip() != '':
                    val_str = str(v).replace('\n', ' ')[:25]
                    items.append(f"C{c_idx}:{val_str}")
            print(s + " | ".join(items[:8]))

inspect_schedule_data("L-1", 35)
inspect_schedule_data("L-2", 35)
inspect_schedule_data("L-3", 35)
inspect_schedule_data("L-7", 25)
inspect_schedule_data("L-8", 25)
inspect_schedule_data("L-9", 25)
inspect_schedule_data("L-32", 30)

wb.close()
