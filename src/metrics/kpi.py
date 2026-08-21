"""
Modul untuk menghitung KPI & agregasi level analisis (per partisipasi vs
per employee) dari data training yang sudah dinormalisasi.

Modul ini SENGAJA tidak bergantung pada Streamlit — hanya menerima
DataFrame dan mengembalikan angka/DataFrame, supaya bisa di-unit-test
terpisah dan dipakai ulang di komponen manapun.

Prasyarat: DataFrame input harus sudah melewati
`src.data.normalizer.jalankan_pipeline_normalisasi()` (harus punya
kolom RESULT_FINAL).
"""

import pandas as pd

from config.settings import (
    LEVEL_PER_EMPLOYEE,
    LEVEL_PER_PARTISIPASI,
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)

KOLOM_ID_EMPLOYEE_DEFAULT = "NRP_ID"


def _agregasi_status_satu_employee(status_list: pd.Series) -> str:
    """
    Helper internal: tentukan status akhir SATU employee dari kumpulan
    RESULT_FINAL semua training yang dia ikuti.

    Rule (ASUMSI — perlu dikonfirmasi ke mentor):
      - Kalau minimal ada satu training berstatus LULUS -> employee LULUS
      - Kalau semua training berstatus TIDAK LULUS -> employee TIDAK LULUS
      - Selain itu (campuran TIDAK LULUS & DATA TIDAK LENGKAP,
        atau semua DATA TIDAK LENGKAP) -> DATA TIDAK LENGKAP
    """
    if (status_list == STATUS_LULUS).any():
        return STATUS_LULUS
    if (status_list == STATUS_TIDAK_LULUS).all():
        return STATUS_TIDAK_LULUS
    return STATUS_DATA_TIDAK_LENGKAP


def agregasi_per_employee(
    df: pd.DataFrame, kolom_id: str = KOLOM_ID_EMPLOYEE_DEFAULT
) -> pd.DataFrame:
    """
    Ubah data dari level "per partisipasi" (1 baris = 1 employee x 1 modul)
    jadi level "per employee" (1 baris = 1 employee, status gabungan dari
    semua training yang dia ikuti).

    Parameters
    ----------
    df : pd.DataFrame
        Harus punya kolom `kolom_id` dan `RESULT_FINAL`.
    kolom_id : str
        Nama kolom identifier employee.

    Returns
    -------
    pd.DataFrame
        Kolom: [kolom_id, "RESULT_FINAL", "jumlah_training_diikuti"]
    """
    if kolom_id not in df.columns or "RESULT_FINAL" not in df.columns:
        raise KeyError(
            f"DataFrame harus punya kolom '{kolom_id}' dan 'RESULT_FINAL'. "
            "Pastikan data sudah melewati pipeline normalisasi."
        )

    hasil = (
        df.groupby(kolom_id)["RESULT_FINAL"]
        .agg(
            RESULT_FINAL=_agregasi_status_satu_employee,
            jumlah_training_diikuti="count",
        )
        .reset_index()
    )
    return hasil


def siapkan_data_kpi(
    df: pd.DataFrame,
    level_agregasi: str,
    kolom_id: str = KOLOM_ID_EMPLOYEE_DEFAULT,
) -> pd.DataFrame:
    """
    Titik masuk utama: siapkan DataFrame yang akan dipakai untuk hitung
    KPI, sesuai level agregasi yang dipilih user di sidebar.

    Parameters
    ----------
    level_agregasi : str
        Salah satu dari LEVEL_PER_PARTISIPASI atau LEVEL_PER_EMPLOYEE
        (konstanta di config/settings.py).

    Returns
    -------
    pd.DataFrame
        Kalau LEVEL_PER_PARTISIPASI -> df apa adanya (setiap baris = 1 partisipasi).
        Kalau LEVEL_PER_EMPLOYEE -> hasil agregasi_per_employee().
    """
    if level_agregasi == LEVEL_PER_EMPLOYEE:
        return agregasi_per_employee(df, kolom_id=kolom_id)
    if level_agregasi == LEVEL_PER_PARTISIPASI:
        return df.copy()

    raise ValueError(
        f"level_agregasi tidak dikenal: '{level_agregasi}'. "
        f"Gunakan '{LEVEL_PER_PARTISIPASI}' atau '{LEVEL_PER_EMPLOYEE}'."
    )


