import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from run_build_data import normalize_doctor_name

def parse_shared_strings(z):
    shared_strings = []
    if "xl/sharedStrings.xml" not in z.namelist():
        return shared_strings
    xml_data = z.read("xl/sharedStrings.xml")
    root = ET.fromstring(xml_data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for si in root.findall(f"{ns}si"):
        text_parts = [t.text for t in si.iter(f"{ns}t") if t.text]
        shared_strings.append("".join(text_parts))
    return shared_strings

def get_sheets_info(z):
    wb_xml = z.read("xl/workbook.xml")
    root = ET.fromstring(wb_xml)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    r_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    rels_xml = z.read("xl/_rels/workbook.xml.rels")
    rels_root = ET.fromstring(rels_xml)
    rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels_root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")}
    
    sheets = []
    for s in root.find(f"{ns}sheets").findall(f"{ns}sheet"):
        s_name = s.attrib["name"]
        r_id = s.attrib[f"{r_ns}id"]
        target = rel_map.get(r_id, "")
        if not target.startswith("worksheets/"):
            target = "worksheets/" + target.split("/")[-1]
        sheets.append({"name": s_name, "filename": f"xl/{target}"})
    return sheets

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
                    try: val = shared_strings[int(val)]
                    except: pass
            col_letter = re.match(r"([A-Z]+)", ref)
            if col_letter:
                row_vals[col_letter.group(1)] = val
        rows[r_idx] = row_vals
    return rows

def parse_date_from_sheet_name(name):
    # Try finding 6 to 8 digits
    # Examples: Minggu 18102026 -> 18-10-2026, KAMIS 112026 -> 01-01-2026
    m = re.search(r"(\d{1,2})(\d{2})(2026)", name)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mth, d).isoformat()
        except:
            pass
    # If 7 digits: e.g. 1102026 -> 1-10-2026 or 01-10-2026
    m7 = re.search(r"(\d{1,2})[/\-.]?(\d{1,2})[/\-.]?(2026|26)", name)
    if m7:
        d = int(m7.group(1))
        mth = int(m7.group(2))
        y = 2026
        try:
            return date(y, mth, d).isoformat()
        except:
            pass
    return None

def excel_date_to_str(val):
    if not val:
        return ""
    val_str = str(val).strip()
    # Check if numeric float/int
    try:
        f = float(val_str)
        if 40000 < f < 50000:
            d = date(1899, 12, 30) + timedelta(days=int(f))
            return d.strftime("%d/%m/%Y")
    except:
        pass
    # If already string date
    return val_str

