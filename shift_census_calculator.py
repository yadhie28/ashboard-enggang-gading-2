#!/usr/bin/env python3
"""
Modul Kalkulasi Sensus Pasien Berbasis Shift (Shift Census Engine)
Ruang Enggang Gading 2 - RSUD Dr. Soedarso Pontianak

Aturan Baku (Rule Tetap):
1. Kapanpun pengambilan data dilakukan (baik terjadwal maupun sewaktu-waktu),
   pembanding dasar hitung (Px awal) TETAP hasil hitung shift terakhir (07.00 / 14.00 / 20.00).
2. Shift Operasional:
   - Shift Pagi  : 07.00 - 14.00 WIB (Pembanding: Shift Malam 07.00 WIB)
   - Shift Sore  : 14.00 - 20.00 WIB (Pembanding: Shift Pagi 14.00 WIB)
   - Shift Malam : 20.00 - 07.00 WIB (Pembanding: Shift Sore 20.00 WIB)
3. Laporan Sensus Terjadwal Jam 07.00 Pagi:
   Menarik data akhir shift malam (tanggal kemarin malam) dengan pembanding Shift 20.00 WIB.
4. Laporan Sewaktu-waktu:
   Menarik data kolom shift berjalan hari ini dengan pembanding shift terakhir yang telah ditutup.
"""

import os
import json
import re
from datetime import datetime, date, timedelta

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CHECKPOINTS_FILE = os.path.join(DIRECTORY, "shift_checkpoints.json")
DASHBOARD_DATA_FILE = os.path.join(DIRECTORY, "dashboard_data.json")

