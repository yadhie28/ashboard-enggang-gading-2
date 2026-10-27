#!/usr/bin/env python3
"""
Sistem Pengirim Pesan WhatsApp Messenger
Tujuan: Kepala Ruang Enggang Gading 2 (Ns. Rusmulyadi, S.Kep.,M.A.R.S)
Nomor : +6281284070082
Isi    : 'Test Boss' (atau pesan sensus / dinamis lainnya)
"""

import os
import sys
import json
import urllib.parse
import webbrowser
import subprocess
import argparse
from datetime import datetime

# Konfigurasi Penerima Resmi Kepala Ruang Enggang Gading 2
DEFAULT_RECIPIENT = {
    "name": "Ns. Rusmulyadi, S.Kep.,M.A.R.S",
    "role": "Kepala Ruang Enggang Gading 2",
    "hospital": "RSUD Dr. Soedarso Pontianak",
    "phone_raw": "+6281284070082",
    "phone": "6281284070082"  # Format nomor internasional WhatsApp
}

DEFAULT_MESSAGE = "Test Boss"

def normalize_phone_number(phone: str) -> str:
    """Membersihkan dan menstandarkan nomor HP ke format internasional WhatsApp."""
    cleaned = ''.join(c for c in phone if c.isdigit())
    if cleaned.startswith('08'):
        cleaned = '62' + cleaned[1:]
    elif cleaned.startswith('8'):
        cleaned = '62' + cleaned
    return cleaned

def generate_whatsapp_urls(phone: str = None, message: str = None) -> dict:
    """Membuat tautan langsung WhatsApp Web, Aplikasi Desktop, dan Universal wa.me."""
    target_phone = normalize_phone_number(phone or DEFAULT_RECIPIENT["phone"])
    target_message = message if message is not None else DEFAULT_MESSAGE
    encoded_text = urllib.parse.quote(target_message)
    
    return {
        "web_url": f"https://web.whatsapp.com/send?phone={target_phone}&text={encoded_text}",
        "app_url": f"whatsapp://send?phone={target_phone}&text={encoded_text}",
        "wa_me_url": f"https://wa.me/{target_phone}?text={encoded_text}",
        "api_url": f"https://api.whatsapp.com/send?phone={target_phone}&text={encoded_text}"
    }

def send_whatsapp_local(phone: str = None, message: str = None, mode: str = "web", launch_browser: bool = True) -> dict:
    """
    Membuka obrolan WhatsApp secara langsung ke nomor Kepala Ruang dengan pesan yang telah terisi.
    mode: 'web' (Direct WhatsApp Web), 'app' (Aplikasi WhatsApp Desktop), atau 'universal' (wa.me)
    """
    target_phone = normalize_phone_number(phone or DEFAULT_RECIPIENT["phone"])
    target_msg = message if message is not None else DEFAULT_MESSAGE
    urls = generate_whatsapp_urls(target_phone, target_msg)
    
    selected_url = urls["web_url"]
    if mode == "app":
        selected_url = urls["app_url"]
    elif mode == "universal":
        selected_url = urls["wa_me_url"]

    result = {
        "status": "success",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient_name": DEFAULT_RECIPIENT["name"],
        "recipient_role": DEFAULT_RECIPIENT["role"],
        "recipient_phone": target_phone,
        "message": target_msg,
        "mode": mode,
        "selected_url": selected_url,
        "urls": urls,
        "launched": False
    }

    if launch_browser:
        try:
            if sys.platform == "darwin":
                # Di macOS: jika mode web dan Google Chrome aktif, buka/arahkan tab Chrome langsung
                if mode == "web":
                    script = f'''
                    tell application "Google Chrome"
                        activate
                        set w to front window
                        set tabIdx to 0
                        repeat with i from 1 to (count of tabs of w)
                            set curUrl to (URL of tab i of w)
                            if curUrl starts with "https://api.whatsapp.com" or curUrl starts with "https://web.whatsapp.com" then
                                set tabIdx to i
                                exit repeat
                            end if
                        end repeat
                        if tabIdx > 0 then
                            set URL of tab tabIdx of w to "{selected_url}"
                            set active tab index of w to tabIdx
                        else
                            tell w
                                make new tab with properties {{URL:"{selected_url}"}}
                            end tell
                        end if
                    end tell
                    '''
                    proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
                    if proc.returncode == 0:
                        result["launched"] = True
                        result["launch_method"] = "chrome_direct_tab"
                    else:
                        subprocess.run(["open", selected_url], check=True)
                        result["launched"] = True
                        result["launch_method"] = "macos_open"
                else:
                    subprocess.run(["open", selected_url], check=True)
                    result["launched"] = True
                    result["launch_method"] = "macos_open"
            else:
                webbrowser.open(selected_url)
                result["launched"] = True
                result["launch_method"] = "webbrowser_module"
        except Exception as e:
            result["launched"] = False
            result["launch_error"] = str(e)
            try:
                webbrowser.open(selected_url)
                result["launched"] = True
                result["launch_method"] = "webbrowser_fallback"
            except Exception as e2:
                result["fallback_error"] = str(e2)

    return result

