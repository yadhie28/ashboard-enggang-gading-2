#!/bin/bash
cd "$(dirname "$0")"
echo "======================================================"
echo "    DASHBOARD ENGGANG GADING 2 - LOCAL SERVER"
echo "======================================================"
echo "Lokasi Folder : $(pwd)"
echo "Website Live  : https://heroic-travesseiro-ef2369.netlify.app"
echo "Jadwal Sync   : Otomatis jam 07.00, 14.00, 20.00 WIB"
echo "------------------------------------------------------"
echo "Tekan Ctrl + C untuk menghentikan server jika selesai."
echo "======================================================"
python3 server.py