def hitung_kpi_dasar(df_kpi: pd.DataFrame) -> dict:
    """
    Hitung 6 KPI utama dari DataFrame yang sudah disiapkan
    (hasil dari `siapkan_data_kpi()`).

    Returns
    -------
    dict
        {
            "total": int,
            "total_lulus": int,
            "total_tidak_lulus": int,
            "total_tidak_lengkap": int,
            "pass_rate": float,   # dalam persen, 0-100
            "fail_rate": float,   # dalam persen, 0-100
        }

        Kalau df_kpi kosong (0 baris), semua nilai dikembalikan 0
        (tidak raise ZeroDivisionError) — pemanggil (komponen UI)
        yang bertanggung jawab menampilkan pesan "data kosong" jika perlu.
    """
    total = len(df_kpi)

    if total == 0:
        return {
            "total": 0,
            "total_lulus": 0,
            "total_tidak_lulus": 0,
            "total_tidak_lengkap": 0,
            "pass_rate": 0.0,
            "fail_rate": 0.0,
        }

    total_lulus = int((df_kpi["RESULT_FINAL"] == STATUS_LULUS).sum())
    total_tidak_lulus = int((df_kpi["RESULT_FINAL"] == STATUS_TIDAK_LULUS).sum())
    total_tidak_lengkap = int((df_kpi["RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP).sum())

    return {
        "total": total,
        "total_lulus": total_lulus,
        "total_tidak_lulus": total_tidak_lulus,
        "total_tidak_lengkap": total_tidak_lengkap,
        "pass_rate": round(total_lulus / total * 100, 1),
        "fail_rate": round(total_tidak_lulus / total * 100, 1),
    }


def hitung_kpi_per_kategori(df: pd.DataFrame, kolom_kategori: str) -> pd.DataFrame:
    """
    Hitung rekap KPI (jumlah per status + pass rate) yang di-breakdown
    per kategori tertentu (misal AREA, JOB, MODUL TRAINING).

    Dipakai oleh komponen chart/tabel breakdown (chart_area.py, chart_job.py, dst.)
    supaya logic hitungnya tidak diduplikasi di tiap file komponen.

    Parameters
    ----------
    df : pd.DataFrame
        Data level partisipasi (bukan hasil agregasi_per_employee),
        harus punya kolom `kolom_kategori` dan "RESULT_FINAL".
    kolom_kategori : str
        Nama kolom yang jadi dasar breakdown, misal "AREA".

    Returns
    -------
    pd.DataFrame
        Index = nilai kategori, kolom = [LULUS, TIDAK LULUS, DATA TIDAK LENGKAP,
        Total, Pass Rate (%)], terurut dari Total terbesar ke terkecil.
    """
    if kolom_kategori not in df.columns:
        raise KeyError(f"Kolom '{kolom_kategori}' tidak ditemukan di DataFrame.")

    tabel = (
        df.groupby(kolom_kategori)["RESULT_FINAL"]
        .value_counts()
        .unstack(fill_value=0)
    )

    # Pastikan ketiga kolom status selalu ada, meski nilainya 0
    for status in [STATUS_LULUS, STATUS_TIDAK_LULUS, STATUS_DATA_TIDAK_LENGKAP]:
        if status not in tabel.columns:
            tabel[status] = 0

    tabel["Total"] = tabel[[STATUS_LULUS, STATUS_TIDAK_LULUS, STATUS_DATA_TIDAK_LENGKAP]].sum(axis=1)
    tabel["Pass Rate (%)"] = (tabel[STATUS_LULUS] / tabel["Total"] * 100).round(1)

    return tabel.sort_values("Total", ascending=False)