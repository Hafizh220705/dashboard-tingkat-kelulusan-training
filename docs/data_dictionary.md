# data_dictionary.md — Penjelasan kolom dataset & asumsi/rule

## Kolom Dataset

| Kolom | Tipe | Deskripsi | Contoh Nilai |
|---|---|---|---|
| `NAMA` | string | Nama lengkap peserta training | `Budi Santoso` |
| `AREA` | string | Lokasi/area kerja peserta | `Jakarta`, `Surabaya` |
| `JOB_TITLE` | string | Jabatan / posisi peserta | `Operator`, `Supervisor` |
| `MODUL_TRAINING` | string | Nama modul yang diikuti | `K3 Dasar`, `SOP Produksi` |
| `TAHUN_TRAINING` | integer | Tahun pelaksanaan training | `2023`, `2024` |
| `SCORE` | float | Nilai ujian peserta (0–100) | `78.5` |
| `RESULT` | string | Hasil evaluasi dari sumber data asli | `PASS`, `FAIL`, `LULUS`, `TIDAK LULUS` |
| `RESULT_FINAL` *(generated)* | string | Kolom biner hasil normalisasi | `PASS` atau `FAIL` |

---

## Asumsi & Rules Normalisasi

1. **Nama kolom**: Seluruh nama kolom diubah ke `UPPER_CASE` + strip spasi.
2. **Teks**: Nilai pada kolom teks (`NAMA`, `AREA`, `JOB_TITLE`, dll.) di-strip whitespace dan di-upper-case.
3. **RESULT_FINAL**:
   - Jika kolom `RESULT` ada → nilai `PASS`, `LULUS`, `PASSED`, `YA`, `YES`, `1` diklasifikasikan sebagai `PASS`; lainnya `FAIL`.
   - Jika kolom `RESULT` tidak ada → fallback ke `SCORE >= 70` (lihat `config/settings.py → PASSING_SCORE`).
4. **Deduplikasi**: Baris dengan kombinasi `NAMA + MODUL_TRAINING + TAHUN_TRAINING` yang sama akan dihapus, dipertahankan baris terakhir.
5. **SCORE**: Dikonversi ke numerik; nilai tidak valid → `NaN`.
6. **TAHUN_TRAINING**: Dikonversi ke integer nullable (`Int64`).

---

## Kolom Pending (belum ada di dataset)

| Kolom | Keterangan |
|---|---|
| `MASA_KERJA` | Lama masa kerja peserta (dalam bulan/tahun) |
| `REASON_FAIL` | Alasan/catatan mengapa peserta tidak lulus |