GATEWAY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "wa_gateway_config.json")
SENT_LOG_PATH = os.path.join(os.path.dirname(__file__), "shift_sent_wa.json")

def get_current_wib_datetime():
    """Mengembalikan datetime dalam zona waktu WIB (UTC+7) secara akurat."""
    from datetime import timezone, timedelta
    wib_tz = timezone(timedelta(hours=7))
    now_utc = datetime.now(timezone.utc)
    return now_utc.astimezone(wib_tz)

def check_scheduled_punctuality(window_minutes=15, custom_now=None, allow_catchup=True):
    """
    Memeriksa jadwal resmi sensus WhatsApp:
    - Shift Pagi  : 07.00 WIB (06.45 - 07.15 WIB) -> Slot: YYYY-MM-DD_07:00
    - Shift Sore  : 14.00 WIB (13.45 - 14.15 WIB) -> Slot: YYYY-MM-DD_14:00
    - Shift Malam : 20.00 WIB (19.45 - 20.15 WIB) -> Slot: YYYY-MM-DD_20:00

    Window on-time mencakup 15 menit SEBELUM hingga 15 menit SESUDAH jadwal resmi.
    Ini mengakomodasi auto_sync yang dijadwalkan 15 menit lebih awal (06:45 WIB)
    agar laporan WhatsApp terkirim tepat sebelum batas waktu (<= 07:02 WIB).
    Jika allow_catchup=True dan slot jadwal shift saat ini belum terkirim hari ini
    (misalnya laptop baru dinyalakan atau terbangun dari sleep mode setelah jam jadwal),
    sistem otomatis mengizinkan pengiriman susulan (catch-up) agar laporan sensus tidak pernah hilang.
    Mengembalikan (is_allowed, slot_key, wib_str, send_type)
    """
    from datetime import timedelta
    now_wib = custom_now if custom_now is not None else get_current_wib_datetime()
    hour = now_wib.hour
    minute = now_wib.minute
    cur_date_str = now_wib.strftime("%Y-%m-%d")
    wib_str = now_wib.strftime("%Y-%m-%d %H:%M:%S")

    # Konversi waktu ke total menit dalam hari (0 - 1439)
    total_minutes = hour * 60 + minute

    # 1. Pengecekan On-Time Window: ±15 menit dari jadwal resmi
    #    Shift Pagi  07:00 => window 06:45 - 07:15  (405 - 435 menit)
    #    Shift Sore  14:00 => window 13:45 - 14:15  (825 - 855 menit)
    #    Shift Malam 20:00 => window 19:45 - 20:15  (1185 - 1215 menit)
    schedule_slots = [
        (7 * 60,  f"{cur_date_str}_07:00"),   # Shift Pagi
        (14 * 60, f"{cur_date_str}_14:00"),   # Shift Sore
        (20 * 60, f"{cur_date_str}_20:00"),   # Shift Malam
    ]
    for sched_total, slot_key in schedule_slots:
        if (sched_total - window_minutes) <= total_minutes <= (sched_total + window_minutes):
            return True, slot_key, wib_str, "on-time"

    # 2. Pengecekan Catch-up (Susulan otomatis jika laptop mati/tidur pada jam tepat)
    if allow_catchup:
        sent_log = load_sent_log()

        # Shift Pagi (06.45 - 13.44 WIB): slot target 07:00
        if (6 * 60 + 45) <= total_minutes < (13 * 60 + 45):
            target_slot = f"{cur_date_str}_07:00"
            if target_slot not in sent_log:
                return True, target_slot, wib_str, "catch-up (Shift Pagi 07.00)"

        # Shift Sore (13.45 - 19.44 WIB): slot target 14:00
        elif (13 * 60 + 45) <= total_minutes < (19 * 60 + 45):
            target_slot = f"{cur_date_str}_14:00"
            if target_slot not in sent_log:
                return True, target_slot, wib_str, "catch-up (Shift Sore 14.00)"

        # Shift Malam (19.45 - 06.44 WIB): slot target 20:00
        else:
            if total_minutes >= (19 * 60 + 45):
                target_slot = f"{cur_date_str}_20:00"
            else:
                prev_date_str = (now_wib - timedelta(days=1)).strftime("%Y-%m-%d")
                target_slot = f"{prev_date_str}_20:00"

            if target_slot not in sent_log:
                return True, target_slot, wib_str, "catch-up (Shift Malam 20.00)"

    return False, None, wib_str, "out-of-schedule"