def parse_patient_row(r, room_type, current_iso_date):
    # Columns: A: NO, B: TGL MASUK, C: NAMA, D: JAMINAN, E: DOKTER, F: DIAGNOSA, G: PAGI, H: SORE, I: MALAM
    bed_raw = str(r.get("A", "")).strip()
    tgl_masuk_raw = excel_date_to_str(r.get("B", ""))
    nama_raw = str(r.get("C", "")).strip()
    jaminan_raw = str(r.get("D", "")).strip()
    dokter_raw = str(r.get("E", "")).strip()
    diagnosa_raw = str(r.get("F", "")).strip()
    pagi = str(r.get("G", "")).strip()
    sore = str(r.get("H", "")).strip()
    malam = str(r.get("I", "")).strip()

    if not bed_raw and not nama_raw:
        return None

    # Bed format
    try:
        bed_num = str(int(float(bed_raw)))
    except:
        bed_num = bed_raw

    # Check if empty bed / repair
    is_empty = False
    status = "Terisi"
    if any(k in bed_raw.upper() for k in ["BAU", "RUSAK", "KOSONG", "PERBAIKAN"]) or any(k in nama_raw.upper() for k in ["BAU", "RUSAK", "KOSONG"]) or (not nama_raw and not diagnosa_raw):
        is_empty = True
        status = "Rusak/Perbaikan" if "BAU" in (bed_raw + nama_raw).upper() else "Kosong"

    # Parse patient name and MR
    mr_no = ""
    clean_name = nama_raw
    age = ""
    gender = "L" if any(clean_name.startswith(p) for p in ["Tn.", "An. L", "By. L", "Sdr."]) else "P"
    
    mr_match = re.search(r"(?:NO\.?\s*MR|MR)\s*[:.]?\s*([0-9]+)", nama_raw, re.IGNORECASE)
    if mr_match:
        mr_no = mr_match.group(1)
        clean_name = re.sub(r"(?:NO\.?\s*MR|MR)\s*[:.]?\s*[0-9]+", "", clean_name, flags=re.IGNORECASE).strip()
    
    age_match = re.search(r"/\s*([0-9]+)\s*(?:th|tahun|yahun)?", clean_name, re.IGNORECASE)
    if age_match:
        age = age_match.group(1) + " th"
        clean_name = re.sub(r"/\s*[0-9]+\s*(?:th|tahun|yahun)?", "", clean_name, flags=re.IGNORECASE).strip()

    clean_name = re.sub(r"\s+", " ", clean_name).strip()
    if not clean_name and not is_empty:
        clean_name = "Pasien Bed " + str(bed_num)

    # Clean jaminan
    jaminan = jaminan_raw.strip()
    if not jaminan:
        if not is_empty:
            jaminan = "BPJS 3" # default common ward category if blank
    else:
        # Standardize
        if "BPJS 1" in jaminan.upper(): jaminan = "BPJS Kelas 1"
        elif "BPJS 2" in jaminan.upper(): jaminan = "BPJS Kelas 2"
        elif "BPJS 3" in jaminan.upper(): jaminan = "BPJS Kelas 3"
        elif "UMUM" in jaminan.upper(): jaminan = "Umum / Mandiri"
        elif "ASURANSI" in jaminan.upper(): jaminan = "Asuransi Swasta"

    # Calculate LOS (Length of Stay)
    los_days = 1
    tgl_masuk_clean = tgl_masuk_raw
    try:
        # Parse DD/MM/YYYY or DD/MM/YY
        m_d = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", tgl_masuk_raw)
        if m_d:
            day, month, year = int(m_d.group(1)), int(m_d.group(2)), int(m_d.group(3))
            if year < 100: year += 2000
            admit_date = date(year, month, day)
            curr_d = datetime.fromisoformat(current_iso_date).date()
            diff = (curr_d - admit_date).days
            los_days = max(1, diff + 1)
            tgl_masuk_clean = admit_date.strftime("%d/%m/%Y")
    except:
        pass

    # Extract tags
    combined_notes = f"{diagnosa_raw}\n{pagi}\n{sore}\n{malam}".upper()
    tags = []
    if any(k in combined_notes for k in ["HD", "HEMODIALISA", "CDL", "CIMINO"]):
        tags.append({"label": "Hemodialisa (HD)", "color": "purple"})
    if any(k in combined_notes for k in ["TRANSFUSI", "PRC", "TF ", "TF:", "KOLF"]):
        tags.append({"label": "Transfusi Darah", "color": "red"})
    if any(k in combined_notes for k in ["POST OP", "PRO OP", "POD", "LAPARASKOPI", "OPERASI", "DEBRIDEMENT", "TKR", "ORIF"]):
        tags.append({"label": "Bedah / Operasi", "color": "orange"})
    if any(k in combined_notes for k in ["CA ", "CANCER", "KANKER", "CHEMO", "KEMO", "ONKOLOGI"]):
        tags.append({"label": "Onkologi", "color": "pink"})
    if any(k in combined_notes for k in ["PULANG", "BLPL", "KRS", "RAJAL"]):
        tags.append({"label": "Rencana Pulang", "color": "green"})
    if any(k in combined_notes for k in ["PUASA", "PRE OP"]):
        tags.append({"label": "Puasa Pre-Op", "color": "amber"})

    # Doctor parsing
    dpjp_primary = dokter_raw.split("\n")[0].strip()
    dpjp_primary = re.sub(r"\s+", " ", dpjp_primary).strip()
    if dpjp_primary.startswith("dr.") or dpjp_primary.startswith("DR."):
        pass
    
    # Diagnosis specialty category
    cat = "Lain-lain"
    diag_up = diagnosa_raw.upper()
    if any(k in diag_up for k in ["CA ", "CANCER", "CARCINOMA", "TUMOR", "ADENOCARCINOMA", "MYELOMA", "LEUKEMIA", "AML"]):
        cat = "Onkologi & Hematologi"
    elif any(k in diag_up for k in ["CKD", "AKI", "GINJAL", "NEFRO", "RENAL", "URETER", "HIDRONEFROSIS", "HEMATURIA"]):
        cat = "Nefrologi & Urologi"
    elif any(k in diag_up for k in ["APP", "ABDOMEN", "ABD PAIN", "CHOLE", "KOLE", "HEPATIS", "PANCREA", "ILEUS", "HEMATOCHEZIA", "VOMITUS"]):
        cat = "Bedah Digestif & Gastro"
    elif any(k in diag_up for k in ["SPONDIL", "OA ", "FRACTURE", "FRAKTUR", "TKR", "ORIF", "TENDON", "SPINE"]):
        cat = "Ortopedi & Traumatologi"
    elif any(k in diag_up for k in ["PNEUMONIA", "TB", "SESAK", "THORAX", "EFFUSI"]):
        cat = "Pulmonologi / Paru"
    elif any(k in diag_up for k in ["DM", "DIABETES", "HIPERKALEMIA", "HIPONATREMIA", "ANASARKA", "EDEMA"]):
        cat = "Penyakit Dalam (Metabolik)"

    return {
        "bed": bed_num,
        "room": room_type,
        "status": status,
        "isEmpty": is_empty,
        "name": clean_name if not is_empty else ("Bed Rusak (BAU)" if "Rusak" in status else "Bed Kosong"),
        "mrNo": mr_no,
        "gender": gender,
        "age": age,
        "admissionDate": tgl_masuk_clean if not is_empty else "-",
        "los": los_days if not is_empty else 0,
        "insurance": jaminan if not is_empty else "-",
        "doctor": dokter_raw if not is_empty else "-",
        "doctorPrimary": dpjp_primary if not is_empty else "-",
        "diagnosis": diagnosa_raw if not is_empty else "-",
        "category": cat if not is_empty else "-",
        "notes": {
            "pagi": pagi,
            "sore": sore,
            "malam": malam
        },
        "tags": tags
    }

