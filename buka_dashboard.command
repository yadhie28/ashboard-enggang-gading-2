#!/bin/bash
PROJECT_DIR="/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2"
cd "$PROJECT_DIR"

echo "================================================================"
echo "    MEMBUKA DASHBOARD RUANG ENGGANG GADING 2"
echo "    RSUD Dr. Soedarso Pontianak"
echo "================================================================"
echo "Lokasi Proyek : $DIR"

# Cek apakah server lokal sudah aktif di port 3000
if lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "✓ Server lokal terdeteksi aktif di port 3000."
else
    echo "Memulai server lokal Python di background..."
    python3 server.py &
    sleep 2
fi

# Buka peramban default ke localhost:3000
echo "Membuka browser ke http://localhost:3000..."
open "http://localhost:3000"

echo ""
echo "✓ Dashboard berhasil dibuka!"
echo "Tautan Cloud (bisa diakses dari HP / Laptop mana saja):"
echo "https://heroic-travesseiro-ef2369.netlify.app"
echo "================================================================"
