# Dashboard Ruang Enggang Gading 2
**RSUD Dr. Soedarso Pontianak — Instalasi Rawat Inap (EG 2A & EG 2B)**

Dashboard pemantauan sensus pasien rawat inap, denah keterisian bed real-time, statistik indikator rumah sakit (BOR, LOS, BTO, TOI, NDR, GDR), visualisasi Top 10 DPJP / Spesialis, Top 10 Diagnosa Medis, serta fitur pembuatan & ekspor **Kronologis Perjalanan Rawat Inap Pasien** ke format Cetak dan Microsoft Word (.doc).

---

## 🌐 Akses Online 24/7
- **Tautan Live**: [https://heroic-travesseiro-ef2369.netlify.app](https://heroic-travesseiro-ef2369.netlify.app)
- Dapat diakses dari HP, tablet, laptop, dan komputer ruangan tanpa instalasi aplikasi.

---

## 💻 Cara Menjalankan di Komputer Lokal (Mac)

### Cara 1 (Paling Mudah — 1 Klik):
1. Buka folder **Desktop** di Mac Anda.
2. Klik ganda (*double click*) file **`Buka_Dashboard_Enggang_Gading.command`**.
3. Dashboard akan langsung terbuka di browser Anda pada alamat `http://localhost:3000`.

### Cara 2 (Lewat Terminal):
```bash
cd /Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2
python3 server.py
```
Lalu buka browser di `http://localhost:3000`.

---

## 🔄 Sinkronisasi Data Otomatis (Google Sheets)
Sistem dilengkapi skrip penarikan data berkala (`auto_sync.sh`) yang berjalan otomatis setiap pergantian shift jaga:
- **Shift Pagi**: 07.00 WIB
- **Shift Sore**: 14.00 WIB
- **Shift Malam**: 21.00 WIB

Untuk menjalankan sinkronisasi data secara manual sewaktu-waktu:
```bash
./auto_sync.sh
```

---

## 📁 Lokasi Penyimpanan & Cadangan File

| Komponen | Lokasi File |
| :--- | :--- |
| **Folder Kerja Utama** | `/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2/` |
| **Pintasan di Dokumen** | `~/Documents/dashboard-enggang-gading-2` |
| **Peluncur Cepat Desktop** | `~/Desktop/Buka_Dashboard_Enggang_Gading.command` |
| **File Cadangan ZIP** | `~/Downloads/dashboard-enggang-gading-2.zip` dan `~/Documents/dashboard-enggang-gading-2.zip` |
| **Riwayat Versi (Git)** | Tersimpan lengkap di repositori lokal `.git` |

---

## ✨ Fitur Utama
1. **Sensus Harian & Denah Bed Dinamis**: Visualisasi status bed EG 2A & EG 2B (Terisi, Kosong, Isolasi, Keluar/Pindah).
2. **Indikator Efisiensi Rawat Inap**: Grafik & metrik standar Depkes (BOR, ALOS, TOI, BTO, NDR, GDR).
3. **Analitik Data**: Diagram interaktif Top 10 DPJP, Top 10 Diagnosa Medis (ICD-10), dan Asuransi/Jaminan.
4. **Riwayat Kronologis Rawat Inap Pasien**:
   - Filter tanggal & pencarian nama/rekam medis pasien.
   - Deteksi otomatis CPPT/SBAR per shift.
   - Ekspor format **Microsoft Word (.doc)** dengan kop standar Pemprov Kalbar & RSUD Dr. Soedarso.
   - Format Cetak Resmi ber-kop dengan penandatangan Kepala Ruang Enggang Gading 2.
5. **Logo Resmi**: Menampilkan logo khas Kalimantan Barat — **Burung Enggang Gading** (*Helmeted Hornbill / Rhinoplax vigil*).
