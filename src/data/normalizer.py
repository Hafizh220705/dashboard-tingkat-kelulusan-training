"""
Modul untuk membersihkan & menormalisasi data training mentah.
Tanggung jawab modul ini: transformasi isi data (bukan I/O — itu
tanggung jawab `src/data/loader.py`).

Modul ini SENGAJA tidak bergantung pada Streamlit sama sekali, supaya
bisa di-unit-test secara terpisah dan reusable di luar konteks dashboard.
"""

import numpy as np
import pandas as pd

from config.settings import (
    JOB_FILTER_AKTIF,
    KOLOM_KATEGORI,
    KOLOM_KUNCI_DUPLIKAT,
    KOLOM_NUMERIK,
    KOLOM_TANGGAL,
    MAPPING_BULAN_INDONESIA,
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
    THRESHOLD_KELULUSAN,
)


def normalisasi_teks(df: pd.DataFrame, kolom_list: list = None) -> pd.DataFrame:
    """
    Standarisasi teks kolom kategorikal: trim whitespace, uppercase,
    dan hilangkan spasi ganda di tengah teks.

    Blank/NaN asli TETAP dipertahankan sebagai NaN (tidak berubah jadi
    string "NAN") supaya bisa ditangani terpisah oleh
    `normalisasi_kategori_kosong()`.

    Catatan: `.str.strip()` hanya menghapus ASCII whitespace. Non-breaking
    space (\xa0) dan karakter whitespace Unicode lain bisa lolos. Karena itu
    dilakukan strip KEDUA setelah `.str.replace(r"\s+", " ")` yang jangkauannya
    lebih luas (regex \s di Python mencakup Unicode whitespace), supaya
    karakter seperti \xa0 di ujung string tidak menyebabkan dua nilai yang
    tampak sama tapi sebenarnya berbeda.
    """
    df = df.copy()
    kolom_list = kolom_list or KOLOM_KATEGORI

    for kolom in kolom_list:
        if kolom not in df.columns:
            continue
        df[kolom] = (
            df[kolom]
            .astype(str)
            .str.strip()                            # strip ASCII whitespace dulu
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)  # collapse semua whitespace Unicode
            .str.strip()                            # strip lagi setelah replace (untuk \xa0 di ujung)
            .replace("NAN", np.nan)
        )
    return df


def parse_tanggal_indonesia(series: pd.Series) -> pd.Series:
    """
    Parse kolom tanggal berformat "DD NamaBulanIndonesia YYYY"
    (contoh: "04 Juli 2019") menjadi datetime.

    pd.to_datetime() bawaan TIDAK bisa memahami nama bulan Indonesia
    ("Juli") -- kalau dipaksa dengan errors="coerce", hasilnya diam-diam
    jadi NaT tanpa ada tanda error yang jelas ke user. Fungsi ini
    menerjemahkan nama bulan Indonesia ke Inggris dulu sebelum parsing.

    Kalau ada baris yang tetap gagal diparse setelah translasi
    (misal format tanggalnya beda sama sekali), tetap dikembalikan
    sebagai NaT -- tapi jumlahnya divalidasi di
    `normalisasi_tipe_data()` supaya tidak lolos diam-diam.
    """
    series_teks = series.astype(str)

    for bulan_indo, bulan_eng in MAPPING_BULAN_INDONESIA.items():
        series_teks = series_teks.str.replace(bulan_indo, bulan_eng, regex=False)

    return pd.to_datetime(series_teks, errors="coerce")

