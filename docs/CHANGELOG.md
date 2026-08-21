# CHANGELOG

Semua perubahan signifikan pada proyek ini akan didokumentasikan di file ini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Alat konversi satu atau banyak CSV menjadi Excel `.xlsx` yang mendeteksi delimiter
  dan encoding umum; hasil batch dikemas sebagai ZIP.
- Alat penggabungan beberapa file Excel berdasarkan nama kolom, termasuk opsi kolom sumber.
- Validasi template laporan training, klasifikasi kelulusan dari `Grade/100.00`,
  dan pencocokan hasil training ke master employee melalui NRP.
- Section upload terpisah untuk master employee dan nilai training, beserta
  dashboard KPI, visualisasi, dan tabel detail status kelulusan karyawan.
- Agregasi maksimal tiga percobaan per NRP menggunakan nilai terbaik, termasuk
  visualisasi percobaan saat lulus dan audit seluruh percobaan.
- Fallback nilai pertanyaan 1–5 dari skala `/10.00` ke `/20.00`, beserta
  normalisasi persentase untuk perbandingan lintas skala.
- Dashboard terintegrasi menampilkan visualisasi master employee dan hasil
  training pada halaman yang sama; hasil merge diteruskan otomatis ke dashboard.
- Filter hasil training diperluas untuk job, modul, status kelulusan, dan seluruh
  atribut master employee yang tersedia, dengan reset state menyeluruh.
- Satu state filter kini dipropagasikan ke visual profil peserta dan seluruh
  visual hasil training agar semua komponen berubah secara konsisten.
- Struktur folder modular: `src/data`, `src/metrics`, `src/components`, `src/utils`
- `config/settings.py` — konstanta global (kolom wajib, threshold, warna)
- `src/data/loader.py` — baca Excel/CSV + validasi kolom
- `src/data/normalizer.py` — pipeline normalisasi 5 tahap
- `src/metrics/kpi.py` — fungsi hitung KPI utama
- Komponen Streamlit: sidebar filter, KPI cards, chart area/job/tahun/modul, pending section
- Unit test: `tests/test_normalizer.py`, `tests/test_kpi.py`
- Dummy data generator: `scripts/generate_dummy_data.py`
- Dokumentasi: `docs/data_dictionary.md`, `docs/CHANGELOG.md`
- `.streamlit/config.toml` — konfigurasi tema dark
- `requirements.txt`, `.gitignore`, `README.md`

---

## [Template]

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security
