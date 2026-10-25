# Dashboard Ruang Enggang Gading 2
**RSUD Dr. Soedarso Pontianak — Instalasi Rawat Inap (EG 2A & EG 2B)**

Sistem Informasi Manajemen Sensus Pasien Rawat Inap, Denah Keterisian Bed Dinamis (56 Bed), Surveilans Triase Fisiologis **EWS/NEWS2**, Interoperabilitas Standar **HL7 FHIR Release 4 (SatuSehat Ready)**, Indikator Efisiensi Mutu RS (BOR, AVLOS, TOI, BTO, NDR, GDR), Grafik Barber-Johnson Interaktif, serta Otomatisasi Pengiriman Laporan Sensus via WhatsApp.

---

## 🚀 3 Cara Membuka Dashboard Sewaktu-Waktu

### 🌐 1. Buka Online Langsung (Tanpa Komputer / dari Smartphone & Laptop Mana Saja)
- **Tautan Live GitHub Pages (Utama)**:  
  👉 **[https://yadhie28.github.io/ashboard-enggang-gading-2/](https://yadhie28.github.io/ashboard-enggang-gading-2/)**
- **Repositori GitHub**:  
  👉 **[https://github.com/yadhie28/ashboard-enggang-gading-2](https://github.com/yadhie28/ashboard-enggang-gading-2)**

*(Data sensus dan perburukan pasien di tautan ini selalu tersinkronisasi otomatis setiap pergantian shift).*

---

### 🖱️ 2. Klik Ganda (Double-Click) dari Desktop Mac
1. Temukan berkas **`Buka_Dashboard_Enggang_Gading_2.command`** di **Desktop** Mac Anda.
2. Klik ganda berkas tersebut.
3. Server lokal Python akan otomatis aktif dan peramban (browser) langsung terbuka di `http://localhost:3000`.

---

### 💻 3. Buka di Antigravity IDE / VS Code
Buka menu **File > Open Folder...** lalu arahkan ke direktori:
```bash
/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2
```
Atur folder ini sebagai **Active Workspace**. Anda dapat langsung mengedit kode, menguji fitur, atau menjalankan terminal.

---

## 📁 Lokasi Penyimpanan Proyek & Arsip Cadangan (Backup)

| Tipe Penyimpanan | Lokasi / Tautan | Keterangan |
| :--- | :--- | :--- |
| **Direktori Kerja Utama** | `/Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2/` | Folder aktif kode sumber & data |
| **Peluncur Desktop** | `/Users/rusmulyadiiskandar/Desktop/Buka_Dashboard_Enggang_Gading_2.command` | Pintasan 1-klik buka dashboard |
| **Cadangan Offline ZIP** | `~/Desktop/dashboard-enggang-gading-2-backup.zip` | Salinan arsip kompresi lengkap |
| **Cadangan Tambahan** | `~/Downloads/dashboard-enggang-gading-2.zip` | Salinan arsip di folder Unduhan |
| **Cloud Repository** | `git@github.com:yadhie28/ashboard-enggang-gading-2.git` | Branch `main` tersinkronisasi penuh |

---

## 🏥 Fitur Utama & Standar Enterprise

1. **Surveilans Triase Klinis EWS / NEWS2 Real-Time**:
   - Algoritma standar *Royal College of Physicians (UK)* menghitung skor dini 7 parameter fisiologis: Laju Napas (RR), SpO2, Terapi O2, Tensi Sistolik, Nadi, AVPU, dan Suhu Tubuh.
   - Badge visual EWS pada setiap kartu bed dan papan operan jaga shift harian.
   - Filter cepat 1-klik untuk pasien risiko kritis (Skor ≥ 7) dan risiko sedang (Skor 5-6).
2. **Suite Interoperabilitas HL7 FHIR Release 4 (SatuSehat Ready)**:
   - Pembangun sumber daya FHIR R4: `Patient`, `Encounter` (Rawat Inap), `Condition` (Diagnosa), `Observation` (NEWS2 & 6 parameter vital LOINC), `Observation` (Morse Fall Risk & Braden Decubitus).
   - Ekspor 1-Klik Bundle sensus 56 bed untuk seluruh bangsal.
   - Peninjau interaktif JSON FHIR dengan fitur salin cepat ke clipboard.
3. **Papan Operan Jaga Shift Harian (SBAR Handover)**:
   - Pembagian shift Pagi (07:00-14:00), Sore (14:00-20:00), dan Malam (20:00-07:00).
   - Pintasan keyboard **`Alt+S`** untuk menyalin format SBAR yang sudah menyertakan skor EWS dan telemetri tanda vital.
4. **Command Palette (`⌘K` / `Ctrl+K`)**:
   - Navigasi sub-detik untuk mencari pasien berdasarkan Nama, No. RM, atau Bed tanpa scroll manual.

---

## ⏰ Jadwal Otomatisasi (Sensus & WhatsApp 07.00, 14.00, 20.00 WIB)

Sistem memiliki daemon lokal (`launchd`) dan *GitHub Actions* yang aktif tepat waktu:
- **Shift Pagi**: Pukul **07.00 WIB**
- **Shift Sore**: Pukul **14.00 WIB**
- **Shift Malam**: Pukul **20.00 WIB**

**Alur Eksekusi Otomatis:**
1. Tarik spreadsheet `EG 2A` dan `EG 2B` terbaru dari Google Sheets.
2. Hitung sensus pasien aktif vs pulang (deteksi sel warna pink).
3. Buat perbandingan mutasi dengan shift sebelumnya (*px awal, baru, pulang, meninggal, pindah, sekarang, BOR, bed sisa*).
4. Kirim laporan sensus terformat rapi ke WhatsApp Kepala Ruangan:
   - **Penerima**: Ns. Rusmulyadi, S.Kep.,M.A.R.S (`+6281284070082`)
5. Deploy otomatis pembaruan ke GitHub Pages.

---

## 🛠️ Perintah Berguna di Terminal

### Menjalankan Server Lokal Secara Manual:
```bash
cd /Users/rusmulyadiiskandar/.gemini/antigravity-ide/scratch/dashboard-enggang-gading-2
python3 server.py
```
Akses di browser: `http://localhost:3000`

### Tarik Data & Sinkronisasi Manual:
```bash
python3 run_build_data.py
```

### Eksekusi Tarik Data & Kirim Laporan WhatsApp Manual:
```bash
python3 send_whatsapp.py --force
```

---
*Dikembangkan dengan dedikasi untuk efisiensi operasional keperawatan dan keselamatan pasien (Patient Safety) Ruang Enggang Gading 2 RSUD Dr. Soedarso Pontianak.*
