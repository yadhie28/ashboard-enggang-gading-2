import zipfile
import xml.etree.ElementTree as ET
import re
from parse_sheets import parse_shared_strings, get_sheets_info

def parse_worksheet(z, filename, shared_strings):
    xml_data = z.read(filename)
    root = ET.fromstring(xml_data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    
    rows = {}
    for row in root.iter(f"{ns}row"):
        r_idx = int(row.attrib.get("r", 0))
        row_vals = {}
        for c in row.iter(f"{ns}c"):
            ref = c.attrib.get("r", "")
            t = c.attrib.get("t", "")
            v = c.find(f"{ns}v")
            val = ""
            if v is not None and v.text is not None:
                val = v.text
                if t == "s":
                    try:
                        val = shared_strings[int(val)]
                    except:
                        pass
            # column letter
            col_letter = re.match(r"([A-Z]+)", ref)
            if col_letter:
                col = col_letter.group(1)
                row_vals[col] = val
        rows[r_idx] = row_vals
    return rows

with zipfile.ZipFile("EG2B.xlsx", "r") as z:
    ss = parse_shared_strings(z)
    sheets = get_sheets_info(z)
    print("EG2B Total Sheets:", len(sheets))
    last_sheet = sheets[-1]
    print(f"Parsing {last_sheet['name']} ({last_sheet['filename']})...")
    rows = parse_worksheet(z, last_sheet["filename"], ss)
    for r_idx in sorted(rows.keys())[:25]:
        r = rows[r_idx]
        if any(r.values()):
            print(f"Row {r_idx:2d}: A={r.get('A','')} | B={r.get('B','')} | C={r.get('C','')} | D={r.get('D','')} | E={r.get('E','')} | F={r.get('F','')[:30]}")

