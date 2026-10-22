"""
Rebuild Dashboard Data with Spreadsheet Cell Fill Color Detection for Patient Discharges (Pasien Pulang)
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from parse_sheets import parse_shared_strings, get_sheets_info
from fix_dates import extract_date_from_sheet

CAPACITY_EG2A = 16
CAPACITY_EG2B = 40
TOTAL_CAPACITY = 56

HEADER_COLORS = {'FF6AA84F', 'FF356854', 'FF38761D'}
IGNORE_COLORS = {'FFFFFFFF', 'FFF8F9FA', 'FFF6F8F9', 'FFF3F3F3', None}

def normalize_doctor_name(raw_name):
    if not raw_name or raw_name == "-" or len(str(raw_name).strip()) < 3:
        return "-"
    name = str(raw_name).strip()
    name = re.sub(r"\s+", " ", name).strip()
    name_clean = name.rstrip(".").strip()
    u = name_clean.upper()
    
    # Filter out non-doctor entries
    if any(u.startswith(x) for x in ["BPJS", "UMUM", "ASURANSI", "BED", "KOSONG", "RUSAK", "RUANG"]):
        return "-"
    if u in ["-", "NONE", "NULL"]:
        return "-"
        
    # Canonical mappings for key doctors requested by user & common variants
    if "IVAN" in u:
        return "IVAN LUMBAN TORUAN, DR, SP.PD-KHOM"
    if "SONY" in u:
        return "R. SONY YUSUF WIBISONO, DR, SP.PD.,KGH"
    if "DARMAWAN" in u:
        return "DARMAWAN, DR., M.KES., SP.PD-KGH. FINASIM"
    if "DECKY" in u:
        return "DECKY ANDREA, DR, SP.PD"
    if "APRIANI" in u:
        return "APRIANI, DR, M.KED (PD), SP.PD"
    if "HARRY ANDHIKA" in u or (u.startswith("DR. HARRY") and "FADJAR" not in u):
        return "HARRY ANDHIKA, DR, SP.PD"
    if "HARRY FADJAR" in u:
        return "HARRY FADJAR, DR. SP.OT"
    if "YANCE" in u or "FEDRY" in u:
        return "FEDRY YANCE, DR, SP.U"
    if "DANAR" in u:
        return "DANAR ANGGRAHINI. K.D., DR. SP.PD. KGH. FINASIM"
    if "EKO RUSTIANTO" in u or u == "DR. EKO":
        return "EKO RUSTIANTO SUHARDIMAN, DR. SP.B(K) ONK"
    if "MUHARDANI" in u:
        return "MUHARDANI IQBAL, DR., M.KED (PD), SP.PD"
    if "PARSAORAN" in u:
        return "PARSAORAN NABABAN, DR., SP.U(K)"
    if "ELIT" in u:
        return "ELIT IRAWAN, DR, M.KES. SP.B SUBSP.BD (K) FINACS"
    if "ZAINUL" in u:
        return "ZAINUL NAIM, DR. SP.B-KBD"
    if "DENNY KRYSTIAN" in u:
        return "DENNY KRYSTIAN TANDI OSE, DR, SP.B-KBD"
    if "NOSIKO" in u:
        return "NOSIKO ALLBER, DR. SP.BS"
    if "OKTAVIANUS" in u:
        return "OKTAVIANUS, DR, SP.OT. SPINE (K)"
    if "YEREMIA" in u:
        return "YEREMIA GERALD K., DR, SP.B"
    if "RETNO" in u:
        return "RETNO MUSTIKANINGSIH, DR, M.KES. SP.K"
    if "DONI SETIAWAN" in u:
        return "DONI SETIAWAN, DR. SP.BP-RE"
    if "JOHANNES MANURUNG" in u:
        return "JOHANNES MANURUNG, DR. SP.BS"
    if "GEDE SANDJAJA" in u:
        return "GEDE SANDJAJA, DR. SP.OT. (K)"
        
    return name_clean

def clean_insurance_name(name):
    if not name or name in ['-', '.', '0.0'] or len(str(name).strip()) < 2:
        return 'Lainnya / Penjamin Khusus'
    u = str(name).strip().upper()
    if any(k in u for k in ['TN.', 'NY.', 'NN.', 'SDR.', 'MR:']):
        return 'Lainnya / Penjamin Khusus'
    if any(k in u for k in ['JR', 'JASA RAHARJA', 'JASARAHARJA', 'JASSA RAHARJA']):
        return 'Jasa Raharja'
    if any(k in u for k in ['UMUM', 'MANDIRI']):
        return 'Umum / Mandiri'
    if any(k in u for k in ['KELAS 3', 'KELAS III', 'BPJS 3', 'BPJS3', 'BPKS 3', 'BPJD 3', 'BPJ 3', 'PBJS 3', 'BPSJ 3']):
        return 'BPJS Kelas 3'
    if any(k in u for k in ['KELAS 2', 'KELAS II', 'BPJS 2', 'BPJS2', 'BPSJ 2']):
        return 'BPJS Kelas 2'
    if any(k in u for k in ['KELAS 1', 'KELAS I', 'BPJS 1', 'BPJS1']):
        return 'BPJS Kelas 1'
    if 'BPJS' in u:
        return 'BPJS Kelas 3'
    return 'Lainnya / Penjamin Khusus'

def load_style_fills(z):
    styles_root = ET.fromstring(z.read('xl/styles.xml'))
    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    fills = styles_root.findall('ns:fills/ns:fill', ns)
    fill_colors = []
    for f in fills:
        pf = f.find('ns:patternFill', ns)
        if pf is not None:
            fg = pf.find('ns:fgColor', ns)
            fill_colors.append(fg.attrib if fg is not None else None)
        else:
            fill_colors.append(None)
    
    xfs = styles_root.findall('ns:cellXfs/ns:xf', ns)
    xf_to_color = {}
    for i, xf in enumerate(xfs):
        fid = int(xf.get('fillId', 0))
        fcol = fill_colors[fid] if fid < len(fill_colors) else None
        if fcol:
            rgb = fcol.get('rgb')
            theme = fcol.get('theme')
            if rgb and rgb not in IGNORE_COLORS and rgb not in HEADER_COLORS:
                xf_to_color[i] = rgb
            elif theme and theme not in ['0']:
                xf_to_color[i] = f'theme:{theme}'
            else:
                xf_to_color[i] = None
        else:
            xf_to_color[i] = None
    return xf_to_color

def parse_worksheet_with_colors(z, filename, shared_strings, xf_to_color):
    xml_data = z.read(filename)
    root = ET.fromstring(xml_data)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows = {}
    for row in root.iter(f"{ns}row"):
        r_idx = int(row.attrib.get("r", 0))
        row_vals = {}
        row_colored = False
        row_colors = []
        for c in row.iter(f"{ns}c"):
            ref = c.attrib.get("r", "")
            t = c.attrib.get("t", "")
            s_id = int(c.attrib.get("s", 0))
            col_info = xf_to_color.get(s_id)
            if col_info:
                row_colored = True
                row_colors.append(col_info)
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
        if row_vals:
            row_vals["_isColored"] = row_colored
            row_vals["_colors"] = row_colors
            rows[r_idx] = row_vals
    return rows

def excel_date_to_str(val):
    if not val:
        return ""
    val_str = str(val).strip()
    try:
        f = float(val_str)
        if 40000 < f < 50000:
            d = date(1899, 12, 30) + timedelta(days=int(f))
            return d.strftime("%d/%m/%Y")
    except:
        pass
    return val_str

def parse_patient_row_enhanced(r, room_type, current_iso_date):
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

    try:
        bed_num = str(int(float(bed_raw)))
    except:
        bed_num = bed_raw

    is_empty = False
    status = "Terisi"
    if any(k in bed_raw.upper() for k in ["BAU", "RUSAK", "KOSONG", "PERBAIKAN"]) or any(k in nama_raw.upper() for k in ["BAU", "RUSAK", "KOSONG"]) or (not nama_raw and not diagnosa_raw):
        is_empty = True
        status = "Rusak/Perbaikan" if "BAU" in (bed_raw + nama_raw).upper() else "Kosong"

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

    jaminan = jaminan_raw.strip()
    if not jaminan:
        if not is_empty: jaminan = "BPJS Kelas 3"
    else:
        if "BPJS 1" in jaminan.upper(): jaminan = "BPJS Kelas 1"
        elif "BPJS 2" in jaminan.upper(): jaminan = "BPJS Kelas 2"
        elif "BPJS 3" in jaminan.upper(): jaminan = "BPJS Kelas 3"
        elif "UMUM" in jaminan.upper(): jaminan = "Umum / Mandiri"
        elif "ASURANSI" in jaminan.upper(): jaminan = "Asuransi Swasta"

    los_days = 1
    tgl_masuk_clean = tgl_masuk_raw
    try:
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

    # Color detection for discharge
    is_colored = bool(r.get("_isColored"))
    color_hex = r.get("_colors", [None])[0] if r.get("_colors") else None
    is_discharged = False
    
    tags = []
    combined_notes = f"{diagnosa_raw}\n{pagi}\n{sore}\n{malam}".upper()
    
    if not is_empty:
        if is_colored or any(k in combined_notes for k in ["PULANG HARI INI", "ACC BLPL", "ACC PULANG", "ACC RAWAT JALAN", "KRS HARI INI"]):
            is_discharged = True
            status = "Pulang Hari Ini"
            tags.append({"label": "Pulang Hari Ini", "color": "emerald"})
        elif any(k in combined_notes for k in ["PULANG", "BLPL", "KRS", "RAJAL"]):
            tags.append({"label": "Rencana Pulang", "color": "green"})

    if any(k in combined_notes for k in ["HD", "HEMODIALISA", "CDL", "CIMINO"]):
        tags.append({"label": "Hemodialisa (HD)", "color": "purple"})
    if any(k in combined_notes for k in ["TRANSFUSI", "PRC", "TF ", "TF:", "KOLF"]):
        tags.append({"label": "Transfusi Darah", "color": "red"})
    if any(k in combined_notes for k in ["POST OP", "PRO OP", "POD", "LAPARASKOPI", "OPERASI", "DEBRIDEMENT", "TKR", "ORIF"]):
        tags.append({"label": "Bedah / Operasi", "color": "orange"})
    if any(k in combined_notes for k in ["CA ", "CANCER", "KANKER", "CHEMO", "KEMO", "ONKOLOGI"]):
        tags.append({"label": "Onkologi", "color": "pink"})
    if any(k in combined_notes for k in ["PUASA", "PRE OP"]):
        tags.append({"label": "Puasa Pre-Op", "color": "amber"})

    dpjp_primary = dokter_raw.split("\n")[0].strip()
    dpjp_primary = normalize_doctor_name(dpjp_primary)

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
        "isDischargedToday": is_discharged,
        "dischargeColor": color_hex,
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

def normalize_wing_beds(patients_raw, wing_name, target_capacity):
    occupied = [p for p in patients_raw if not p.get("isEmpty")]
    empty_raw = [p for p in patients_raw if p.get("isEmpty")]
    
    bed_slots = {}
    overflow = []
    
    for p in occupied:
        try:
            b_int = int(re.sub(r"[^0-9]", "", str(p["bed"])))
        except:
            b_int = None
            
        if b_int and 1 <= b_int <= target_capacity and b_int not in bed_slots:
            bed_slots[b_int] = p
        else:
            overflow.append(p)
            
    for p in empty_raw:
        try:
            b_int = int(re.sub(r"[^0-9]", "", str(p["bed"])))
        except:
            b_int = None
        if b_int and 1 <= b_int <= target_capacity and b_int not in bed_slots:
            bed_slots[b_int] = p
            
    for slot in range(1, target_capacity + 1):
        if slot not in bed_slots and overflow:
            p = overflow.pop(0)
            p_copy = dict(p)
            p_copy["bed"] = str(slot)
            bed_slots[slot] = p_copy
            
    result = []
    for slot in range(1, target_capacity + 1):
        if slot in bed_slots:
            result.append(bed_slots[slot])
        else:
            result.append({
                "bed": str(slot),
                "room": wing_name,
                "status": "Kosong",
                "isEmpty": True,
                "isDischargedToday": False,
                "name": "Bed Kosong",
                "mrNo": "",
                "gender": "-",
                "age": "",
                "admissionDate": "-",
                "los": 0,
                "insurance": "-",
                "doctor": "-",
                "doctorPrimary": "-",
                "diagnosis": "-",
                "category": "-",
                "notes": {"pagi": "", "sore": "", "malam": ""},
                "tags": []
            })
    return result

def run():
    print(f"Building dashboard data with CELL FILL COLOR DETECTION...")
    print(f"Capacity: EG2A={CAPACITY_EG2A}, EG2B={CAPACITY_EG2B}, Total={TOTAL_CAPACITY}")

    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a:
        ss_a = parse_shared_strings(z_a)
        fa_map = load_style_fills(z_a)
        sheets_a = get_sheets_info(z_a)
        date_map_a = {}
        for s in sheets_a:
            if "MASTER" in s["name"].upper(): continue
            dt = extract_date_from_sheet(z_a, s, ss_a)
            if dt: date_map_a[dt] = s

    with zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        ss_b = parse_shared_strings(z_b)
        fb_map = load_style_fills(z_b)
        sheets_b = get_sheets_info(z_b)
        date_map_b = {}
        for s in sheets_b:
            dt = extract_date_from_sheet(z_b, s, ss_b)
            if dt: date_map_b[dt] = s

    all_dates = sorted([d for d in set(list(date_map_a.keys()) + list(date_map_b.keys())) if "2026-01-01" <= d <= "2026-12-31"])
    latest_date = all_dates[-1]

    history = []
    doctor_patients = defaultdict(set)
    patient_diagnoses_text = defaultdict(set)
    total_unique_patients = set()
    diag_counts = {}
    cat_counts = {}
    insurance_counts = {}
    recent_days = {}

    daily_stats = {}
    prev_patients = set()

    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a, zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        for idx, dt in enumerate(all_dates):
            is_recent = (idx >= len(all_dates) - 45)
            
            raw_patients_a = []
            if dt in date_map_a:
                rows_a = parse_worksheet_with_colors(z_a, date_map_a[dt]["filename"], ss_a, fa_map)
                header_passed = False
                for r_idx in sorted(rows_a.keys()):
                    r = rows_a[r_idx]
                    vals = [str(v).upper() for v in r.values()]
                    if any("TGL MASUK" in v or "TANGGAL MASUK" in v for v in vals):
                        header_passed = True
                        continue
                    if header_passed and (r.get("A") or r.get("C")):
                        pt = parse_patient_row_enhanced(r, "EG2A", dt)
                        if pt: raw_patients_a.append(pt)

            raw_patients_b = []
            if dt in date_map_b:
                rows_b = parse_worksheet_with_colors(z_b, date_map_b[dt]["filename"], ss_b, fb_map)
                header_passed = False
                for r_idx in sorted(rows_b.keys()):
                    r = rows_b[r_idx]
                    vals = [str(v).upper() for v in r.values()]
                    if any("TGL MASUK" in v or "TANGGAL MASUK" in v for v in vals):
                        header_passed = True
                        continue
                    if header_passed and (r.get("A") or r.get("C")):
                        pt = parse_patient_row_enhanced(r, "EG2B", dt)
                        if pt: raw_patients_b.append(pt)

            patients_a = normalize_wing_beds(raw_patients_a, "EG2A", CAPACITY_EG2A)
            patients_b = normalize_wing_beds(raw_patients_b, "EG2B", CAPACITY_EG2B)
            # Pasien aktif = Pasien tanpa warna (tidak kosong dan bukan pasien pulang)
            occ_a = len([p for p in patients_a if not p["isEmpty"] and not p.get("isDischargedToday")])
            occ_b = len([p for p in patients_b if not p["isEmpty"] and not p.get("isDischargedToday")])
            tot_occ = occ_a + occ_b
            bor = round((tot_occ / TOTAL_CAPACITY) * 100, 1)

            history.append({
                "date": dt,
                "occA": occ_a,
                "occB": occ_b,
                "totalOcc": tot_occ,
                "totalBeds": TOTAL_CAPACITY,
                "bor": bor
            })

            curr_p_keys = set()
            deaths_today = 0
            death_gt48_today = 0
            discharges_from_color = 0

            for p in patients_a + patients_b:
                if not p["isEmpty"]:
                    pkey = p["mrNo"].strip() if (p["mrNo"] and len(p["mrNo"].strip()) > 3) else p["name"].strip().upper()
                    curr_p_keys.add(pkey)
                    total_unique_patients.add(pkey)

                    if p.get("isDischargedToday"):
                        discharges_from_color += 1

                    doc = p["doctorPrimary"]
                    if doc and doc != "-" and len(doc) > 3:
                        doctor_patients[doc].add(pkey)
                    cat = p["category"]
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                    ins = clean_insurance_name(p["insurance"])
                    insurance_counts[ins] = insurance_counts.get(ins, 0) + 1
                    diag_raw = p.get("diagnosis", "")
                    if diag_raw and diag_raw != "-" and len(diag_raw) > 2:
                        patient_diagnoses_text[pkey].add(diag_raw.upper())

                    notes = (p["notes"]["pagi"] + " " + p["notes"]["sore"] + " " + p["notes"]["malam"]).upper()
                    if any(k in notes for k in ["MENINGGAL JAM", "MENINGGAL PUKUL", "EXIT JAM", "EXIT PUKUL", "WAFAT JAM", "WAFAT PUKUL", "MENINGGAL DI RUANGAN", "PX MENINGGAL", "PASIEN MENINGGAL", "DEATH"]):
                        deaths_today += 1
                        if p["los"] >= 2:
                            death_gt48_today += 1

            # Discharges calculation: prioritize exact color fill
            if discharges_from_color > 0:
                discharges_today = discharges_from_color
            else:
                # Fallback to turnover set diff
                discharges_today = len(prev_patients - curr_p_keys) if idx > 0 else 0

            daily_stats[dt] = {
                "hp": tot_occ,
                "occA": occ_a,
                "occB": occ_b,
                "discharges": discharges_today,
                "deaths": deaths_today,
                "deathsGt48": death_gt48_today
            }
            prev_patients = curr_p_keys

            if is_recent:
                tag_counts = {}
                for p in patients_a + patients_b:
                    for t in p.get("tags", []):
                        lbl = t["label"]
                        tag_counts[lbl] = tag_counts.get(lbl, 0) + 1

                # Logika Pergeseran Bed
                text_free_a = f"{max(0, 4 - (occ_a - 12))} ekstra bed" if occ_a >= 12 else f"{12 - occ_a} + 4 ekstra bed"
                text_free_b = f"{max(0, 4 - (occ_b - 36))} ekstra bed" if occ_b >= 36 else f"{36 - occ_b} + 4 ekstra bed"
                free_bed_detail = f"Free Bed:  {TOTAL_CAPACITY - tot_occ} (EG2-A: {text_free_a}, EG2-B: {text_free_b})"

                recent_days[dt] = {
                    "date": dt,
                    "eg2a": patients_a,
                    "eg2b": patients_b,
                    "summary": {
                        "totalBeds": TOTAL_CAPACITY,
                        "capacityA": CAPACITY_EG2A,
                        "capacityB": CAPACITY_EG2B,
                        "occupied": tot_occ,
                        "empty": max(0, TOTAL_CAPACITY - tot_occ),
                        "freeBedDetail": free_bed_detail,
                        "textFreeA": text_free_a,
                        "textFreeB": text_free_b,
                        "bor": bor,
                        "borA": round((occ_a / CAPACITY_EG2A) * 100, 1),
                        "borB": round((occ_b / CAPACITY_EG2B) * 100, 1),
                        "occA": occ_a,
                        "occB": occ_b,
                        "emptyA": max(0, CAPACITY_EG2A - occ_a),
                        "emptyB": max(0, CAPACITY_EG2B - occ_b),
                        "dischargedToday": discharges_today,
                        "tagCounts": tag_counts
                    }
                }

    # Monthly Aggregation
    monthly_data = {}
    for dt, stat in daily_stats.items():
        m_key = dt[:7]
        if m_key not in monthly_data:
            monthly_data[m_key] = {
                "month": m_key,
                "days": 0,
                "totalHP": 0,
                "totalHPA": 0,
                "totalHPB": 0,
                "totalDischarges": 0,
                "totalDeaths": 0,
                "totalDeathsGt48": 0
            }
        monthly_data[m_key]["days"] += 1
        monthly_data[m_key]["totalHP"] += stat["hp"]
        monthly_data[m_key]["totalHPA"] += stat.get("occA", 0)
        monthly_data[m_key]["totalHPB"] += stat.get("occB", 0)
        monthly_data[m_key]["totalDischarges"] += stat["discharges"]
        monthly_data[m_key]["totalDeaths"] += stat["deaths"]
        monthly_data[m_key]["totalDeathsGt48"] += stat["deathsGt48"]

    computed_months = []
    tot_hp_all = 0
    tot_d_all = 0
    tot_days_all = 0
    tot_deaths_all = 0
    tot_deaths_gt48_all = 0

    for m_key in sorted(monthly_data.keys()):
        m = monthly_data[m_key]
        A = TOTAL_CAPACITY
        T = m["days"]
        HP = m["totalHP"]
        D = max(1, m["totalDischarges"])
        Deaths = m["totalDeaths"]
        DeathsGt48 = m["totalDeathsGt48"]

        tot_hp_all += HP
        tot_d_all += D
        tot_days_all += T
        tot_deaths_all += Deaths
        tot_deaths_gt48_all += DeathsGt48

        bor = (HP / (A * T)) * 100
        avlos = HP / D
        toi = ((A * T) - HP) / D
        bto = D / A
        gdr = (Deaths / D) * 1000
        ndr = (DeathsGt48 / D) * 1000

        computed_months.append({
            "month": m_key,
            "days": T,
            "hp": HP,
            "hpA": m["totalHPA"],
            "hpB": m["totalHPB"],
            "discharges": D,
            "deaths": Deaths,
            "deathsGt48": DeathsGt48,
            "bor": round(bor, 2),
            "avlos": round(avlos, 2),
            "toi": round(toi, 2),
            "bto": round(bto, 2),
            "gdr": round(gdr, 2),
            "ndr": round(ndr, 2)
        })

    overall_bor = (tot_hp_all / (TOTAL_CAPACITY * tot_days_all)) * 100
    overall_avlos = tot_hp_all / tot_d_all
    overall_toi = ((TOTAL_CAPACITY * tot_days_all) - tot_hp_all) / tot_d_all
    overall_bto = tot_d_all / TOTAL_CAPACITY
    overall_gdr = (tot_deaths_all / tot_d_all) * 1000
    overall_ndr = (tot_deaths_gt48_all / tot_d_all) * 1000

    hospital_indicators = {
        "capacity": {
            "eg2a": CAPACITY_EG2A,
            "eg2b": CAPACITY_EG2B,
            "total": TOTAL_CAPACITY
        },
        "availableBeds": TOTAL_CAPACITY,
        "totalDays": tot_days_all,
        "totalHP": tot_hp_all,
        "totalDischarges": tot_d_all,
        "overall": {
            "bor": round(overall_bor, 2),
            "avlos": round(overall_avlos, 2),
            "toi": round(overall_toi, 2),
            "bto": round(overall_bto, 2),
            "gdr": round(overall_gdr, 2),
            "ndr": round(overall_ndr, 2)
        },
        "monthly": computed_months
    }

    with open("hospital_indicators.json", "w") as f_hosp:
        json.dump(hospital_indicators, f_hosp, indent=2)

    CLINICAL_DIAGNOSES = [
        ("Anemia (Semua Jenis)", [r"\bANEMIA\b"]),
        ("Chronic Kidney Disease (CKD / GGK)", [r"\bCKD\b", r"CHRONIC KIDNEY", r"GAGAL GINJAL KRONIK"]),
        ("Gangguan Elektrolit (Hipo/Hiperkalemia/Natremia)", [r"HIPOKALEMI", r"HIPONATREMI", r"HIPERKALEMI", r"HIPERALBUMIN", r"HIPOALBUMIN"]),
        ("Neoplasma / Kanker (Ca / Tumor)", [r"\bCA\b", r"CANCER", r"TUMOR", r"KANKER", r"CARCINOMA", r"LEUKEMIA", r"MYELOMA"]),
        ("Diabetes Melitus (DM)", [r"\bDM\b", r"DIABETES", r"ULKUS DM", r"GANGREN"]),
        ("Hipertensi (HT)", [r"\bHT\b", r"HIPERTENSI", r"HYPERTENSION"]),
        ("Dyspepsia / Sindrom Dispepsia", [r"DYSPEPSIA", r"DISPEPSIA", r"GASTRITIS", r"HEMATEMESIS", r"MELENA"]),
        ("Acute Kidney Injury (AKI)", [r"\bAKI\b", r"ACUTE KIDNEY", r"GAGAL GINJAL AKUT"]),
        ("Abdominal Pain / Akut Abdomen", [r"ABD\b.*PAIN", r"ABDOMINAL PAIN", r"NYERI PERUT", r"COLIC ABDOMEN", r"AKUT ABDOMEN"]),
        ("Fraktur / Trauma Ortopedi", [r"FRAKTUR", r"FRACTURE", r"DISLOKASI", r"TRAUMA"]),
        ("Hepatitis / Sirosis Hepatis", [r"HEPATITIS", r"SIROSIS", r"HBSAG"]),
        ("Gastroenteritis Akut (GEA)", [r"\bGEA\b", r"GASTROENTERITIS", r"DIARE", r"BAB CAIR"]),
        ("Penyakit Jantung (CHF / CAD / UAP)", [r"\bCHF\b", r"\bCAD\b", r"\bUAP\b", r"HEART FAILURE", r"GAGAL JANTUNG", r"INFARK"]),
        ("Penyakit Paru / Pneumonia / TB", [r"PNEUMONIA", r"TUBERKULOSIS", r"\bTB\b", r"EFFUSI PLEURA", r"TBC"]),
        ("Sepsis / Syok Septik", [r"SEPSIS", r"SEPTIC", r"SYOK SEPTIK"]),
        ("Apendisitis (Appendicitis)", [r"APP\b", r"APPENDISITIS", r"APENDISITIS"]),
    ]

    diag_patient_sets = defaultdict(set)
    for pkey, d_set in patient_diagnoses_text.items():
        all_text = " ".join(d_set)
        for dname, patterns in CLINICAL_DIAGNOSES:
            if any(re.search(pat, all_text) for pat in patterns):
                diag_patient_sets[dname].add(pkey)

    top_doctors = sorted([{"name": k, "count": len(v)} for k, v in doctor_patients.items()], key=lambda x: x["count"], reverse=True)[:15]
    top_diags = sorted([{"name": k, "count": len(v)} for k, v in diag_patient_sets.items()], key=lambda x: x["count"], reverse=True)[:10]
    total_patients_count = len(total_unique_patients)
    ins_distribution = sorted([{"name": k, "count": v} for k, v in insurance_counts.items()], key=lambda x: x["count"], reverse=True)

    monthly_stats = []
    for m in computed_months:
        monthly_stats.append({
            "month": m["month"],
            "avgOcc": round(m["hp"] / m["days"], 1),
            "avgOccA": round(m.get("hpA", 0) / m["days"], 1),
            "avgOccB": round(m.get("hpB", 0) / m["days"], 1),
            "avgBor": m["bor"],
            "daysCounted": m["days"]
        })

    payload = {
        "metadata": {
            "title": "Dashboard Ruang Enggang Gading 2",
            "subtitle": "Sistem Informasi Sensus Pasien & Operan Jaga Rawat Inap EG2A (16 Bed) & EG2B (40 Bed)",
            "hospital": "RSUD Dr. Soedarso Pontianak",
            "roomName": "Ruang Rawat Inap Enggang Gading 2",
            "capacity": {
                "eg2a": CAPACITY_EG2A,
                "eg2b": CAPACITY_EG2B,
                "total": TOTAL_CAPACITY
            },
            "wings": ["Enggang Gading 2A (16 Bed)", "Enggang Gading 2B (40 Bed)"],
            "lastUpdated": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "latestDate": latest_date,
            "totalDatesRecorded": len(all_dates),
            "dateRange": f"{all_dates[0]} s/d {all_dates[-1]}",
            "spreadsheetA": "https://docs.google.com/spreadsheets/d/1RtJzfTnuTu-cmZXW59aGUDpihhJ1kGm_z9BozUHsgsI/edit?usp=sharing",
            "spreadsheetB": "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/edit?usp=sharing",
            "colorDischargeDetection": True
        },
        "allDates": all_dates,
        "history": history,
        "monthly": monthly_stats,
        "analytics": {
            "topDoctors": top_doctors,
            "topDiagnoses": top_diags,
            "categories": top_diags,
            "totalPatients": total_patients_count,
            "insurances": ins_distribution
        },
        "hospitalIndicators": hospital_indicators,
        "recentDays": recent_days,
        "today": recent_days.get(latest_date)
    }

    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Dataset successfully built with color discharge detection!")
    print(f"Overall 2026: Total HP={tot_hp_all}, Discharges={tot_d_all}, BOR={overall_bor:.1f}%, AVLOS={overall_avlos:.1f}h, TOI={overall_toi:.2f}h, BTO={overall_bto:.1f}x")

if __name__ == "__main__":
    run()