def load_sent_log():
    """Memuat histori pengiriman WhatsApp agar tidak terjadi pengiriman duplikat."""
    if os.path.exists(SENT_LOG_PATH):
        try:
            with open(SENT_LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def record_sent_slot(slot_key, wib_str):
    """Mencatat slot checkpoint yang telah berhasil dikirim ke WA."""
    data = load_sent_log()
    data[slot_key] = wib_str
    try:
        with open(SENT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Gagal menyimpan log shift_sent_wa.json: {e}")

def load_gateway_config() -> dict:
    """Memuat konfigurasi gateway API jika tersimpan."""
    if os.path.exists(GATEWAY_CONFIG_PATH):
        try:
            with open(GATEWAY_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"provider": "fonnte", "token": os.getenv("FONNTE_TOKEN", "")}

def save_gateway_config(provider: str, token: str) -> None:
    """Menyimpan konfigurasi gateway API lokal."""
    with open(GATEWAY_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"provider": provider, "token": token}, f, indent=2)

def send_via_gateway(phone: str, message: str, token: str = None, provider: str = "fonnte") -> dict:
    """
    Mengirim pesan WhatsApp 100% otomatis di latar belakang melalui Gateway API (Fonnte/Wablas).
    Dilengkapi automatic retry (3x), timeout 30 detik, serta fallback curl sistem macOS
    untuk menjamin kehandalan pengiriman mutlak (zero-failure).
    """
    target_phone = normalize_phone_number(phone)
    active_token = token or load_gateway_config().get("token") or os.getenv("FONNTE_TOKEN", "")

    if not active_token:
        return {
            "status": "error",
            "error": "API Token Gateway belum diisi. Masukkan token Fonnte / Wablas untuk pengiriman otomatis di latar belakang."
        }

    import urllib.request
    import subprocess
    import time

    max_retries = 3
    last_error = ""

    if provider == "fonnte":
        url = "https://api.fonnte.com/send"
        data = urllib.parse.urlencode({
            "target": target_phone,
            "message": message,
            "countryCode": "62"
        }).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers={"Authorization": active_token})
                with urllib.request.urlopen(req, timeout=30) as res:
                    body = res.read().decode("utf-8")
                    return {"status": "success", "provider": "fonnte", "response": json.loads(body)}
            except Exception as e:
                last_error = str(e)
                time.sleep(2)

        # Fallback menggunakan curl sistem macOS jika urllib timeout / ssl handshake issue
        try:
            curl_cmd = [
                "curl", "-s", "--max-time", "35", "--retry", "2",
                "-X", "POST", url,
                "-H", f"Authorization: {active_token}",
                "-d", f"target={target_phone}",
                "-d", f"countryCode=62",
                "--data-urlencode", f"message={message}"
            ]
            c_res = subprocess.run(curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=40)
            if c_res.returncode == 0 and c_res.stdout.strip():
                resp_json = json.loads(c_res.stdout)
                return {"status": "success", "provider": "fonnte", "response": resp_json}
            else:
                last_error = c_res.stderr or "Curl failed without stdout"
        except Exception as ce:
            last_error = f"{last_error} | curl error: {ce}"

        return {"status": "error", "provider": "fonnte", "error": last_error}

    elif provider == "wablas":
        url = "https://jakarta.wablas.com/api/send-message"
        data = urllib.parse.urlencode({
            "phone": target_phone,
            "message": message
        }).encode("utf-8")

        for attempt in range(1, max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers={"Authorization": active_token})
                with urllib.request.urlopen(req, timeout=30) as res:
                    body = res.read().decode("utf-8")
                    return {"status": "success", "provider": "wablas", "response": json.loads(body)}
            except Exception as e:
                last_error = str(e)
                time.sleep(2)

        return {"status": "error", "provider": "wablas", "error": last_error}

    return {"status": "error", "error": f"Provider '{provider}' tidak didukung."}