def load_checkpoints():
    if os.path.exists(CHECKPOINTS_FILE):
        try:
            with open(CHECKPOINTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Initial default checkpoints based on verified census baseline
    return {
        "last_updated": "2026-10-23 07:00:00",
        "checkpoints": {
            "2026-10-22_20:00": {
                "date": "2026-10-22",
                "shift": "20:00",
                "shift_name": "Shift Sore",
                "px_skrg": 50,
                "occ_a": 13,
                "occ_b": 37,
                "free_bed": 6,
                "text_free_a": "3 ekstra bed",
                "text_free_b": "3 ekstra bed",
                "bor": "89.3%"
            },
            "2026-10-23_07:00": {
                "date": "2026-10-23",
                "shift": "07:00",
                "shift_name": "Shift Malam",
                "px_skrg": 50,
                "occ_a": 13,
                "occ_b": 37,
                "free_bed": 6,
                "text_free_a": "3 ekstra bed",
                "text_free_b": "3 ekstra bed",
                "bor": "89.3%"
            }
        }
    }

def save_checkpoints(data):
    try:
        with open(CHECKPOINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Failed to save shift_checkpoints.json: {e}")

def get_current_shift_info(now=None):
    """
    Menentukan shift saat ini dan shift pembanding terakhir.
    """
    if now is None:
        now = datetime.now()
    
    hour = now.hour
    minute = now.minute
    time_float = hour + minute / 60.0
    
    # 07.00 - 13.59 => Shift Pagi (Pembanding: Shift Malam 07.00 WIB)
    if 7.0 <= time_float < 14.0:
        return {
            "current_shift": "Shift Pagi",
            "current_column": "PAGI",
            "time_range": "07.00 - 14.00 WIB",
            "baseline_shift": "07:00",
            "baseline_name": "Shift Malam (07.00 WIB)",
            "is_scheduled_checkpoint": (hour == 7 and minute <= 5)
        }
    # 14.00 - 19.59 => Shift Sore (Pembanding: Shift Pagi 14.00 WIB)
    elif 14.0 <= time_float < 20.0:
        return {
            "current_shift": "Shift Sore",
            "current_column": "SORE",
            "time_range": "14.00 - 20.00 WIB",
            "baseline_shift": "14:00",
            "baseline_name": "Shift Pagi (14.00 WIB)",
            "is_scheduled_checkpoint": (hour == 14 and minute <= 5)
        }
    # 20.00 - 06.59 => Shift Malam (Pembanding: Shift Sore 20.00 WIB)
    else:
        return {
            "current_shift": "Shift Malam",
            "current_column": "MALAM",
            "time_range": "20.00 - 07.00 WIB",
            "baseline_shift": "20:00",
            "baseline_name": "Shift Sore (20.00 WIB)",
            "is_scheduled_checkpoint": (hour == 20 and minute <= 5)
        }

def compute_census_report(mode="auto", custom_now=None):
    """
    Menyusun laporan sensus resmi dengan format pesan WhatsApp baku.
    mode:
      - 'auto' : otomatis deteksi shift & pembanding
      - 'shift_07' : laporan akhir shift malam (07.00 WIB)
      - 'shift_14' : laporan akhir shift pagi (14.00 WIB)
      - 'shift_20' : laporan akhir shift sore (20.00 WIB)
      - 'realtime' : penarikan sewaktu-waktu saat ini
    """
    now = custom_now or datetime.now()
    checkpoints_data = load_checkpoints()
    ck_map = checkpoints_data.get("checkpoints", {})
    
    # Load data dashboard
    dashboard_data = {}
    if os.path.exists(DASHBOARD_DATA_FILE):
        try:
            with open(DASHBOARD_DATA_FILE, "r", encoding="utf-8") as f:
                dashboard_data = json.load(f)
        except Exception:
            pass

    today_summary = dashboard_data.get("today", {}).get("summary", {})
    
    # CASE 1: Laporan Khusus Jam 07.00 WIB (Akhir Shift Malam Kemarin)
    if mode == "shift_07" or (mode == "auto" and now.hour == 7 and now.minute <= 15):
        # Data ditarik dari kolom shift malam tanggal kemarin
        # Pembanding: Shift 20.00 WIB sore kemarin
        prev_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        day_info = dashboard_data.get("recentDays", {}).get(prev_date, {}).get("summary", today_summary)
        
        occ_a = day_info.get("occA", 13)
        occ_b = day_info.get("occB", 37)
        px_skrg = occ_a + occ_b
        
        # Px awal dari checkpoint 20:00 kemarin
        baseline_ck = ck_map.get(f"{prev_date}_20:00", {})
        px_awal = baseline_ck.get("px_skrg", px_skrg)
        
        # Hitung mutasi delta terhadap shift pembanding (20:00 WIB kemarin)
        delta = px_skrg - px_awal
        if delta > 0:
            px_baru = delta
            px_pulang = 0
        elif delta < 0:
            px_baru = 0
            px_pulang = abs(delta)
        else:
            px_baru = 0
            px_pulang = 0
        
        px_meninggal = "-"
        px_pindah = "-"
        
        free_bed = 56 - px_skrg
        bor = f"{(px_skrg / 56 * 100):.1f}%"
        text_free_a = day_info.get("textFreeA", "3 ekstra bed")
        text_free_b = day_info.get("textFreeB", "3 ekstra bed")
        
        # Simpan checkpoint 07:00
        cur_date_str = now.strftime("%Y-%m-%d")
        ck_map[f"{cur_date_str}_07:00"] = {
            "date": cur_date_str,
            "shift": "07:00",
            "shift_name": "Shift Malam",
            "px_skrg": px_skrg,
            "occ_a": occ_a,
            "occ_b": occ_b,
            "free_bed": free_bed,
            "text_free_a": text_free_a,
            "text_free_b": text_free_b,
            "bor": bor
        }
        checkpoints_data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_checkpoints(checkpoints_data)
        
        shift_header_note = "Laporan Sensus Terjadwal (Akhir Shift Malam 07.00 WIB)"
        
    else:
        # CASE 2: Permintaan Sewaktu-waktu / Shift Berjalan Hari Ini
        sinfo = get_current_shift_info(now)
        cur_date_str = now.strftime("%Y-%m-%d")
        
        occ_a = today_summary.get("occA", 15)
        occ_b = today_summary.get("occB", 40)
        px_skrg = occ_a + occ_b
        
        # Cari checkpoint shift terakhir sebagai pembanding dasar hitung
        baseline_px = 50  # Default fallback ke 07:00 WIB
        baseline_key = None
        
        if sinfo["baseline_shift"] == "07:00":
            baseline_key = f"{cur_date_str}_07:00"
        elif sinfo["baseline_shift"] == "14:00":
            baseline_key = f"{cur_date_str}_14:00"
        elif sinfo["baseline_shift"] == "20:00":
            prev_date_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            baseline_key = f"{prev_date_str}_20:00"
            
        if baseline_key and baseline_key in ck_map:
            baseline_px = ck_map[baseline_key].get("px_skrg", 50)
        else:
            # Cari checkpoint terdekat yang ada sebelum waktu sekarang
            available_keys = sorted(ck_map.keys())
            if available_keys:
                baseline_px = ck_map[available_keys[-1]].get("px_skrg", 50)
                
        px_awal = baseline_px
        
        # Hitung mutasi delta real-time terhadap shift pembanding
        delta = px_skrg - px_awal
        if delta > 0:
            px_baru = delta
            px_pulang = 0
        elif delta < 0:
            px_baru = 0
            px_pulang = abs(delta)
        else:
            px_baru = 0
            px_pulang = 0
            
        px_pindah = "-"
        px_meninggal = "-"
        
        free_bed = 56 - px_skrg
        bor = f"{(px_skrg / 56 * 100):.1f}%"
        text_free_a = today_summary.get("textFreeA", f"{max(0, 4 - (occ_a - 12))} ekstra bed" if occ_a >= 12 else f"{12 - occ_a} + 4 ekstra bed")
        text_free_b = today_summary.get("textFreeB", f"{max(0, 4 - (occ_b - 36))} ekstra bed" if occ_b >= 36 else f"{36 - occ_b} + 4 ekstra bed")
        
        shift_header_note = f"Laporan Sensus Real-Time ({sinfo['current_shift']} • Pembanding {sinfo['baseline_name']})"

    # Format Pesan WhatsApp Baku
    wa_message = (
        "*Ruang Enggang Gading 2*\n"
        "Kapasitas: 56 Bed (EG2-A: 12 + 4 ekstra bed, EG2-B: 36 + 4 ekstra bed) \n\n"
        f"*Px awal: {px_awal}*\n"
        f"Px baru: {px_baru}\n"
        f"Px pindah: {px_pindah}\n"
        f"Px meninggal: {px_meninggal}\n"
        f"Px pulang: {px_pulang}\n"
        "Renc pulang: -\n"
        "Renc pindah: -\n\n"
        f"*Px sekarang: {px_skrg}*\n\n"
        "*Antrean:*\n\n"
        f"*Free Bed:  {free_bed} (EG2-A: {text_free_a}, EG2-B: {text_free_b})*\n\n"
        f"*Persentase terisi: {bor}*\n\n"
        "*Rencana/Antrean Pindah:*\n\n"
        "Makaseh 🙏\n"
        "*Semoga sehat selalu 😊*"
    )
    
    return {
        "message": wa_message,
        "note": shift_header_note,
        "stats": {
            "px_awal": px_awal,
            "px_baru": px_baru,
            "px_pindah": px_pindah,
            "px_meninggal": px_meninggal,
            "px_pulang": px_pulang,
            "px_skrg": px_skrg,
            "free_bed": free_bed,
            "text_free_a": text_free_a,
            "text_free_b": text_free_b,
            "bor": bor,
            "occ_a": occ_a,
            "occ_b": occ_b
        },
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }

if __name__ == "__main__":
    rep = compute_census_report(mode="auto")
    print(f"[{rep['note']} - {rep['timestamp']}]")
    print("-" * 50)
    print(rep["message"])
