# Dashboard Ruang Enggang Gading 2
**RSUD Dr. Soedarso Pontianak — Instalasi Rawat Inap (EG 2A & EG 2B)**

Dashboard pemantauan sensus pasien rawat inap real-time, denah keterisian bed dinamis, indikator efisiensi mutu pelayanan rumah sakit (BOR, AVLOS, BTO, TOI, NDR, GDR), Grafik Barber-Johnson interaktif, visualisasi Top DPJP & Diagnosa, serta otomatisasi pengiriman laporan sensus via WhatsApp Gateway.

---

## 🚀 Cara Cepat Membuka Dashboard Sewaktu-waktu

### 🖱️ Opsi 1: Klik Ganda (Double-Click) dari Desktop Mac
1. Temukan ikon file **`Buka_Dashboard_Enggang_Gading_2.command`** di **Desktop** Mac Anda (atau di dalam folder proyek).
2. Klik ganda berkas tersebut.
3. Server lokal akan aktif dan peramban (browser) otomatis terbuka menampilkan dashboard di `http://localhost:3000`.

### 🌐 Opsi 2: Buka Online Langsung (Tanpa Komputer / dari Smartphone & HP Mana Saja)
- **Tautan Live Netlify**: [https://heroic-travesseiro-ef2369.netlify.app](https://heroic-travesseiro-ef2369.netlify.app)
- **Repositori GitHub**: [https://github.com/yadhie28/ashboard-enggang-gading-2.git](https://github.com/yadhie28/ashboard-enggang-gading-2.git)

### 💻 Opsi 3: Buka di Antigravity IDE / VS Code
Buka menu **File > Open Folder...** lalu pilih direktori:
`/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2`
Atur folder ini sebagai **Active Workspace**.

---

## 📁 Lokasi Proyek & Direktori Kerja
- **Path Proyek Utama**: `/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2/`
- **Cadangan ZIP Terbaru**: 
  - `~/Downloads/dashboard-enggang-gading-2.zip`
  - `~/Documents/dashboard-enggang-gading-2.zip`
- **Cadangan GitHub**: Sinkron otomatis dengan remote branch `main`

---

## ⏰ Jadwal Otomatisasi (Sensus & Laporan WhatsApp)
Sistem memiliki pipeline ganda (*Cloud via GitHub Actions* dan *Lokal via launchd/cron*) yang aktif secara otomatis pada:
- **Pagi**: **07.00 WIB** (00:00 UTC)
- **Siang**: **14.00 WIB** (07:00 UTC)
- **Malam**: **21.00 WIB** (14:00 UTC)

### Alur Kerja Otomatis:
1. Menarik data mutasi terbaru dari Google Sheets (`EG 2A` & `EG 2B`).
2. Menghitung sensus dengan deteksi warna sel (*Pink/FFE6B8AF* = Pasien Pulang, *Uncolored* = Pasien Aktif).
3. Memperbarui `dashboard_data.json` & `hospital_indicators.json`.
4. Mengirimkan pesan laporan sensus berformat khusus (bold, list, emoji) ke WhatsApp Kepala Ruangan:
   - **Penerima**: Ns. Rusmulyadi, S.Kep.,M.A.R.S (`+6281284070082`)
   - **Gateway**: Fonnte API (`wa_gateway_config.json`)
5. Melakukan push pembaruan data ke GitHub Pages/Netlify secara otomatis.

---

## 🛠️ Perintah Berguna untuk Pembaruan & Pemeliharaan

### 1. Menjalankan Server Dashboard Lokal
```bash
cd /Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2
python3 server.py
```
Lalu buka browser di `http://localhost:3000`.

### 2. Tarik Data & Perbarui Sensus Manual
```bash
python3 run_build_data.py
```

### 3. Kirim Ulang Laporan Sensus WhatsApp Manual
```bash
python3 -c "import server; server.send_wa_census_report()"
```

### 4. Sinkronisasi Penuh Manual (Tarik Data + Kirim WA + Push ke GitHub)
```bash
./auto_sync.sh
```

---

## 📊 Ringkasan Kapasitas & Metrik Ruang EG 2
- **Kapasitas Total**: **56 Bed**
  - **EG2-A**: 16 Bed (12 Standar + 4 Ekstra Bed)
  - **EG2-B**: 40 Bed (36 Standar + 4 Ekstra Bed)
- **Formula BOR Real-Time**:
  $$\text{BOR Sekarang} = \frac{\text{Pasien Aktif}}{\text{Kapasitas Bed (56)}} \times 100\%$$
- **Diagram Responsif**:
  - Tampilan Android / Mobile: Disesuaikan optimal 320px lebar layar.
  - Tampilan Desktop / Monitor: Skala otomatis membesar hingga 460px – 480px.