def normalisasi_tipe_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pastikan tipe data kolom numerik, tahun, dan tanggal benar.
    Nilai yang gagal dikonversi (misal teks aneh di kolom angka)
    otomatis jadi NaN via errors="coerce" — bukan bikin aplikasi crash.

    Setelah memparse kolom START, fungsi ini mengekstrak hari (angka)
    ke kolom baru TANGGAL, lalu menghapus START dan END dari DataFrame.
    Konsisten dengan proses cleaning manual di notebook.
    """
    df = df.copy()

    for kolom in KOLOM_NUMERIK:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

    if "TAHUN" in df.columns:
        df["TAHUN"] = pd.to_numeric(df["TAHUN"], errors="coerce").astype("Int64")

    for kolom in KOLOM_TANGGAL:
        if kolom not in df.columns:
            continue

        nilai_asli_terisi = df[kolom].notna().sum()
        df[kolom] = parse_tanggal_indonesia(df[kolom])
        nilai_hasil_terisi = df[kolom].notna().sum()

        # Kalau ada baris yang tadinya terisi tapi gagal diparse jadi NaT,
        # itu bukan berarti datanya memang kosong -- kemungkinan besar
        # formatnya beda dari yang diantisipasi. Ini sengaja di-print
        # sebagai warning (bukan silent) supaya ketahuan saat development/testing.
        gagal_parse = nilai_asli_terisi - nilai_hasil_terisi
        if gagal_parse > 0:
            print(
                f"⚠️ PERINGATAN: {gagal_parse} baris di kolom '{kolom}' gagal "
                "diparse jadi tanggal dan menjadi kosong (NaT). Cek format "
                "tanggal aslinya, mungkin ada variasi format yang belum ditangani."
            )

    # Ekstrak hari dari START → kolom TANGGAL (Int64), lalu hapus START dan END.
    # Sesuai dengan proses notebook: df['HARI'] = df['START'].dt.day
    if "START" in df.columns:
        df["TANGGAL"] = df["START"].dt.day.astype("Int64")
        df = df.drop(columns=["START"])
    if "END" in df.columns:
        df = df.drop(columns=["END"])

    return df


def _klasifikasi_satu_baris(row: pd.Series, threshold: int) -> str:
    """
    Helper internal: tentukan RESULT_FINAL untuk satu baris.

    Rule (sesuai cleaning notebook):
      - RESULT_FINAL SELALU diklasifikasikan ulang dari nilai TEORI.
        Nilai RESULT asli di kolom 'RESULT' diabaikan untuk klasifikasi ini.
      - TEORI >= threshold → LULUS
      - TEORI < threshold (dan bukan NaN) → TIDAK LULUS
      - TEORI kosong/NaN → DATA TIDAK LENGKAP

    Kolom RESULT asli TETAP disimpan sebagai audit trail (tidak dihapus).
    """
    nilai_teori = row.get("TEORI")
    if pd.isna(nilai_teori):
        return STATUS_DATA_TIDAK_LENGKAP
    return STATUS_LULUS if nilai_teori >= threshold else STATUS_TIDAK_LULUS


def normalisasi_result(df: pd.DataFrame, threshold: int = None) -> pd.DataFrame:
    """
    Reklasifikasi kolom RESULT mentah menjadi kolom baru RESULT_FINAL
    yang nilainya konsisten: LULUS / TIDAK LULUS / DATA TIDAK LENGKAP.

    RESULT_FINAL selalu dihitung dari nilai TEORI (setelah normalisasi),
    bukan dari teks di kolom RESULT asli. Ini konsisten dengan:
        df['RESULT'] = df['TEORI'].apply(lambda x: 'LULUS' if x >= 80 else ...)
    di notebook pembersihan data.

    Kolom RESULT asli TIDAK dihapus — tetap disimpan sebagai jejak audit.
    """
    df = df.copy()
    threshold = threshold if threshold is not None else THRESHOLD_KELULUSAN

    df["RESULT_FINAL"] = df.apply(
        lambda row: _klasifikasi_satu_baris(row, threshold), axis=1
    )
    return df


def normalisasi_kategori_kosong(
    df: pd.DataFrame, kolom_list: list = None, label: str = "TIDAK DIKETAHUI"
) -> pd.DataFrame:
    """
    Isi nilai blank/NaN di kolom kategorikal dengan label eksplisit,
    supaya tidak muncul sebagai 'nan' mentah di dropdown filter/chart.
    """
    df = df.copy()
    kolom_list = kolom_list or KOLOM_KATEGORI

    for kolom in kolom_list:
        if kolom in df.columns:
            df[kolom] = df[kolom].fillna(label)
    return df


def normalisasi_duplikat(df: pd.DataFrame, subset_kolom: list = None) -> tuple[pd.DataFrame, int]:
    """
    Deteksi & hapus baris duplikat (misal karena double entry saat input data).

    Returns
    -------
    tuple[pd.DataFrame, int]
        DataFrame yang sudah bersih dari duplikat, dan jumlah baris yang dihapus.
        Jumlah ini dikembalikan secara eksplisit (bukan lewat st.session_state)
        supaya modul ini tetap tidak bergantung pada Streamlit.
    """
    subset_kolom = subset_kolom or KOLOM_KUNCI_DUPLIKAT
    subset_ada = [kolom for kolom in subset_kolom if kolom in df.columns]

    if not subset_ada:
        return df, 0

    jumlah_sebelum = len(df)
    df = df.drop_duplicates(subset=subset_ada, keep="first")
    jumlah_setelah = len(df)

    return df, jumlah_sebelum - jumlah_setelah


def normalisasi_nrp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buat kolom `NRP_ID` sebagai identifier karyawan yang handal:
    pakai NRP BARU jika terisi, fallback ke NRP LAMA jika NRP BARU kosong.

    Latar belakang: di data asli PT United Tractors, kolom NRP BARU banyak
    yang kosong (terutama karyawan lama), sehingga NRP LAMA menjadi satu-
    satunya identifier yang konsisten tersedia. `NRP_ID` inilah yang dipakai
    sebagai kunci deduplikasi (lihat KOLOM_KUNCI_DUPLIKAT di settings.py).

    Catatan: NRP sering dibaca pandas sebagai float (misal 70214522.0) karena
    ada baris kosong di kolom yang sama. Kita strip ".0" supaya dedup bisa
    mengenali NRP yang sama meski tipe datanya berbeda antar baris.

    Catatan kritis: jika KEDUA kolom NRP kosong untuk suatu baris, kita
    TIDAK membiarkan NRP_ID = "" — karena itu akan menyebabkan semua baris
    tanpa NRP yang punya modul+tahun sama dianggap duplikat dan dihapus!
    Sebagai gantinya, baris tersebut diberi ID unik berbasis nomor baris
    supaya tidak pernah ter-deduplikasi satu sama lain.
    """
    df = df.copy()

    def _bersihkan_nrp(series: pd.Series) -> pd.Series:
        """Konversi NRP ke string bersih: strip, hapus '.0' dari float, tangani NaN."""
        return (
            series
            .astype(str)
            .str.strip()
            # Hapus '.0' yang muncul saat NRP numerik dibaca pandas sebagai float
            .str.replace(r"\.0$", "", regex=True)
            .replace({"NAN": "", "nan": "", "NaN": "", "None": "", "none": "", "<NA>": ""})
        )

    nrp_lama = _bersihkan_nrp(df["NRP LAMA"])

    if "NRP BARU" in df.columns:
        nrp_baru = _bersihkan_nrp(df["NRP BARU"])
        # Pakai NRP BARU jika tidak kosong, fallback ke NRP LAMA
        df["NRP_ID"] = nrp_baru.where(nrp_baru != "", nrp_lama)
    else:
        df["NRP_ID"] = nrp_lama

    # Fallback akhir: baris yang NRP_ID-nya masih kosong (kedua NRP tidak
    # tersedia / keduanya NaN di Excel) diberi identifier unik berbasis nomor
    # baris. Ini mencegah false deduplication: tanpa ini, semua baris tanpa
    # NRP yang kebetulan punya modul+tahun sama akan dianggap satu orang dan
    # dihapus kecuali satu baris — menyebabkan modul kehilangan banyak data.
    mask_kosong = df["NRP_ID"] == ""
    if mask_kosong.any():
        idx_kosong = df.index[mask_kosong]
        df.loc[mask_kosong, "NRP_ID"] = [
            f"__TANPA_NRP_{i}__" for i in idx_kosong
        ]

    return df


