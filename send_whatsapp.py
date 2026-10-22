#!/usr/bin/env python3
"""
Sistem Pengirim Pesan WhatsApp Messenger
Tujuan: Kepala Ruang Enggang Gading 2 (Ns. Rusmulyadi, S.Kep.,M.A.R.S)
Nomor : +6281284070082
Isi    : 'Test Boss' (atau pesan dinamis lainnya)
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
    "phone": "6281284070082"  # Format nomor internasional WhatsApp tanpa '+' atau '08'
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

def generate_whatsapp_url(phone: str = None, message: str = None, use_api_domain: bool = False) -> str:
    """Membuat tautan universal WhatsApp Web / Messenger."""
    target_phone = normalize_phone_number(phone or DEFAULT_RECIPIENT["phone"])
    target_message = message if message is not None else DEFAULT_MESSAGE
    encoded_text = urllib.parse.quote(target_message)
    
    if use_api_domain:
        return f"https://api.whatsapp.com/send?phone={target_phone}&text={encoded_text}"
    return f"https://wa.me/{target_phone}?text={encoded_text}"

def send_whatsapp_local(phone: str = None, message: str = None, launch_browser: bool = True) -> dict:
    """
    Mengirim pesan WhatsApp via WhatsApp Messenger (Web / App).
    Membuka tautan resmi wa.me / api.whatsapp.com di browser default atau aplikasi WhatsApp Desktop.
    """
    target_phone = normalize_phone_number(phone or DEFAULT_RECIPIENT["phone"])
    target_msg = message if message is not None else DEFAULT_MESSAGE
    
    wa_url = generate_whatsapp_url(target_phone, target_msg)
    api_url = generate_whatsapp_url(target_phone, target_msg, use_api_domain=True)
    
    result = {
        "status": "success",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "recipient_name": DEFAULT_RECIPIENT["name"],
        "recipient_role": DEFAULT_RECIPIENT["role"],
        "recipient_phone": target_phone,
        "message": target_msg,
        "wa_url": wa_url,
        "api_url": api_url,
        "launched": False
    }

    if launch_browser:
        try:
            # Di macOS, gunakan perintah 'open' untuk memicu browser / WhatsApp desktop
            if sys.platform == "darwin":
                subprocess.run(["open", wa_url], check=True)
            else:
                webbrowser.open(wa_url)
            result["launched"] = True
            result["launch_method"] = "system_browser"
        except Exception as e:
            result["launched"] = False
            result["launch_error"] = str(e)
            # Fallback ke webbrowser standard library
            try:
                webbrowser.open(wa_url)
                result["launched"] = True
                result["launch_method"] = "webbrowser_fallback"
            except Exception as e2:
                result["fallback_error"] = str(e2)

    return result

def send_via_gateway(phone: str, message: str, gateway_config: dict = None) -> dict:
    """
    Mengirim pesan melalui Gateway API pihak ketiga (Fonnte, Wablas, Twilio, dll.)
    jika konfigurasi gateway disediakan.
    """
    import urllib.request
    
    config = gateway_config or {}
    api_url = config.get("api_url")
    token = config.get("token")
    
    if not api_url or not token:
        return {
            "status": "skipped",
            "message": "Gateway API belum dikonfigurasi. Menggunakan tautan langsung wa.me."
        }
        
    try:
        data = json.dumps({"target": phone, "message": message}).encode('utf-8')
        req = urllib.request.Request(
            api_url, 
            data=data, 
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            return {"status": "success", "response": json.loads(res_body)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Kirim Pesan WhatsApp ke Kepala Ruang Enggang Gading 2")
    parser.add_argument("-m", "--message", default=DEFAULT_MESSAGE, help="Isi pesan (default: 'Test Boss')")
    parser.add_argument("-p", "--phone", default=DEFAULT_RECIPIENT["phone"], help="Nomor tujuan (default: 6281284070082)")
    parser.add_argument("--no-open", action="store_true", help="Hanya tampilkan link tanpa membuka browser/aplikasi")
    parser.add_argument("--json", action="store_true", help="Output format JSON")
    
    args = parser.parse_args()
    
    res = send_whatsapp_local(
        phone=args.phone,
        message=args.message,
        launch_browser=not args.no_open
    )
    
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("=" * 65)
        print(" SISTEM PENGIRIM PESAN WHATSAPP MESSENGER")
        print(" RUANG ENGGANG GADING 2 — RSUD DR. SOEDARSO")
        print("=" * 65)
        print(f" Penerima : {res['recipient_name']} ({res['recipient_role']})")
        print(f" Nomor HP : +{res['recipient_phone']}")
        print(f" Waktu    : {res['timestamp']}")
        print(f" Isi Pesan: \"{res['message']}\"")
        print("-" * 65)
        print(f" Tautan WhatsApp:")
        print(f" -> {res['wa_url']}")
        print(f" -> {res['api_url']}")
        if res.get("launched"):
            print(" Status   : [BERHASIL] Tautan WhatsApp Messenger telah dibuka ke browser/aplikasi!")
        else:
            print(" Status   : [SIAP] Salin tautan di atas untuk membuka WhatsApp langsung.")
        print("=" * 65)

if __name__ == "__main__":
    main()
