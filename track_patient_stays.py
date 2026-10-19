import zipfile
import xml.etree.ElementTree as ET
import re
import json
from datetime import datetime, date, timedelta
from parse_sheets import parse_shared_strings, get_sheets_info
from run_build_data import extract_date_from_sheet, parse_worksheet, parse_patient_row

print("Tracking patient stays across all days...")

with zipfile.ZipFile("EG2A.xlsx", "r") as z_a, zipfile.ZipFile("EG2B.xlsx", "r") as z_b:
    ss_a = parse_shared_strings(z_a)
    sheets_a = get_sheets_info(z_a)
    date_map_a = {}
    for s in sheets_a:
        if "MASTER" in s["name"].upper(): continue
        dt = extract_date_from_sheet(z_a, s, ss_a)
        if dt: date_map_a[dt] = s

    ss_b = parse_shared_strings(z_b)
    sheets_b = get_sheets_info(z_b)
    date_map_b = {}
    for s in sheets_b:
        dt = extract_date_from_sheet(z_b, s, ss_b)
        if dt: date_map_b[dt] = s

    all_dates = sorted([d for d in set(list(date_map_a.keys()) + list(date_map_b.keys())) if "2026-01-01" <= d <= "2026-12-31"])
    print(f"Analyzing {len(all_dates)} days from {all_dates[0]} to {all_dates[-1]}...")

    # We will track daily census:
    # - HP (Hari Perawatan): sum of occupied beds on that day
    # - New admissions on that day
    # - Discharges on that day (patients present on day T who are no longer present on day T+1)
    # - Deaths (notes mention death/meninggal on that day)

    daily_stats = {}
    prev_patients = set()

    for i, dt in enumerate(all_dates):
        curr_patients_map = {}
        patients = []

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
                    if pt and not pt["isEmpty"]:
                        patients.append(pt)

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
                    if pt and not pt["isEmpty"]:
                        patients.append(pt)

        # Build unique key for patients
        curr_p_keys = set()
        deaths_today = 0
        death_gt48_today = 0

        for p in patients:
            # Key by MR if available, else clean name
            pkey = p["mrNo"] if (p["mrNo"] and len(p["mrNo"]) > 4) else p["name"]
            curr_p_keys.add(pkey)
            curr_patients_map[pkey] = p

            notes = (p["notes"]["pagi"] + " " + p["notes"]["sore"] + " " + p["notes"]["malam"]).upper()
            if any(k in notes for k in ["MENINGGAL JAM", "MENINGGAL PUKUL", "EXIT JAM", "EXIT PUKUL", "WAFAT JAM", "WAFAT PUKUL", "MENINGGAL DI RUANGAN", "PX MENINGGAL", "PASIEN MENINGGAL", "DEATH"]):
                deaths_today += 1
                if p["los"] >= 2:
                    death_gt48_today += 1

        # Patients discharged between yesterday and today
        discharges_today = 0
        if i > 0:
            discharged_keys = prev_patients - curr_p_keys
            discharges_today = len(discharged_keys)

        new_admissions = len(curr_p_keys - prev_patients) if i > 0 else len(curr_p_keys)

        daily_stats[dt] = {
            "date": dt,
            "hp": len(patients),
            "availableBeds": 56, # standard total bed capacity
            "discharges": discharges_today,
            "newAdmissions": new_admissions,
            "deaths": deaths_today,
            "deathsGt48": death_gt48_today,
            "patients": curr_patients_map
        }

        prev_patients = curr_p_keys

    # Now aggregate monthly
    monthly_data = {}
    for dt, stat in daily_stats.items():
        m_key = dt[:7] # YYYY-MM
        if m_key not in monthly_data:
            monthly_data[m_key] = {
                "month": m_key,
                "days": 0,
                "totalHP": 0,
                "totalDischarges": 0,
                "totalAdmissions": 0,
                "totalDeaths": 0,
                "totalDeathsGt48": 0,
                "availableBeds": 56
            }
        monthly_data[m_key]["days"] += 1
        monthly_data[m_key]["totalHP"] += stat["hp"]
        monthly_data[m_key]["totalDischarges"] += stat["discharges"]
        monthly_data[m_key]["totalAdmissions"] += stat["newAdmissions"]
        monthly_data[m_key]["totalDeaths"] += stat["deaths"]
        monthly_data[m_key]["totalDeathsGt48"] += stat["deathsGt48"]

    print("\n" + "="*80)
    print("REKAPITULASI INDIKATOR PELAYANAN RAWAT INAP (KEMENKES & BARBER JOHNSON)")
    print("RUANG ENGGANG GADING 2 (EG2A & EG2B) TAHUN 2026")
    print("="*80)
    print(f"{'Bulan':<10} | {'Hari':<4} | {'HP':<6} | {'Keluar':<6} | {'BOR (%)':<7} | {'AVLOS':<6} | {'TOI':<6} | {'BTO':<5} | {'GDR(‰)':<6} | {'NDR(‰)'}")
    print("-" * 80)

    computed_months = []
    tot_hp_all = 0
    tot_d_all = 0
    tot_days_all = 0
    tot_deaths_all = 0
    tot_deaths_gt48_all = 0

    for m_key in sorted(monthly_data.keys()):
        m = monthly_data[m_key]
        A = m["availableBeds"] # 56
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

        # Standard Formulas:
        # BOR = (HP / (A * T)) * 100
        # AVLOS = HP / D
        # TOI = ((A * T) - HP) / D
        # BTO = D / A
        # GDR = (Deaths / D) * 1000
        # NDR = (DeathsGt48 / D) * 1000

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
            "discharges": D,
            "admissions": m["totalAdmissions"],
            "deaths": Deaths,
            "deathsGt48": DeathsGt48,
            "bor": round(bor, 2),
            "avlos": round(avlos, 2),
            "toi": round(toi, 2),
            "bto": round(bto, 2),
            "gdr": round(gdr, 2),
            "ndr": round(ndr, 2)
        })

        print(f"{m_key:<10} | {T:<4} | {HP:<6} | {D:<6} | {bor:6.1f}% | {avlos:5.1f}h | {toi:5.2f}h | {bto:4.1f}x | {gdr:5.1f}‰ | {ndr:4.1f}‰")

    # Total Overall Year
    A_all = 56
    overall_bor = (tot_hp_all / (A_all * tot_days_all)) * 100
    overall_avlos = tot_hp_all / tot_d_all
    overall_toi = ((A_all * tot_days_all) - tot_hp_all) / tot_d_all
    overall_bto = tot_d_all / A_all
    overall_gdr = (tot_deaths_all / tot_d_all) * 1000
    overall_ndr = (tot_deaths_gt48_all / tot_d_all) * 1000

    print("-" * 80)
    print(f"{'TOTAL 2026':<10} | {tot_days_all:<4} | {tot_hp_all:<6} | {tot_d_all:<6} | {overall_bor:6.1f}% | {overall_avlos:5.1f}h | {overall_toi:5.2f}h | {overall_bto:4.1f}x | {overall_gdr:5.1f}‰ | {overall_ndr:4.1f}‰")

    with open("hospital_indicators.json", "w") as f:
        json.dump({
            "availableBeds": A_all,
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
        }, f, indent=2)
    print("\nSaved hospital_indicators.json successfully!")

