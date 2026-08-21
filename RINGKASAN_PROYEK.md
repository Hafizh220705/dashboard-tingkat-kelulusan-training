# Ringkasan Proyek — Dashboard Tingkat Kelulusan Training

## Gambaran Umum

Proyek ini adalah dashboard interaktif berbasis **Streamlit** untuk memantau performa dan tingkat kelulusan training karyawan PT United Tractors Tbk. Pengguna mengunggah data training dalam format Excel (`.xlsx`) atau CSV (`.csv`), kemudian aplikasi memvalidasi, membersihkan, memfilter, dan menyajikan data tersebut sebagai KPI serta visualisasi.

Status proyek saat ini masih berupa **skeleton awal/prototipe**. Beberapa aturan bisnis dan dokumentasi perlu dikonfirmasi serta diselaraskan sebelum dashboard dianggap final.

## Tujuan

- Memantau jumlah partisipasi training dan jumlah karyawan unik.
- Menghitung jumlah peserta lulus, tidak lulus, dan data tidak lengkap.
- Menampilkan pass rate dan fail rate.
- Membandingkan hasil training berdasarkan area, job, tahun, dan modul.
- Membantu menemukan modul dengan performa kelulusan terendah.
- Menyediakan filter interaktif agar analisis dapat difokuskan pada kelompok tertentu.

## Teknologi

| Teknologi | Kegunaan |
|---|---|
| Python | Bahasa utama aplikasi |
| Streamlit | Antarmuka dashboard web |
| Pandas | Pemrosesan dan agregasi data |
| Plotly | Visualisasi interaktif |
| OpenPyXL | Membaca berkas Excel |
| Pytest | Pengujian otomatis |

Dependensi lengkap tersedia pada `requirements.txt`.

## Alur Kerja Aplikasi

1. Pengguna mengunggah file Excel atau CSV melalui sidebar.
2. Aplikasi mendeteksi baris header, membersihkan nama kolom, dan memvalidasi kolom wajib.
3. Pipeline normalisasi membersihkan teks, mengubah tipe data, membentuk ID karyawan, menentukan status kelulusan, menangani data kosong, serta memfilter job aktif.
4. Pengguna memilih filter dan level agregasi KPI.
5. Dashboard menghitung KPI dari data yang telah difilter.
6. Hasil ditampilkan dalam kartu KPI dan tab visualisasi.

Alur singkat:

```text
Upload Excel/CSV
      ↓
Validasi dan pembersihan kolom
      ↓
Normalisasi dan penerapan aturan bisnis
      ↓
Filter interaktif
      ↓
KPI dan visualisasi
```

## Aturan Data Utama

Menurut implementasi pada `config/settings.py`, kolom wajib saat ini adalah:

- `NRP LAMA`
- `AREA`
- `JOB`
- `MODUL TRAINING`
- `TAHUN`
- `TEORI`
- `RESULT`

Kolom `NRP_ID` dibuat selama normalisasi. Nilainya menggunakan `NRP BARU` bila tersedia dan menggunakan `NRP LAMA` sebagai fallback.

Aturan kelulusan yang diterapkan kode saat ini:

- Nilai `TEORI >= 80` menjadi `LULUS`.
- Nilai `TEORI < 80` menjadi `TIDAK LULUS`.
- Nilai teori kosong atau tidak valid menjadi `DATA TIDAK LENGKAP`.

Hanya data dengan job yang tercantum dalam `JOB_FILTER_AKTIF` yang masuk ke visualisasi. Konfigurasi saat ini berisi `COP`, `PTO`, dan `ADM_SERVICE`.

## KPI dan Visualisasi

Dashboard mendukung dua level perhitungan:

- **Per partisipasi**: satu baris mewakili satu karyawan pada satu modul.
- **Per employee**: beberapa partisipasi digabung menjadi satu status per karyawan.

Informasi yang ditampilkan meliputi:

- Total partisipasi atau total employee.
- Jumlah lulus.
- Jumlah tidak lulus.
- Jumlah data tidak lengkap.
- Pass rate dan fail rate.
- Distribusi status berdasarkan area.
- Distribusi status berdasarkan job.
- Tren hasil training berdasarkan tahun.
- Ringkasan hasil berdasarkan modul training.
- Sorotan modul dengan performa terendah jika jumlah pesertanya memenuhi batas minimum.

Analisis masa kerja dan alasan kegagalan masih berstatus **pending** karena kolom sumbernya belum tersedia.

## Struktur Proyek

```text
app.py                         Entry point dan orkestrasi dashboard
config/settings.py             Konstanta, kolom, threshold, warna, dan filter job
src/data/loader.py             Pembacaan file dan validasi kolom
src/data/normalizer.py         Pipeline pembersihan dan normalisasi data
src/metrics/kpi.py             Agregasi dan perhitungan KPI
src/components/                Komponen UI, filter, KPI, dan visualisasi
src/utils/helpers.py           Fungsi format angka, persen, dan teks
tests/                         Unit test normalizer, KPI, dan filter
docs/                          Kamus data dan changelog
.streamlit/config.toml         Tema dan konfigurasi Streamlit
requirements.txt               Dependensi Python
```

## Menjalankan Proyek

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Dashboard dapat dibuka melalui `http://localhost:8501` setelah server berjalan.

## Menjalankan Pengujian

```powershell
pytest tests -v
```

Baseline pemeriksaan pada 15 Agustus 2026 menghasilkan **74 test lulus dan 22 test gagal**. Kelompok kegagalan utama meliputi:

- Perbedaan identifier default antara `NRP_ID` dan data test yang memakai `NRP BARU`.
- Perbedaan ekspektasi aturan `RESULT` dengan klasifikasi ulang berdasarkan `TEORI`.
- Parsing kolom tanggal `START` dan `END`.
- Penanganan nilai kosong setelah normalisasi teks.
- Metadata jumlah duplikat yang tidak lagi dikembalikan pipeline.
- Perbedaan konfigurasi job `COP` dengan ekspektasi test `CPO`.

## Catatan dan Risiko Saat Ini

- `README.md` dan `docs/data_dictionary.md` masih menjelaskan skema lama seperti `NAMA`, `JOB_TITLE`, `TAHUN_TRAINING`, dan `SCORE`, sedangkan kode menggunakan skema NRP, `JOB`, `TAHUN`, dan `TEORI`.
- Dokumentasi lama menyebut status berasal dari kolom `RESULT`, tetapi implementasi saat ini mengklasifikasikan ulang status dari nilai `TEORI`.
- Terdapat indikasi salah ketik antara job `COP` pada konfigurasi dan `CPO` pada pengujian.
- Sejumlah karakter emoji dan tanda baca di beberapa file tampil rusak akibat masalah encoding.
- Aturan agregasi status per employee dan aturan kelulusan perlu divalidasi bersama pemilik proses bisnis.
- Direktori proyek yang diperiksa belum terdeteksi sebagai repository Git.

## Rekomendasi Pengembangan

1. Tetapkan skema dataset resmi dan samakan kode, test, README, serta data dictionary.
2. Konfirmasi apakah status akhir harus mengikuti `RESULT` asli atau dihitung ulang dari `TEORI`.
3. Konfirmasi nama job yang benar: `COP` atau `CPO`.
4. Perbaiki test suite sampai seluruh pengujian kembali lulus.
5. Perbaiki encoding dokumentasi dan teks antarmuka menjadi UTF-8.
6. Lengkapi data masa kerja dan alasan kegagalan bila analisis pending ingin diaktifkan.
7. Tambahkan contoh dataset yang sesuai dengan skema produksi terbaru.

## Kesimpulan

Fondasi aplikasi sudah dipisahkan dengan cukup baik antara pemuatan data, normalisasi, perhitungan KPI, dan komponen tampilan. Dashboard telah memiliki alur utama yang jelas dan cakupan test yang cukup luas. Prioritas berikutnya adalah menyelaraskan aturan bisnis, konfigurasi, dokumentasi, dan pengujian agar hasil analisis konsisten serta siap digunakan sebagai dashboard produksi.
