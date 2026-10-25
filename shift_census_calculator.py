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
            "2026-10-22_21:00": {
                "date": "2026-10-22",
                "shift": "21:00",
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
    Mendukung jadwal operan jaga resmi terkunci:
    - Shift Pagi  : 07.00 - 14.00 WIB (Pembanding: Shift Malam 07.00 WIB)
    - Shift Sore  : 14.00 - 20.00 WIB (Pembanding: Shift Pagi 14.00 WIB)
    - Shift Malam : 20.00 - 07.00 WIB (Pembanding: Shift Sore 20.00 WIB)
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
            "is_scheduled_checkpoint": (hour == 7 and minute <= 20)
        }
    # 14.00 - 19.59 => Shift Sore (Pembanding: Shift Pagi 14.00 WIB)
    elif 14.0 <= time_float < 20.0:
        return {
            "current_shift": "Shift Sore",
            "current_column": "SORE",
            "time_range": "14.00 - 20.00 WIB",
            "baseline_shift": "14:00",
            "baseline_name": "Shift Pagi (14.00 WIB)",
            "is_scheduled_checkpoint": (hour == 14 and minute <= 20)
        }
    # 20.00 - 06.59 => Shift Malam (Pembanding: Shift Sore 20.00 WIB)
    else:
        return {
            "current_shift": "Shift Malam",
            "current_column": "MALAM",
            "time_range": "20.00 - 07.00 WIB",
            "baseline_shift": "20:00",
            "baseline_name": "Shift Sore (20.00 WIB)",
            "is_scheduled_checkpoint": (hour == 20 and minute <= 20)
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
    cur_date_str = now.strftime("%Y-%m-%d")
    hour = now.hour
    minute = now.minute

    def fmt_metric(val):
        """
        Format metrik sensus WhatsApp:
        Jika nilai yang ditemukan nihil / tidak ada / 0 / None / '', isi format dengan '-', bukan '0'.
        Hanya tampilkan angka jika > 0.
        """
        if val is None or val == "" or val == "-" or str(val).strip() == "-":
            return "-"
        try:
            num = int(val)
            if num <= 0:
                return "-"
            return str(num)
        except (ValueError, TypeError):
            if str(val).strip() in ["0", "nihil", "none", "null"]:
                return "-"
            return str(val).strip()

    # 1. Tentukan Jadwal Shift & Slot Checkpoint
    slot_key = None
    if mode == "shift_07" or (mode == "auto" and hour == 7 and minute <= 20):
        shift_name = "Shift Malam"
        slot_key = f"{cur_date_str}_07:00"
        baseline_pref = "20:00"
        shift_header_note = "Laporan Sensus Terjadwal (Akhir Shift Malam 07.00 WIB)"
    elif mode == "shift_14" or (mode == "auto" and hour == 14 and minute <= 20):
        shift_name = "Shift Pagi"
        slot_key = f"{cur_date_str}_14:00"
        baseline_pref = "07:00"
        shift_header_note = "Laporan Sensus Terjadwal (Akhir Shift Pagi 14.00 WIB)"
    elif mode in ["shift_20", "shift_21"] or (mode == "auto" and hour == 20 and minute <= 30):
        shift_name = "Shift Sore"
        slot_key = f"{cur_date_str}_20:00"
        baseline_pref = "14:00"
        shift_header_note = "Laporan Sensus Terjadwal (Akhir Shift Sore 20.00 WIB)"
    else:
        sinfo = get_current_shift_info(now)
        shift_name = sinfo["current_shift"]
        baseline_pref = sinfo["baseline_shift"]
        shift_header_note = f"Laporan Sensus Real-Time ({sinfo['current_shift']} • Pembanding {sinfo['baseline_name']})"

    # 2. Cari Px Awal Pembanding dari Checkpoint Sebelumnya
    baseline_px = 52
    candidates = []
    if baseline_pref == "07:00":
        candidates = [f"{cur_date_str}_07:00"]
    elif baseline_pref == "14:00":
        candidates = [f"{cur_date_str}_14:00"]
    elif baseline_pref in ["20:00", "21:00"]:
        prev_date_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        candidates = [f"{cur_date_str}_20:00", f"{cur_date_str}_21:00", f"{prev_date_str}_20:00", f"{prev_date_str}_21:00"]

    found_baseline = False
    for c in candidates:
        if c in ck_map and "px_skrg" in ck_map[c]:
            baseline_px = ck_map[c]["px_skrg"]
            found_baseline = True
            break
            
    if not found_baseline and ck_map:
        sorted_keys = sorted(ck_map.keys())
        for k in reversed(sorted_keys):
            if k <= f"{cur_date_str}_{hour:02d}:{minute:02d}" and "px_skrg" in ck_map[k]:
                baseline_px = ck_map[k]["px_skrg"]
                break

    px_awal = baseline_px

    # 3. Px Sekarang dari jumlah pasien aktif saat ini di spreadsheet (tidak diwarnai / dirawat)
    occ_a = today_summary.get("occA", 16)
    occ_b = today_summary.get("occB", 34)
    px_skrg = today_summary.get("occupied", occ_a + occ_b)

    # 4. Deteksi Kematian (Meninggal)
    deaths = today_summary.get("deathsToday", 0)

    # 5. Persamaan Keseimbangan Sensus Pasien
    # Px awal + Px baru - (Px pulang + Px meninggal + Px pindah) = Px sekarang
    delta = px_skrg - px_awal
    px_pindah = "-"
    renc_pulang = "-"
    renc_pindah = "-"

    if delta > 0:
        # Netto pasien bertambah
        px_baru = delta
        px_pulang = "-"
        px_meninggal = "-"
    else:
        # Pasien berkurang / tetap
        px_baru = "-"
        total_keluar = px_awal - px_skrg
        if total_keluar > 0 and deaths > 0:
            px_meninggal = min(deaths, total_keluar)
            n_pulang = max(0, total_keluar - px_meninggal)
            px_pulang = n_pulang if n_pulang > 0 else "-"
        elif total_keluar > 0:
            px_meninggal = "-"
            px_pulang = total_keluar
        else:
            px_meninggal = "-"
            px_pulang = "-"

    # 6. Kapasitas & Free Bed
    free_bed = 56 - px_skrg
    bor = f"{(px_skrg / 56 * 100):.1f}%".replace(".", ",")
    text_free_a = today_summary.get("textFreeA") or (f"{max(0, 4 - (occ_a - 12))} ekstra bed" if occ_a >= 12 else f"{12 - occ_a} + 4 ekstra bed")
    text_free_b = today_summary.get("textFreeB") or (f"{max(0, 4 - (occ_b - 36))} ekstra bed" if occ_b >= 36 else f"{36 - occ_b} + 4 ekstra bed")

    # 7. Simpan Checkpoint jika Terjadwal
    if slot_key:
        ck_map[slot_key] = {
            "date": cur_date_str,
            "shift": slot_key.split("_")[1],
            "shift_name": shift_name,
            "px_awal": px_awal,
            "px_baru": px_baru,
            "px_pulang": px_pulang,
            "px_pindah": px_pindah,
            "px_meninggal": px_meninggal,
            "px_skrg": px_skrg,
            "occ_a": occ_a,
            "occ_b": occ_b,
            "free_bed": free_bed,
            "text_free_a": text_free_a,
            "text_free_b": text_free_b,
            "bor": bor
        }
        # Tambahkan mirror 20:00 <-> 21:00 agar kompatibel dengan sistem pelacak shift
        if "20:00" in slot_key:
            ck_map[f"{cur_date_str}_21:00"] = dict(ck_map[slot_key], shift="21:00")
        elif "21:00" in slot_key:
            ck_map[f"{cur_date_str}_20:00"] = dict(ck_map[slot_key], shift="20:00")

        checkpoints_data["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")
        save_checkpoints(checkpoints_data)

    # Format nilai-nilai mutasi: jika 0 / nihil / tidak ada -> '-'
    f_px_baru = fmt_metric(px_baru)
    f_px_pindah = fmt_metric(px_pindah)
    f_px_meninggal = fmt_metric(px_meninggal)
    f_px_pulang = fmt_metric(px_pulang)
    f_renc_pulang = fmt_metric(renc_pulang)
    f_renc_pindah = fmt_metric(renc_pindah)

    # Format Pesan WhatsApp Baku Resmi (Sesuai Format Jam 20.00 EG2)
    wa_message = (
        "Ruang Enggang Gading 2\n"
        "Kapasitas: 56 Bed (EG2-A: 12 + 4 ekstra bed, EG2-B: 36 + 4 ekstra bed) \n\n"
        f"Px awal: {px_awal}\n"
        f"Px baru: {f_px_baru}\n"
        f"Px pindah: {f_px_pindah}\n"
        f"Px meninggal: {f_px_meninggal}\n"
        f"Px pulang: {f_px_pulang}\n"
        f"Renc pulang: {f_renc_pulang}\n"
        f"Renc pindah: {f_renc_pindah}\n\n"
        f"Px sekarang: {px_skrg}\n\n"
        "Antrean:\n\n"
        f"Free Bed:  {free_bed} (EG2-A: {text_free_a}, EG2-B: {text_free_b})\n\n"
        f"Persentase terisi: {bor}\n\n"
        "Rencana/Antrean Pindah:\n\n"
        "Makaseh 🙏\n"
        "Semoga sehat selalu 😊"
    )
    
    return {
        "message": wa_message,
        "note": shift_header_note,
        "stats": {
            "px_awal": px_awal,
            "px_baru": f_px_baru,
            "px_pindah": f_px_pindah,
            "px_meninggal": f_px_meninggal,
            "px_pulang": f_px_pulang,
            "renc_pulang": f_renc_pulang,
            "renc_pindah": f_renc_pindah,
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
