#!/bin/bash
# Standalone Auto-Sync Script for Ruang Enggang Gading 2
# Can be run manually or invoked by crontab / launchd
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=================================================================="
echo " [AUTO-SYNC] Menjalankan Penarikan Spreadsheet Google Sheets..."
echo " Tanggal & Jam: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================================="

# 1. Download EG2A
echo "Downloading EG2A..."
curl -s -L "https://docs.google.com/spreadsheets/d/1RtJzfTnuTu-cmZXW59aGUDpihhJ1kGm_z9BozUHsgsI/export?format=xlsx" -o EG2A.xlsx

# 2. Download EG2B
echo "Downloading EG2B..."
curl -s -L "https://docs.google.com/spreadsheets/d/1lpmrLiILZtFX-sBVyzBjlqf3xRgcYJ84Yrzj8fZ8Lx0/export?format=xlsx" -o EG2B.xlsx

# 3. Run build script
echo "Rebuilding dashboard dataset..."
python3 run_build_data.py

# 4. Update zip archive
echo "Updating zip package..."
zip -r dashboard-enggang-gading-2.zip index.html index.css app.js dashboard_data.json hospital_indicators.json server.py share_link.sh auto_sync.sh
cp dashboard-enggang-gading-2.zip ~/Downloads/dashboard-enggang-gading-2.zip

# 5. Automatically deploy to Netlify (https://heroic-travesseiro-ef2369.netlify.app)
echo "Deploying update to Netlify (heroic-travesseiro-ef2369.netlify.app)..."
echo "/* /index.html 200" > _redirects
zip -r deploy_netlify.zip index.html index.css app.js dashboard_data.json hospital_indicators.json _redirects > /dev/null
curl -s -X POST \
  -H "Authorization: Bearer nfp_jReUwsNgDkXUNzN4n8is2vbtGeRwP9Teab01" \
  -H "Content-Type: application/zip" \
  --data-binary "@deploy_netlify.zip" \
  https://api.netlify.com/api/v1/sites/4fbdaa25-4820-4a43-9ded-2b87885e8859/deploys > /dev/null
echo "Deployed to Netlify successfully!"

# 6. Notify local server if running
curl -s http://localhost:3000/api/status > /dev/null 2>&1

echo "=================================================================="
echo " [AUTO-SYNC] Sinkronisasi & Deploy Netlify Selesai: $(date '+%Y-%m-%d %H:%M:%S')"
echo " URL: https://heroic-travesseiro-ef2369.netlify.app/"
echo "=================================================================="
