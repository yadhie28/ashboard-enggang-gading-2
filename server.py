#!/usr/bin/env python3
"""
Dashboard Server with Automated Shift Synchronization
Ruang Enggang Gading 2 (EG2A & EG2B) - RSUD Dr. Soedarso Pontianak

Features:
- Static file serving (HTML, CSS, JS, JSON)
- Automatic spreadsheet pull at 07:00, 14:00, and 21:00 (Shift handover times)
- Manual sync trigger via /api/sync
- Schedule & status endpoint via /api/sync-schedule
- Automatic zip package update to ~/Downloads/
"""

import http.server
import socketserver
import os
import json
import urllib.request
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
SYNC_INFO_FILE = os.path.join(DIRECTORY, "sync_info.json")

# Schedule times: 07:00, 14:00, 21:00
SCHEDULE_HOURS = [
    {"hour": 7, "minute": 0, "name": "Shift Pagi", "desc": "Operan Jaga Malam ➔ Pagi"},
    {"hour": 14, "minute": 0, "name": "Shift Sore", "desc": "Operan Jaga Pagi ➔ Sore"},
    {"hour": 21, "minute": 0, "name": "Shift Malam", "desc": "Operan Jaga Sore ➔ Malam"}
]

sync_lock = threading.Lock()
sync_state = {
    "is_syncing": False,
    "last_sync": None,
    "last_status": "idle",
    "last_message": "Server baru dimulai. Jadwal auto-sync aktif.",
    "sync_count": 0,
    "history": []
}

