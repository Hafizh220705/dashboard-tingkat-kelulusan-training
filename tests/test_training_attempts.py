"""Test fallback nilai pertanyaan dan agregasi maksimal tiga percobaan."""

import pandas as pd

from config.settings import (
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)
from src.components.training_results_dashboard import rekap_kelulusan_percobaan
from src.data.training_attempts import (
    agregasi_percobaan_per_karyawan,
    normalisasi_nilai_pertanyaan,
)


def test_soal_1_sampai_5_memakai_skala_10_lalu_fallback_skala_20():
    df = pd.DataFrame(
        {
            "Q. 1 /10.00": [8, None, "-", 15],
            "Q. 1 /20.00": [19, 16, None, 18],
        }
    )

    hasil = normalisasi_nilai_pertanyaan(df)

    assert hasil["Q. 1 NILAI"].tolist()[:2] == [8, 16]
    assert pd.isna(hasil.loc[2, "Q. 1 NILAI"])
    assert hasil.loc[3, "Q. 1 NILAI"] == 18
    assert hasil["Q. 1 MAKSIMAL"].dropna().tolist() == [10, 20, 20]
    assert pd.isna(hasil.loc[2, "Q. 1 MAKSIMAL"])
    assert hasil["Q. 1 SUMBER"].tolist()[:2] == ["/10.00", "/20.00"]
    assert hasil.loc[0, "Q. 1 PERSEN"] == 80
    assert hasil.loc[1, "Q. 1 PERSEN"] == 80


def test_soal_6_sampai_10_hanya_memakai_skala_10():
    df = pd.DataFrame({"Q. 6 /10.00": [7.5, None]})

    hasil = normalisasi_nilai_pertanyaan(df)

    assert hasil.loc[0, "Q. 6 NILAI"] == 7.5
    assert hasil.loc[0, "Q. 6 PERSEN"] == 75
    assert pd.isna(hasil.loc[1, "Q. 6 NILAI"])


def _data_percobaan() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "NRP_ID": ["A", "A", "B", "B", "B", "C"],
            "NILAI_FINAL": [80, 60, 75, 50, 65, None],
            "RESULT_FINAL": [
                STATUS_LULUS,
                STATUS_TIDAK_LULUS,
                STATUS_TIDAK_LULUS,
                STATUS_TIDAK_LULUS,
                STATUS_TIDAK_LULUS,
                STATUS_DATA_TIDAK_LENGKAP,
            ],
            # Sengaja tidak berurutan untuk memastikan sorting memakai waktu.
            "Completed": [
                "2026-01-02 10:00",
                "2026-01-01 10:00",
                "2026-01-03 10:00",
                "2026-01-01 10:00",
                "2026-01-02 10:00",
                "2026-01-01 10:00",
            ],
        }
    )


def test_status_akhir_memakai_nilai_terbaik_dari_maksimal_tiga_percobaan():
    hasil, percobaan, ringkasan = agregasi_percobaan_per_karyawan(
        _data_percobaan()
    )
    hasil = hasil.set_index("NRP_ID")

    assert hasil.loc["A", "NILAI_PERCOBAAN_1"] == 60
    assert hasil.loc["A", "NILAI_PERCOBAAN_2"] == 80
    assert pd.isna(hasil.loc["A", "NILAI_PERCOBAAN_3"])
    assert hasil.loc["A", "NILAI_TERBAIK"] == 80
    assert hasil.loc["A", "RESULT_FINAL"] == STATUS_LULUS
    assert hasil.loc["A", "LULUS_PADA_PERCOBAAN"] == 2

    assert hasil.loc["B", "NILAI_TERBAIK"] == 75
    assert hasil.loc["B", "RESULT_FINAL"] == STATUS_TIDAK_LULUS
    assert pd.isna(hasil.loc["B", "LULUS_PADA_PERCOBAAN"])

    assert hasil.loc["C", "RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP
    assert ringkasan.jumlah_karyawan == 3
    assert ringkasan.jumlah_percobaan == len(percobaan) == 6


def test_percobaan_keempat_tidak_memengaruhi_status_akhir():
    df = pd.DataFrame(
        {
            "NRP_ID": ["A"] * 4,
            "NILAI_FINAL": [50, 60, 70, 100],
            "RESULT_FINAL": [STATUS_TIDAK_LULUS] * 3 + [STATUS_LULUS],
            "Completed": pd.date_range("2026-01-01", periods=4),
        }
    )

    hasil, percobaan, ringkasan = agregasi_percobaan_per_karyawan(df)

    assert hasil.loc[0, "NILAI_TERBAIK"] == 70
    assert hasil.loc[0, "RESULT_FINAL"] == STATUS_TIDAK_LULUS
    assert ringkasan.jumlah_percobaan_diabaikan == 1
    assert percobaan["DIGUNAKAN_DALAM_HASIL"].tolist() == [True, True, True, False]


def test_baris_tanpa_nrp_tidak_digabung_sebagai_satu_karyawan():
    df = pd.DataFrame(
        {
            "NRP_ID": [None, None],
            "NILAI_FINAL": [90, 50],
            "RESULT_FINAL": [STATUS_LULUS, STATUS_TIDAK_LULUS],
        }
    )

    hasil, _, ringkasan = agregasi_percobaan_per_karyawan(df)

    assert len(hasil) == 2
    assert ringkasan.jumlah_baris_tanpa_nrp == 2


def test_rekap_visualisasi_membedakan_lulus_di_percobaan_berapa():
    hasil, _, _ = agregasi_percobaan_per_karyawan(_data_percobaan())

    rekap = rekap_kelulusan_percobaan(hasil).set_index("Kategori")["Jumlah"]

    assert rekap["Percobaan 2"] == 1
    assert rekap["Belum Lulus"] == 1
    assert rekap["Data Tidak Lengkap"] == 1
