import zipfile
import xml.etree.ElementTree as ET
import re
import json
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from parse_sheets import parse_shared_strings, get_sheets_info
from run_build_data import extract_date_from_sheet, parse_worksheet, parse_patient_row

CAPACITY_EG2A = 16
CAPACITY_EG2B = 40
TOTAL_CAPACITY = 56

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
    print(f"Running data rebuild with fixed capacity: EG2A={CAPACITY_EG2A}, EG2B={CAPACITY_EG2B}, TOTAL={TOTAL_CAPACITY}...")

    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a:
        ss_a = parse_shared_strings(z_a)
        sheets_a = get_sheets_info(z_a)
        date_map_a = {}
        for s in sheets_a:
            if "MASTER" in s["name"].upper(): continue
            dt = extract_date_from_sheet(z_a, s, ss_a)
            if dt: date_map_a[dt] = s

    with zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        ss_b = parse_shared_strings(z_b)
        sheets_b = get_sheets_info(z_b)
        date_map_b = {}
        for s in sheets_b:
            dt = extract_date_from_sheet(z_b, s, ss_b)
            if dt: date_map_b[dt] = s

    all_dates = sorted([d for d in set(list(date_map_a.keys()) + list(date_map_b.keys())) if "2026-01-01" <= d <= "2026-12-31"])
    latest_date = all_dates[-1]

    history = []
    doctor_patients = defaultdict(set)
    diag_counts = {}
    cat_counts = {}
    insurance_counts = {}
    recent_days = {}

    # For hospital indicators
    daily_stats = {}
    prev_patients = set()

    with zipfile.ZipFile("EG2A.xlsx", "r") as z_a, zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
        for idx, dt in enumerate(all_dates):
            is_recent = (idx >= len(all_dates) - 45)
            
            raw_patients_a = []
            if dt in date_map_a:
                rows_a = parse_worksheet(z_a, date_map_a[dt]["filename"], ss_a)
                header_passed = False
                for r_idx in sorted(rows_a.keys()):
                    r = rows_a[r_idx]
                    vals = [str(v).upper() for v in r.values()]
                    if any("TGL MASUK" in v or "TANGGAL MASUK" in v for v in vals):
                        header_passed = True
                        continue
                    if header_passed and (r.get("A") or r.get("C")):
                        pt = parse_patient_row(r, "EG2A", dt)
                        if pt: raw_patients_a.append(pt)

            raw_patients_b = []
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
                        if pt: raw_patients_b.append(pt)

            # Normalize to 16 and 40 beds
            patients_a = normalize_wing_beds(raw_patients_a, "EG2A", CAPACITY_EG2A)
            patients_b = normalize_wing_beds(raw_patients_b, "EG2B", CAPACITY_EG2B)

            occ_a = len([p for p in patients_a if not p["isEmpty"]])
            occ_b = len([p for p in patients_b if not p["isEmpty"]])
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

            # Indicators tracking
            curr_p_keys = set()
            deaths_today = 0
            death_gt48_today = 0

            for p in patients_a + patients_b:
                if not p["isEmpty"]:
                    pkey = p["mrNo"] if (p["mrNo"] and len(p["mrNo"]) > 4) else p["name"]
                    curr_p_keys.add(pkey)

                    doc = p["doctorPrimary"]
                    if doc and doc != "-" and len(doc) > 3:
                        pkey = p["mrNo"].strip() if (p["mrNo"] and len(p["mrNo"].strip()) > 3) else p["name"].strip().upper()
                        doctor_patients[doc].add(pkey)
                    cat = p["category"]
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                    ins = p["insurance"]
                    insurance_counts[ins] = insurance_counts.get(ins, 0) + 1
                    diag_raw = p["diagnosis"].split("\n")[0].strip()[:45]
                    if diag_raw and diag_raw != "-" and len(diag_raw) > 3:
                        diag_counts[diag_raw] = diag_counts.get(diag_raw, 0) + 1

                    notes = (p["notes"]["pagi"] + " " + p["notes"]["sore"] + " " + p["notes"]["malam"]).upper()
                    if any(k in notes for k in ["MENINGGAL JAM", "MENINGGAL PUKUL", "EXIT JAM", "EXIT PUKUL", "WAFAT JAM", "WAFAT PUKUL", "MENINGGAL DI RUANGAN", "PX MENINGGAL", "PASIEN MENINGGAL", "DEATH"]):
                        deaths_today += 1
                        if p["los"] >= 2:
                            death_gt48_today += 1

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
                        "bor": bor,
                        "borA": round((occ_a / CAPACITY_EG2A) * 100, 1),
                        "borB": round((occ_b / CAPACITY_EG2B) * 100, 1),
                        "occA": occ_a,
                        "occB": occ_b,
                        "emptyA": max(0, CAPACITY_EG2A - occ_a),
                        "emptyB": max(0, CAPACITY_EG2B - occ_b),
                        "tagCounts": tag_counts
                    }
                }

    # Monthly Aggregation for Barber Johnson & Hospital Indicators
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
        A = TOTAL_CAPACITY # 56
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

    top_doctors = sorted([{"name": k, "count": len(v)} for k, v in doctor_patients.items()], key=lambda x: x["count"], reverse=True)[:15]
    top_diags = sorted([{"name": k, "count": v} for k, v in diag_counts.items()], key=lambda x: x["count"], reverse=True)[:15]
    cat_distribution = sorted([{"name": k, "count": v} for k, v in cat_counts.items()], key=lambda x: x["count"], reverse=True)
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
            "spreadsheetB": "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/edit?usp=sharing"
        },
        "allDates": all_dates,
        "history": history,
        "monthly": monthly_stats,
        "analytics": {
            "topDoctors": top_doctors,
            "topDiagnoses": top_diags,
            "categories": cat_distribution,
            "insurances": ins_distribution
        },
        "hospitalIndicators": hospital_indicators,
        "recentDays": recent_days,
        "today": recent_days.get(latest_date)
    }

    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Dataset rebuilt successfully!")
    print(f"Latest day summary (18-10-2026):")
    print(f"  EG2A: {len(recent_days[latest_date]['eg2a'])} beds (Occupied: {recent_days[latest_date]['summary']['occA']}, Empty: {recent_days[latest_date]['summary']['emptyA']})")
    print(f"  EG2B: {len(recent_days[latest_date]['eg2b'])} beds (Occupied: {recent_days[latest_date]['summary']['occB']}, Empty: {recent_days[latest_date]['summary']['emptyB']})")
    print(f"  Total Beds: {recent_days[latest_date]['summary']['totalBeds']}, Total Occupied: {recent_days[latest_date]['summary']['occupied']}, BOR: {recent_days[latest_date]['summary']['bor']}%")

if __name__ == "__main__":
    run()
