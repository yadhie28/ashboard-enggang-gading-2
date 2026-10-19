import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
from datetime import datetime, date

def parse_shared_strings(z):
    shared_strings = []
    if "xl/sharedStrings.xml" not in z.namelist():
        return shared_strings
    
    xml_data = z.read("xl/sharedStrings.xml")
    root = ET.fromstring(xml_data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for si in root.findall(f"{ns}si"):
        # Could be <t> or multiple <r><t>
        text_parts = []
        for t in si.iter(f"{ns}t"):
            if t.text:
                text_parts.append(t.text)
        shared_strings.append("".join(text_parts))
    return shared_strings

def get_sheets_info(z):
    wb_xml = z.read("xl/workbook.xml")
    root = ET.fromstring(wb_xml)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    r_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    
    # Also read rels to map rId to filename
    rels_xml = z.read("xl/_rels/workbook.xml.rels")
    rels_root = ET.fromstring(rels_xml)
    rel_map = {}
    rel_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    for r in rels_root.findall(f"{rel_ns}Relationship"):
        rel_map[r.attrib["Id"]] = r.attrib["Target"]
        
    sheets = []
    for s in root.find(f"{ns}sheets").findall(f"{ns}sheet"):
        s_name = s.attrib["name"]
        r_id = s.attrib[f"{r_ns}id"]
        target = rel_map.get(r_id, "")
        if not target.startswith("worksheets/"):
            target = "worksheets/" + target.split("/")[-1]
        sheets.append({
            "name": s_name,
            "filename": f"xl/{target}"
        })
    return sheets

print("Helper defined.")