def normalisasi_nilai_teori(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalisasi nilai TEORI yang inkonsisten akibat input manual.
    Rule sesuai cleaning notebook:

    - 1000 ≤ nilai ≤ 10000 : dibagi 100  (misal 9000 → 90.0, 8000 → 80.0)
    - 0 < nilai < 10       : dikali 10   (misal 7 → 70, 8 → 80)
    - 10 ≤ nilai ≤ 100     : apa adanya (rentang normal)
    - nilai ≤ 0 / NaN      : tetap NaN  (tidak valid)

    Nilai di range 101-999 dibiarkan apa adanya karena tidak termasuk pola
    inkonsisten yang terdokumentasi (bisa jadi skor dengan skala berbeda).

    Fungsi ini HARUS dipanggil SETELAH normalisasi_tipe_data() supaya kolom
    TEORI sudah bertipe numerik (float), bukan string.
    """
    if "TEORI" not in df.columns:
        return df

    df = df.copy()

    def _normalisasi_satu_nilai(nilai):
        if pd.isna(nilai) or nilai <= 0:
            return np.nan
        if 1000 <= nilai <= 10000:   # misal 9000 → 90, 8500 → 85
            return round(nilai / 100, 1)
        if nilai < 10:               # 0 < nilai < 10: misal 8 → 80
            return round(nilai * 10, 1)
        return nilai                 # 10–999 atau >10000: apa adanya

    df["TEORI"] = df["TEORI"].apply(_normalisasi_satu_nilai)
    return df


def filter_job_aktif(
    df: pd.DataFrame, job_list: list = None
) -> tuple[pd.DataFrame, int]:
    """
    Buang baris yang JOB-nya tidak ada di `job_list`.

    Hanya job COP, PTO, ADM_SERVICE yang relevan untuk visualisasi
    dashboard ini. Baris JOB lain (termasuk 'TIDAK DIKETAHUI' dari
    karyawan tanpa data JOB) dibuang di tahap ini.

    Fungsi ini HARUS dipanggil SETELAH normalisasi_teks() (supaya JOB
    sudah UPPERCASE) dan SETELAH normalisasi_duplikat() (supaya dedup
    tetap menghitung dari dataset lengkap, bukan subset yang sudah difilter).

    Returns
    -------
    tuple[pd.DataFrame, int]
        DataFrame yang sudah difilter dan jumlah baris yang dibuang.
    """
    job_list = job_list if job_list is not None else JOB_FILTER_AKTIF

    if "JOB" not in df.columns:
        return df, 0

    jumlah_sebelum = len(df)
    df_filtered = df[df["JOB"].isin(job_list)].copy()
    jumlah_dibuang = jumlah_sebelum - len(df_filtered)

    return df_filtered, jumlah_dibuang


def jalankan_pipeline_normalisasi(df: pd.DataFrame) -> dict:
    """
    Fungsi utama yang dipanggil dari app.py — menjalankan seluruh
    tahapan normalisasi secara berurutan.

    Urutan tahapan (JANGAN diubah tanpa memahami dependensinya):
      1. normalisasi_teks          — uppercase/trim dulu supaya lookup berikutnya konsisten
      2. normalisasi_nrp           — NRP_ID dibutuhkan oleh normalisasi_duplikat
      3. normalisasi_tipe_data     — TEORI harus jadi numerik sebelum dinormalisasi nilainya
      4. normalisasi_nilai_teori   — fix TEORI inkonsisten SEBELUM klasifikasi RESULT
      5. normalisasi_result        — RESULT_FINAL bergantung pada nilai TEORI yang sudah benar
      6. normalisasi_kategori_kosong— NaN → 'TIDAK DIKETAHUI' termasuk JOB kosong
      7. normalisasi_duplikat      — dedup dari dataset lengkap (sebelum filter JOB)
      8. filter_job_aktif          — buang JOB di luar COP/PTO/ADM_SERVICE (tahap terakhir)

    Returns
    -------
    dict
        {
            "data"                  : pd.DataFrame,  # data final yang sudah bersih
            "jumlah_job_dibuang"    : int,  # baris yang dibuang karena JOB tidak relevan
        }
    """
    df = normalisasi_teks(df)
    df = normalisasi_nrp(df)
    df = normalisasi_tipe_data(df)
    df = normalisasi_nilai_teori(df)
    df = normalisasi_result(df)
    df = normalisasi_kategori_kosong(df)
    # normalisasi_duplikat TIDAK dipanggil di pipeline utama.
    # Setiap baris di data sumber merepresentasikan 1 event training yang unik dan valid.
    # Menghapus "duplikat" berdasarkan NRP+Modul+Tahun ternyata membuang data yang sah
    # (misal karyawan yang ikut modul yang sama dua kali dalam setahun).
    # Konsisten dengan notebook cleaning yang juga tidak melakukan drop_duplicates().

    # Simpan distribusi JOB sebelum difilter sebagai diagnostik.
    distribusi_job_sebelum_filter = (
        df["JOB"].value_counts().to_dict() if "JOB" in df.columns else {}
    )

    df, jumlah_job_dibuang = filter_job_aktif(df)

    return {
        "data": df,
        "jumlah_job_dibuang": jumlah_job_dibuang,
        "distribusi_job_sebelum_filter": distribusi_job_sebelum_filter,
    }