import openpyxl
import re

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)
ws = wb["L-4"]

def parse_l4_blocks(ws):
    # Find all quarter blocks
    # A quarter block starts where row 1 or row 2 has FY / Quarter
    # Let's find all column indices that start a block
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
            blocks.append({
                'fy': current_fy,
                'q': q_match,
                'col': c
            })
            
    print(f"Found {len(blocks)} blocks:")
    for b in blocks:
        print(b)
        
    # Now for each block, determine its column range and extract metrics
    results = []
    for i, b in enumerate(blocks):
        start_c = b['col']
        end_c = blocks[i+1]['col'] - 1 if i+1 < len(blocks) else ws.max_column
        
        # In this column range [start_c, end_c], find PARTICULARS column and Quarter Value column
        particulars_c = None
        quarter_c = None
        
        for c in range(start_c, end_c + 1):
            for r in range(1, min(ws.max_row + 1, 15)):
                val = str(ws.cell(r, c).value or '').strip()
                if 'particular' in val.lower():
                    particulars_c = c
                if 'for the' in val.lower() and 'quarter' in val.lower() and 'corresponding' not in val.lower() and 'previous' not in val.lower():
                    quarter_c = c
                    
        # If particulars_c not found, default to start_c or start_c + 1
        if particulars_c is None:
            for c in range(start_c, end_c + 1):
                # check if column has strings like "First year" or "Single"
                for r in range(10, min(ws.max_row + 1, 20)):
                    val = str(ws.cell(r, c).value or '').lower()
                    if 'first year' in val or 'single' in val:
                        particulars_c = c
                        break
                if particulars_c:
                    break
                    
        # If quarter_c not found, look for first numeric column next to particulars_c
        if quarter_c is None and particulars_c:
            quarter_c = particulars_c + 1
            
        print(f"\nBlock {b['fy']} {b['q']} (cols {start_c}..{end_c}): particulars_col={particulars_c}, quarter_col={quarter_c}")
        
        # Now extract rows in [start_c..end_c]
        row_dict = {}
        if particulars_c and quarter_c:
            for r in range(8, ws.max_row + 1):
                part = str(ws.cell(r, particulars_c).value or '').strip()
                val = ws.cell(r, quarter_c).value
                if part and val is not None:
                    row_dict[part] = val
                    
        for k, v in row_dict.items():
            print(f"  {k} -> {v}")
            
    return results

parse_l4_blocks(ws)
wb.close()