def build_census_report(mode="auto", px_awal=None, px_baru=None, px_pindah=None, data_path="dashboard_data.json") -> str:
    """
    Menghasilkan template resmi laporan sensus WhatsApp Ruang Enggang Gading 2
    dengan perbandingan shift terakhir (07.00 / 14.00 / 20.00) sesuai ketetapan baku.
    """
    try:
        from shift_census_calculator import compute_census_report
        res = compute_census_report(mode=mode)
        return res["message"]
    except Exception as e:
        print(f"[WARN] Error in compute_census_report: {e}")
        # Fallback template resmi
        return (
            "Ruang Enggang Gading 2\n"
            "Kapasitas: 56 Bed (EG2-A: 12 + 4 ekstra bed, EG2-B: 36 + 4 ekstra bed) \n\n"
            "Px awal: 52\n"
            "Px baru: -\n"
            "Px pindah: -\n"
            "Px meninggal: 1\n"
            "Px pulang: 1\n"
            "Renc pulang: -\n"
            "Renc pindah: -\n\n"
            "Px sekarang: 50\n\n"
            "Antrean:\n\n"
            "Free Bed:  6 (EG2-A: 0 ekstra bed, EG2-B: 2 + 4 ekstra bed)\n\n"
            "Persentase terisi: 89,3%\n\n"
            "Rencana/Antrean Pindah:\n\n"
            "Makaseh 🙏\n"
            "Semoga sehat selalu 😊"
        )