def load_sync_info():
    global sync_state
    if os.path.exists(SYNC_INFO_FILE):
        try:
            with open(SYNC_INFO_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                sync_state["last_sync"] = saved.get("last_sync")
                sync_state["last_status"] = saved.get("last_status", "success")
                sync_state["last_message"] = saved.get("last_message", "Tersinkronisasi")
                sync_state["sync_count"] = saved.get("sync_count", 0)
                sync_state["history"] = saved.get("history", [])[-20:]
        except Exception as e:
            print(f"[WARN] Failed to load sync_info.json: {e}")

def save_sync_info():
    try:
        with open(SYNC_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_sync": sync_state["last_sync"],
                "last_status": sync_state["last_status"],
                "last_message": sync_state["last_message"],
                "sync_count": sync_state["sync_count"],
                "history": sync_state["history"][-20:]
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Failed to save sync_info.json: {e}")

def get_next_scheduled_sync(now=None):
    if now is None:
        now = datetime.now()

    candidates = []
    for s in SCHEDULE_HOURS:
        t_today = now.replace(hour=s["hour"], minute=s["minute"], second=0, microsecond=0)
        if t_today > now:
            candidates.append((t_today, s))
        else:
            t_tomorrow = t_today + timedelta(days=1)
            candidates.append((t_tomorrow, s))

    candidates.sort(key=lambda x: x[0])
    next_dt, s_info = candidates[0]
    delta = next_dt - now
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    remaining_str = ""
    if hours > 0:
        remaining_str += f"{hours} jam "
    remaining_str += f"{minutes} menit"

    return {
        "datetime": next_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "time": f"{s_info['hour']:02d}:{s_info['minute']:02d}",
        "shiftName": s_info["name"],
        "shiftDesc": s_info["desc"],
        "remainingSeconds": total_seconds,
        "remainingFormatted": remaining_str.strip() or "sebentar lagi"
    }

NETLIFY_SITE_ID = "4fbdaa25-4820-4a43-9ded-2b87885e8859"
NETLIFY_TOKEN = "nfp_jReUwsNgDkXUNzN4n8is2vbtGeRwP9Teab01"

def download_spreadsheet(url, dest):
    """Download Google Sheets export using browser User-Agent to avoid HTTP 400."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        with open(dest, "wb") as f:
            f.write(resp.read())

def deploy_to_netlify():
    """Create a deployment zip and push directly to Netlify API."""
    try:
        zip_path = os.path.join(DIRECTORY, "deploy_netlify.zip")
        cmd = "echo '/* /index.html 200' > _redirects && zip -r deploy_netlify.zip index.html index.css app.js dashboard_data.json hospital_indicators.json _redirects"
        subprocess.run(cmd, shell=True, cwd=DIRECTORY, check=True, capture_output=True)

        url = f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {NETLIFY_TOKEN}",
                "Content-Type": "application/zip"
            },
            method="POST"
        )
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        with urllib.request.urlopen(req, data=zip_bytes, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "deployId": data.get("id"),
                "state": data.get("state"),
                "url": data.get("ssl_url") or "https://heroic-travesseiro-ef2369.netlify.app"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_sync(trigger_type="manual"):
    """Download Google Sheets, parse with fill colors, build data, update zip, and deploy to Netlify."""
    global sync_state
    if not sync_lock.acquire(blocking=False):
        return {
            "success": False,
            "error": "Sinkronisasi sedang berlangsung oleh proses lain.",
            "is_syncing": True
        }

    sync_state["is_syncing"] = True
    start_time = datetime.now()
    log_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n================================================================")
    print(f"[SYNC START] ({trigger_type.upper()}) at {log_time_str}")
    print(f"================================================================")

    try:
        url_a = "https://docs.google.com/spreadsheets/d/1RtJzfTnuTu-cmZXW59aGUDpihhJ1kGm_z9BozUHsgsI/export?format=xlsx"
        dest_a = os.path.join(DIRECTORY, "EG2A.xlsx")
        print(f"[SYNC] Mengunduh Spreadsheet EG 2A...")
        download_spreadsheet(url_a, dest_a)

        url_b = "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/export?format=xlsx"
        dest_b = os.path.join(DIRECTORY, "EG2B.xlsx")
        print(f"[SYNC] Mengunduh Spreadsheet EG 2B...")
        download_spreadsheet(url_b, dest_b)

        print(f"[SYNC] Menjalankan pemrosesan data (run_build_data.py)...")
        script_path = os.path.join(DIRECTORY, "run_build_data.py")
        cmd = [sys.executable, script_path]
        res = subprocess.run(cmd, cwd=DIRECTORY, capture_output=True, text=True, check=True)
        print(f"[SYNC] Build output:\n{res.stdout.strip()}")

        # Update ZIP package
        print(f"[SYNC] Memperbarui arsip ZIP dashboard-enggang-gading-2.zip...")
        zip_cmd = (
            "zip -r dashboard-enggang-gading-2.zip index.html index.css app.js "
            "dashboard_data.json hospital_indicators.json server.py share_link.sh auto_sync.sh "
            "&& cp dashboard-enggang-gading-2.zip ~/Downloads/dashboard-enggang-gading-2.zip"
        )
        subprocess.run(zip_cmd, shell=True, cwd=DIRECTORY, check=False)

        # Deploy directly to Netlify
        print(f"[SYNC] Mengunggah otomatis ke Netlify (https://heroic-travesseiro-ef2369.netlify.app)...")
        netlify_res = deploy_to_netlify()
        netlify_msg = ""
        if netlify_res.get("success"):
            print(f"[SYNC] Netlify Deploy Sukses! ID: {netlify_res.get('deployId')}")
            netlify_msg = " [Netlify Live 🚀]"
        else:
            print(f"[SYNC] Netlify Deploy Gagal: {netlify_res.get('error')}")
            netlify_msg = " [Netlify Warning]"

        end_time = datetime.now()
        duration_sec = round((end_time - start_time).total_seconds(), 1)
        finish_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S")

        sync_state["last_sync"] = finish_time_str
        sync_state["last_status"] = "success"
        sync_state["last_message"] = f"Sinkronisasi ({trigger_type}) berhasil dalam {duration_sec} detik{netlify_msg}"
        sync_state["sync_count"] += 1
        sync_state["history"].append({
            "timestamp": finish_time_str,
            "trigger": trigger_type,
            "status": "success",
            "duration": f"{duration_sec}s"
        })
        save_sync_info()

        print(f"[SYNC COMPLETE] Selesai sukses dalam {duration_sec} detik ({finish_time_str})")
        return {
            "success": True,
            "message": sync_state["last_message"],
            "timestamp": finish_time_str,
            "duration": f"{duration_sec}s",
            "trigger": trigger_type
        }
    except Exception as e:
        err_msg = str(e)
        print(f"[SYNC ERROR] Gagal sinkronisasi: {err_msg}")
        finish_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sync_state["last_sync"] = finish_time_str
        sync_state["last_status"] = "error"
        sync_state["last_message"] = f"Gagal: {err_msg}"
        sync_state["history"].append({
            "timestamp": finish_time_str,
            "trigger": trigger_type,
            "status": "error",
            "error": err_msg
        })
        save_sync_info()
        return {
            "success": False,
            "error": err_msg,
            "timestamp": finish_time_str
        }
    finally:
        sync_state["is_syncing"] = False
        sync_lock.release()

def auto_sync_scheduler_worker():
    """Background daemon thread checking schedule every 10 seconds."""
    print("[SCHEDULER] Auto-Sync Scheduler aktif untuk jam 07:00, 14:00, dan 21:00 WIB.")
    last_triggered_slot = None

    while True:
        try:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute

            for s in SCHEDULE_HOURS:
                if current_hour == s["hour"] and current_minute == s["minute"]:
                    slot_key = f"{now.strftime('%Y-%m-%d')}_{current_hour}:{current_minute}"
                    if last_triggered_slot != slot_key:
                        last_triggered_slot = slot_key
                        print(f"\n[SCHEDULER TRIGGER] Memulai Auto-Sync {s['name']} ({s['desc']}) pada {now.strftime('%H:%M:%S')}...")
                        threading.Thread(target=execute_sync, args=(f"auto_{s['name'].lower().replace(' ', '_')}",), daemon=True).start()
                    break

            time.sleep(10)
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
            time.sleep(15)

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            next_info = get_next_scheduled_sync()
            status = {
                "status": "online",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "directory": DIRECTORY,
                "autoSync": True,
                "schedules": ["07:00", "14:00", "21:00"],
                "lastSync": sync_state["last_sync"],
                "nextSync": next_info["datetime"],
                "nextShift": next_info["shiftName"]
            }
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        elif self.path == "/api/sync-schedule":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            next_info = get_next_scheduled_sync()
            payload = {
                "autoSyncEnabled": True,
                "schedules": [
                    {"time": "07:00", "name": "Shift Pagi", "desc": "Operan Jaga Malam ➔ Pagi"},
                    {"time": "14:00", "name": "Shift Sore", "desc": "Operan Jaga Pagi ➔ Sore"},
                    {"time": "21:00", "name": "Shift Malam", "desc": "Operan Jaga Sore ➔ Malam"}
                ],
                "currentTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "isSyncing": sync_state["is_syncing"],
                "lastSync": sync_state["last_sync"],
                "lastStatus": sync_state["last_status"],
                "lastMessage": sync_state["last_message"],
                "syncCount": sync_state["sync_count"],
                "nextSync": next_info,
                "history": sync_state["history"][-5:]
            }
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/data":
            json_path = os.path.join(DIRECTORY, "dashboard_data.json")
            if os.path.exists(json_path):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(json_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        elif self.path == "/api/whatsapp/info":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            info = {
                "recipient": {
                    "name": "Ns. Rusmulyadi, S.Kep.,M.A.R.S",
                    "role": "Kepala Ruang Enggang Gading 2",
                    "hospital": "RSUD Dr. Soedarso Pontianak",
                    "phone": "6281284070082",
                    "phoneFormatted": "+62 812-8407-0082"
                },
                "defaultMessage": "Test Boss",
                "defaultUrl": "https://wa.me/6281284070082?text=Test%20Boss",
                "status": "ready"
            }
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/sync":
            print("[API] Menerima permintaan sinkronisasi manual dari dashboard web...")
            res = execute_sync(trigger_type="manual_web")
            status_code = 200 if res.get("success") else 500
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path == "/api/whatsapp/send":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
                data = json.loads(body) if body else {}
                
                from send_whatsapp import send_whatsapp_local, DEFAULT_RECIPIENT, DEFAULT_MESSAGE
                phone = data.get("phone", DEFAULT_RECIPIENT["phone"])
                message = data.get("message", DEFAULT_MESSAGE)
                mode = data.get("mode", "web")
                open_client = data.get("open", True)
                res = send_whatsapp_local(phone=phone, message=message, mode=mode, launch_browser=open_client)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

def run():
    load_sync_info()
    # Start scheduler daemon
    scheduler_thread = threading.Thread(target=auto_sync_scheduler_worker, daemon=True)
    scheduler_thread.start()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"================================================================")
        print(f"  RUANG ENGGANG GADING 2 - DASHBOARD SENSUS & OPERAN JAGA")
        print(f"  RSUD Dr. Soedarso Pontianak")
        print(f"  Server berjalan di : http://localhost:{PORT}")
        print(f"  Jadwal Auto-Sync   : 07:00, 14:00, 21:00 WIB (Tiap Pergantian Shift)")
        next_sync = get_next_scheduled_sync()
        print(f"  Sinkron Berikutnya : {next_sync['datetime']} ({next_sync['shiftName']} - dalam {next_sync['remainingFormatted']})")
        print(f"================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    run()
