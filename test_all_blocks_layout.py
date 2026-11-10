import openpyxl
import re
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

wb = openpyxl.load_workbook("ACKO_LIFE_INSURANCE_Consolidated.xlsx", data_only=True)

def inspect_sheet_block_layout(sheet_name):
    ws = wb[sheet_name]
    print(f"\n==================== Sheet: {sheet_name} ====================")
    
    # 1. Detect all quarter blocks by scanning row 1 and 2
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
                'start_col': c
            })
            
    print(f"Total blocks detected: {len(blocks)}")
    
    # Check first 3 blocks
    for i, b in enumerate(blocks[:3]):
        start_c = b['start_col']
        end_c = blocks[i+1]['start_col'] - 1 if i+1 < len(blocks) else ws.max_column
        
        # Look for headers in row 7-15
        headers = {}
        for c in range(start_c, end_c + 1):
            col_text = []
            for r in range(7, 14):
                v = ws.cell(r, c).value
                if v is not None:
                    col_text.append(str(v).replace('\n', ' ').strip())
            if col_text:
                headers[c] = " // ".join(col_text[:3])
                
        print(f"Block {b['fy']} {b['q']} (cols {start_c}..{end_c}):")
        for c, h in headers.items():
            print(f"  Col {c:2d}: {h[:80]}")

for s in ['L-1', 'L-2', 'L-3', 'L-7', 'L-8', 'L-9', 'L-32', 'L-36', 'L-37', 'L-38', 'L-41', 'L-45']:
    inspect_sheet_block_layout(s)

wb.close()