print("Extractor functions defined.")

def compile_all():
    print("Compiling all sheets from EG2A.xlsx and EG2B.xlsx...")
    
    # 1. Process EG2A
    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a:
        ss_a = parse_shared_strings(z_a)
        sheets_a = get_sheets_info(z_a)
        print(f"EG2A sheets: {len(sheets_a)}")
        
        # Build date -> sheet map for A
        date_map_a = {}
        for s in sheets_a:
            if "MASTER" in s["name"].upper():
                continue
            iso = parse_date_from_sheet_name(s["name"])
            if iso:
                date_map_a[iso] = s

    # 2. Process EG2B
    with zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        ss_b = parse_shared_strings(z_b)
        sheets_b = get_sheets_info(z_b)
        print(f"EG2B sheets: {len(sheets_b)}")
        
        date_map_b = {}
        for s in sheets_b:
            iso = parse_date_from_sheet_name(s["name"])
            if iso:
                date_map_b[iso] = s

    all_dates = sorted(list(set(list(date_map_a.keys()) + list(date_map_b.keys()))))
    print(f"Total dates detected: {len(all_dates)}, from {all_dates[0]} to {all_dates[-1]}")

    # We will parse:
    # - Latest date (e.g. 2026-10-18) in full detail
    # - Historical daily metrics (BOR, count, admissions)
    # - The most recent 30 days in full detail so user can toggle any recent day instantly
    
    latest_date = all_dates[-1]
    print(f"Latest date is {latest_date}")

    history = []
    doctor_patients = defaultdict(set)
    diag_counts = {}
    cat_counts = {}
    insurance_counts = {}
    recent_days = {}

    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a, zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        for idx, dt in enumerate(all_dates):
            is_recent = (idx >= len(all_dates) - 30)
            
            patients_a = []
            if dt in date_map_a:
                rows_a = parse_worksheet(z_a, date_map_a[dt]["filename"], ss_a)
                # Find start row (after header NO, TGL MASUK, etc)
                header_passed = False
                for r_idx in sorted(rows_a.keys()):
                    r = rows_a[r_idx]
                    vals = [str(v).upper() for v in r.values()]
                    if any("TGL MASUK" in v or "TANGGAL MASUK" in v for v in vals):
                        header_passed = True
                        continue
                    if header_passed and (r.get("A") or r.get("C")):
                        # Check if row has valid content
                        pt = parse_patient_row(r, "EG2A", dt)
                        if pt:
                            patients_a.append(pt)

            patients_b = []
            if dt in date_map_b:
                rows_b = parse_worksheet(z_b, date_map_b[dt]["filename"], ss_b)
                header_passed = False
                for r_idx in sorted(rows_b.keys()):
                    r = rows_b[r_idx]
                    vals = [str(v).upper() for v in r.values()]
                    if any("TGL MASUK" in v or "TANGGAL MASUK" in v for v in vals):
                        header_passed = True
                        continue
                    if header_passed and (r.get("A") or r.get("C")):
                        pt = parse_patient_row(r, "EG2B", dt)
                        if pt:
                            patients_b.append(pt)

            # Metrics
            occ_a = len([p for p in patients_a if not p["isEmpty"]])
            occ_b = len([p for p in patients_b if not p["isEmpty"]])
            tot_beds = len(patients_a) + len(patients_b)
            tot_occ = occ_a + occ_b
            bor = round((tot_occ / max(1, tot_beds)) * 100, 1)

            history.append({
                "date": dt,
                "occA": occ_a,
                "occB": occ_b,
                "totalOcc": tot_occ,
                "totalBeds": tot_beds,
                "bor": bor
            })

            # Tally stats
            for p in patients_a + patients_b:
                if not p["isEmpty"]:
                    doc = normalize_doctor_name(p["doctorPrimary"])
                    if doc and doc != "-" and len(doc) > 3:
                        pkey = p["mrNo"].strip() if (p["mrNo"] and len(p["mrNo"].strip()) > 3) else p["name"].strip().upper()
                        doctor_patients[doc].add(pkey)
                    cat = p["category"]
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                    ins = p["insurance"]
                    insurance_counts[ins] = insurance_counts.get(ins, 0) + 1
                    
                    # Top diagnosis phrase
                    diag_raw = p["diagnosis"].split("\n")[0].strip()[:40]
                    if diag_raw and diag_raw != "-":
                        diag_counts[diag_raw] = diag_counts.get(diag_raw, 0) + 1

            if is_recent:
                recent_days[dt] = {
                    "date": dt,
                    "eg2a": patients_a,
                    "eg2b": patients_b,
                    "summary": {
                        "totalBeds": tot_beds,
                        "occupied": tot_occ,
                        "empty": tot_beds - tot_occ,
                        "bor": bor,
                        "occA": occ_a,
                        "occB": occ_b
                    }
                }

    # Format Top Doctors
    top_doctors = sorted([{"name": k, "count": len(v)} for k, v in doctor_patients.items()], key=lambda x: x["count"], reverse=True)[:15]
    top_diags = sorted([{"name": k, "count": v} for k, v in diag_counts.items()], key=lambda x: x["count"], reverse=True)[:15]
    cat_distribution = [{"name": k, "count": v} for k, v in cat_counts.items()]
    ins_distribution = [{"name": k, "count": v} for k, v in insurance_counts.items()]

    payload = {
        "metadata": {
            "title": "Dashboard Ruang Rawat Inap Enggang Gading 2",
            "hospital": "RSUD Dr. Soedarso / Ruang Enggang Gading 2 (EG2A & EG2B)",
            "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latestDate": latest_date,
            "totalDatesRecorded": len(all_dates),
            "spreadsheetA": "https://docs.google.com/spreadsheets/d/1RtJzfTnuTu-cmZXW59aGUDpihhJ1kGm_z9BozUHsgsI/edit",
            "spreadsheetB": "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/edit"
        },
        "allDates": all_dates,
        "history": history,
        "analytics": {
            "topDoctors": top_doctors,
            "topDiagnoses": top_diags,
            "categories": cat_distribution,
            "insurances": ins_distribution
        },
        "recentDays": recent_days,
        "today": recent_days.get(latest_date)
    }

    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    print(f"Generated dashboard_data.json successfully! File size: {os.path.getsize('dashboard_data.json')} bytes")

if __name__ == "__main__":
    compile_all()