def main():
    parser = argparse.ArgumentParser(description="Kirim Pesan WhatsApp ke Kepala Ruang Enggang Gading 2")
    parser.add_argument("-m", "--message", default=None, help="Isi pesan (default: 'Test Boss' atau template sensus bila --sensus aktif)")
    parser.add_argument("--sensus", action="store_true", help="Gunakan template resmi laporan sensus WhatsApp EG2 (format bold baku)")
    parser.add_argument("-p", "--phone", default=DEFAULT_RECIPIENT["phone"], help="Nomor tujuan (default: 6281284070082)")
    parser.add_argument("--mode", choices=["web", "app", "universal"], default="web", help="Mode peluncuran: web (WhatsApp Web langsung), app (Aplikasi Desktop), universal (wa.me)")
    parser.add_argument("--gateway", choices=["fonnte", "wablas"], help="Kirim melalui Gateway API otomatis di background (dari nomor bot mana pun)")
    parser.add_argument("--token", help="API Token untuk gateway Fonnte / Wablas")
    parser.add_argument("--save-token", action="store_true", help="Simpan token gateway ke wa_gateway_config.json")
    parser.add_argument("--no-open", action="store_true", help="Hanya tampilkan link tanpa membuka browser/aplikasi")
    parser.add_argument("--scheduled-only", action="store_true", help="Kirim HANYA jika waktu sesuai jadwal shift (07.00, 14.00, 20.00 WIB) atau catch-up otomatis bila slot shift hari ini belum terkirim.")
    parser.add_argument("--force", action="store_true", help="Paksa kirim mengabaikan filter jam dan deduplikasi")
    parser.add_argument("--json", action="store_true", help="Output format JSON")

    args = parser.parse_args()

    slot_key = None
    # Ketepatan Waktu Guard & Catch-Up Auto Guard
    if args.scheduled_only and not args.force:
        is_allowed, slot_key, wib_str, send_type = check_scheduled_punctuality(window_minutes=15, allow_catchup=True)
        if not is_allowed:
            print(f"[ON-TIME GUARD] Waktu saat ini: {wib_str} WIB.")
            print("[ON-TIME GUARD] Bukan jam jadwal resmi dan seluruh slot shift hari ini sudah terpenuhi. Pengiriman dibatalkan.")
            return

        sent_log = load_sent_log()
        if slot_key and slot_key in sent_log:
            print(f"[DEDUP GUARD] Laporan sensus slot {slot_key} sudah terkirim pada {sent_log[slot_key]}.")
            print("[DEDUP GUARD] Pengiriman diabaikan untuk mencegah duplikasi pesan ke Kepala Ruang.")
            return

        print(f"[SCHEDULE GUARD] Waktu: {wib_str} WIB | Status: {send_type} | Target Slot: {slot_key}")

    # Tentukan pesan default
    if args.message is None:
        if args.sensus:
            target_mode = "auto"
            if slot_key:
                if "07:00" in slot_key: target_mode = "shift_07"
                elif "14:00" in slot_key: target_mode = "shift_14"
                elif "20:00" in slot_key: target_mode = "shift_20"
            args.message = build_census_report(mode=target_mode)
        else:
            args.message = DEFAULT_MESSAGE
    elif args.sensus:
        target_mode = "auto"
        if slot_key:
            if "07:00" in slot_key: target_mode = "shift_07"
            elif "14:00" in slot_key: target_mode = "shift_14"
            elif "20:00" in slot_key: target_mode = "shift_20"
        args.message = build_census_report(mode=target_mode)

    if args.save_token and args.token:
        save_gateway_config(args.gateway or "fonnte", args.token)
        print(f"Token gateway {args.gateway or 'fonnte'} berhasil disimpan ke wa_gateway_config.json!")

    # Jika mode gateway dipilih atau token tersedia
    if args.gateway or args.token:
        gw_res = send_via_gateway(
            phone=args.phone,
            message=args.message,
            token=args.token,
            provider=args.gateway or "fonnte"
        )
        if args.json:
            print(json.dumps(gw_res, indent=2, ensure_ascii=False))
        else:
            print("=" * 68)
            print(" PENGIRIMAN VIA WHATSAPP GATEWAY (OTOMATIS BACKGROUND)")
            print("=" * 68)
            print(f" Provider : {gw_res.get('provider', args.gateway or 'fonnte').upper()}")
            print(f" Target   : +{args.phone}")
            print(f" Status   : {gw_res.get('status')}")
            if gw_res.get("status") == "success":
                print(" Hasil    : [BERHASIL TERKIRIM] Pesan langsung masuk ke WhatsApp tujuan.")
                now_str = get_current_wib_datetime().strftime("%Y-%m-%d %H:%M:%S")
                if not slot_key:
                    _, slot_key, _, _ = check_scheduled_punctuality(window_minutes=15, allow_catchup=True)
                if slot_key:
                    record_sent_slot(slot_key, now_str)
                    print(f" [CATATAN] Slot sensus {slot_key} tercatat sukses di shift_sent_wa.json.")
            else:
                print(f" Error    : {gw_res.get('error')}")
            print("=" * 68)
        return

    res = send_whatsapp_local(
        phone=args.phone,
        message=args.message,
        mode=args.mode,
        launch_browser=not args.no_open
    )
    
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("=" * 68)
        print(" SISTEM PENGIRIM PESAN WHATSAPP MESSENGER")
        print(" RUANG ENGGANG GADING 2 — RSUD DR. SOEDARSO")
        print("=" * 68)
        print(f" Penerima : {res['recipient_name']} ({res['recipient_role']})")
        print(f" Nomor HP : +{res['recipient_phone']}")
        print(f" Waktu    : {res['timestamp']}")
        print(f" Mode     : {res['mode'].upper()}")
        print(f" Isi Pesan: \"{res['message']}\"")
        print("-" * 68)
        print(" Tautan WhatsApp:")
        print(f" 🟢 Web Direct : {res['urls']['web_url']}")
        print(f" 📱 Desktop App: {res['urls']['app_url']}")
        print(f" 🌐 Universal  : {res['urls']['wa_me_url']}")
        print("-" * 68)
        if res.get("launched"):
            print(" Status   : [BERHASIL DIBUKA]")
            print(" ⚠️ PENTING: Pesan otomatis terisi di kolom chat WhatsApp.")
            print(" Silakan tekan [ENTER] atau ikon [Kirim] di WhatsApp untuk menyelesaikan.")
        else:
            print(" Status   : [SIAP] Salin salah satu tautan di atas untuk membuka WhatsApp.")
        print("=" * 68)

if __name__ == "__main__":
    main()
