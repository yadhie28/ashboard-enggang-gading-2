#!/bin/bash
# Standalone Auto-Sync Script for Ruang Enggang Gading 2
# Designed for macOS Launchd, Terminal, or Cron execution

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

LOG_FILE="$DIR/auto_sync.log"

# Function for dual console & file logging
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

# Prevent concurrent execution between cron and launchd
LOCKFILE="/tmp/auto_sync_eg2.lock"
if [ -e "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then
    log "[INFO] Sinkronisasi lain sedang berjalan (PID $(cat "$LOCKFILE")). Keluar untuk mencegah konflik berkas."
    exit 0
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT INT TERM

echo "==================================================================" >> "$LOG_FILE"
log "=== [AUTO-SYNC START] Memulai Penarikan Spreadsheet Google Sheets ==="

# 1. Download EG2A with retry and safety check
log "Mengunduh Spreadsheet EG2A..."
curl -s -L --retry 3 --connect-timeout 20 "https://docs.google.com/spreadsheets/d/1RtJzfTnuTu-cmZXW59aGUDpihhJ1kGm_z9BozUHsgsI/export?format=xlsx" -o EG2A.xlsx.tmp
if [ -s EG2A.xlsx.tmp ] && [ $(wc -c < EG2A.xlsx.tmp) -gt 50000 ]; then
    mv EG2A.xlsx.tmp EG2A.xlsx
    log "EG2A berhasil diunduh ($(wc -c < EG2A.xlsx) bytes)."
else
    log "[WARN] Gagal mengunduh EG2A terbaru. Mempertahankan berkas lama."
    rm -f EG2A.xlsx.tmp
fi

# 2. Download EG2B with retry and safety check
log "Mengunduh Spreadsheet EG2B..."
curl -s -L --retry 3 --connect-timeout 20 "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/export?format=xlsx" -o EG2B.xlsx.tmp
if [ -s EG2B.xlsx.tmp ] && [ $(wc -c < EG2B.xlsx.tmp) -gt 50000 ]; then
    mv EG2B.xlsx.tmp EG2B.xlsx
    log "EG2B berhasil diunduh ($(wc -c < EG2B.xlsx) bytes)."
else
    log "[WARN] Gagal mengunduh EG2B terbaru. Mempertahankan berkas lama."
    rm -f EG2B.xlsx.tmp
fi

# 3. Run build script
log "Membangun ulang dataset sensus & deteksi warna kepulangan (run_build_data.py)..."
python3 run_build_data.py >> "$LOG_FILE" 2>&1
BUILD_STATUS=$?

if [ $BUILD_STATUS -ne 0 ]; then
    log "[ERROR] Pemrosesan run_build_data.py gagal dengan kode $BUILD_STATUS."
    exit 1
fi
log "Dataset dashboard_data.json & hospital_indicators.json berhasil diperbarui."

# 4. Update zip archive for offline distribution
log "Memperbarui arsip ZIP dashboard..."
zip -r dashboard-enggang-gading-2.zip index.html index.css app.js dashboard_data.json hospital_indicators.json server.py share_link.sh auto_sync.sh run_build_data.py update_full_pipeline.py generate_dashboard_data.py logo_kalbar.svg start_server.command _redirects sync_info.json logo_asset.js logo_kalbar.png logo_enggang.png >> "$LOG_FILE" 2>&1
if [ -d "$HOME/Downloads" ]; then
    cp dashboard-enggang-gading-2.zip "$HOME/Downloads/dashboard-enggang-gading-2.zip"
fi

# 5. Automatically deploy to Netlify
log "Mengunggah paket pembaruan ke Netlify..."
echo "/* /index.html 200" > _redirects
zip -r deploy_netlify.zip index.html index.css app.js dashboard_data.json hospital_indicators.json _redirects logo_kalbar.svg logo_asset.js logo_kalbar.png logo_enggang.png >> "$LOG_FILE" 2>&1

DEPLOY_RESP=$(curl -s -X POST \
  -H "Authorization: Bearer nfp_jReUwsNgDkXUNzN4n8is2vbtGeRwP9Teab01" \
  -H "Content-Type: application/zip" \
  --data-binary "@deploy_netlify.zip" \
  https://api.netlify.com/api/v1/sites/4fbdaa25-4820-4a43-9ded-2b87885e8859/deploys)

log "Netlify Deploy Response diterima."

# 6. Update sync_info.json
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
python3 -c "
import json, os
info = {
    'last_sync': '$CURRENT_TIME',
    'last_status': 'success',
    'last_message': 'Auto-Sync Berhasil (Jadwal Terjadwal)',
    'sync_count': 1
}
path = 'sync_info.json'
if os.path.exists(path):
    try:
        with open(path) as f:
            old = json.load(f)
            info['sync_count'] = old.get('sync_count', 0) + 1
    except:
        pass
with open(path, 'w') as f:
    json.dump(info, f, indent=2)
"

# 7. Push updated data to GitHub repository
log "Menyelaraskan data sensus ke repositori GitHub..."
git pull --rebase -X theirs origin main >> "$LOG_FILE" 2>&1 || true
git add dashboard_data.json hospital_indicators.json EG2A.xlsx EG2B.xlsx sync_info.json >> "$LOG_FILE" 2>&1
git commit -m "chore(sync): automated census sync $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE" 2>&1 || true
git push origin main >> "$LOG_FILE" 2>&1 || true

# 8. Send WhatsApp Census Report (Hanya pada jam tepat 07.00, 14.00, 20.00 WIB)
log "Mengirimkan laporan sensus WhatsApp otomatis ke Kepala Ruang (Strict On-Time)..."
python3 send_whatsapp.py --sensus --scheduled-only --gateway fonnte >> "$LOG_FILE" 2>&1 || true

# 9. Notify local server if running
curl -s http://localhost:3000/api/status > /dev/null 2>&1 || true

# 10. Send macOS Desktop Notification
osascript -e 'display notification "Data sensus berhasil ditarik, diperbarui & dikirim ke WhatsApp." with title "Auto-Sync Enggang Gading 2" subtitle "'"$CURRENT_TIME"'" sound name "Glass"' 2>/dev/null || true

log "=== [AUTO-SYNC COMPLETED] Selesai pada $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "==================================================================" >> "$LOG_FILE"
