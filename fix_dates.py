import zipfile
import xml.etree.ElementTree as ET
import re
from datetime import date
from parse_sheets import parse_shared_strings, get_sheets_info

months_id = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MEI": 5, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGU": 8, "AUG": 8, "SEP": 9, "OKT": 10, "OCT": 10, "NOV": 11, "DES": 12, "DEC": 12
}

def extract_date_from_sheet(z, sheet_info, ss):
    s_name = sheet_info["name"]
    # 1. Prioritize explicit 8 digits DDMMYYYY in sheet name (e.g. "JUMAT 23102026" or "EG 2B 23102026")
    m8 = re.search(r"(\d{2})(\d{2})(2026)", s_name)
    if m8:
        d, mth, y = int(m8.group(1)), int(m8.group(2)), int(m8.group(3))
        try: return date(y, mth, d).isoformat()
        except: pass

    # 2. Try reading row 1, 2, 3 in the worksheet
    xml_data = z.read(sheet_info["filename"])
    root = ET.fromstring(xml_data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    
    header_texts = []
    for row in root.iter(f"{ns}row"):
        r_idx = int(row.attrib.get("r", 0))
        if r_idx > 4: break
        for c in row.iter(f"{ns}c"):
            t = c.attrib.get("t", "")
            v = c.find(f"{ns}v")
            if v is not None and v.text is not None:
                val = v.text
                if t == "s":
                    try: val = ss[int(val)]
                    except: pass
                header_texts.append(val)
                
    text_combined = " ".join(header_texts)
    # Search for D/M/YYYY or DD/MM/YYYY
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", text_combined)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mth, d).isoformat()
        except:
            pass
            
    # Search for DD MMMM YYYY (e.g. 18 OKTOBER 2026)
    m2 = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text_combined)
    if m2:
        d = int(m2.group(1))
        mth_str = m2.group(2)[:3].upper()
        if mth_str in months_id:
            mth = months_id[mth_str]
            try:
                return date(int(m2.group(3)), mth, d).isoformat()
            except:
                pass
        
    # If 7 digits e.g. 1102026 -> 01/10/2026 or 1/1/2026?
    # Usually in sheet name: "KAMIS 112026" is 1/1/2026
    m7 = re.search(r"(\d{1})(\d{1})(2026)", s_name)
    if m7:
        d, mth, y = int(m7.group(1)), int(m7.group(2)), int(m7.group(3))
        try: return date(y, mth, d).isoformat()
        except: pass

    return None

if __name__ == "__main__":
    with zipfile.ZipFile("EG2A.xlsx", "r") as z:
        ss = parse_shared_strings(z)
        sheets = get_sheets_info(z)
        for s in sheets[:5] + sheets[-5:]:
            if "MASTER" in s["name"].upper(): continue
            dt = extract_date_from_sheet(z, s, ss)
            print(f"Sheet: {s['name']} -> Date: {dt}")

