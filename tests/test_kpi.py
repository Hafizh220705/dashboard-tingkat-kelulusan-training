"""
Unit test untuk src/metrics/kpi.py.

Jalankan dengan:
    pytest tests/test_kpi.py -v
"""

import pandas as pd
import pytest

from src.metrics.kpi import (
    agregasi_per_employee,
    hitung_kpi_dasar,
    hitung_kpi_per_kategori,
    siapkan_data_kpi,
)
from config.settings import (
    LEVEL_PER_EMPLOYEE,
    LEVEL_PER_PARTISIPASI,
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)


# =========================================================
# FIXTURE — DATA SUDAH TERNORMALISASI (level partisipasi)
# =========================================================
@pytest.fixture
def data_partisipasi():
    """
    Dataset dummy setara output pipeline normalisasi.
    N1: ikut 2 training, satu LULUS satu TIDAK LULUS -> harus LULUS di level employee
    N2: ikut 1 training, TIDAK LULUS -> tetap TIDAK LULUS di level employee
    N3: ikut 2 training, dua-duanya DATA TIDAK LENGKAP -> DATA TIDAK LENGKAP
    N4: ikut 1 training, DATA TIDAK LENGKAP campur, tapi tidak ada LULUS & tidak semua TIDAK LULUS
    """
    return pd.DataFrame({
        "NRP BARU": ["N1", "N1", "N2", "N3", "N3", "N4", "N4"],
        "AREA": ["PLANT A", "PLANT A", "PLANT B", "PLANT A", "PLANT A", "PLANT B", "PLANT B"],
        "JOB": ["OPERATOR", "OPERATOR", "MEKANIK", "OPERATOR", "OPERATOR", "MEKANIK", "MEKANIK"],
        "MODUL TRAINING": ["SAFETY", "TEKNIS", "SAFETY", "SAFETY", "TEKNIS", "SAFETY", "TEKNIS"],
        "RESULT_FINAL": [
            STATUS_LULUS, STATUS_TIDAK_LULUS,      # N1
            STATUS_TIDAK_LULUS,                     # N2
            STATUS_DATA_TIDAK_LENGKAP, STATUS_DATA_TIDAK_LENGKAP,  # N3
            STATUS_TIDAK_LULUS, STATUS_DATA_TIDAK_LENGKAP,          # N4
        ],
    })


@pytest.fixture
def data_kosong():
    return pd.DataFrame({"NRP BARU": [], "AREA": [], "RESULT_FINAL": []})


# =========================================================
# TEST: agregasi_per_employee
# =========================================================
class TestAgregasiPerEmployee:
    def test_employee_dengan_satu_lulus_dianggap_lulus(self, data_partisipasi):
        """N1 punya 1 LULUS + 1 TIDAK LULUS -> keseluruhan harus LULUS."""
        hasil = agregasi_per_employee(data_partisipasi)
        status_n1 = hasil.loc[hasil["NRP BARU"] == "N1", "RESULT_FINAL"].iloc[0]
        assert status_n1 == STATUS_LULUS

    def test_employee_semua_tidak_lulus(self, data_partisipasi):
        hasil = agregasi_per_employee(data_partisipasi)
        status_n2 = hasil.loc[hasil["NRP BARU"] == "N2", "RESULT_FINAL"].iloc[0]
        assert status_n2 == STATUS_TIDAK_LULUS

    def test_employee_semua_data_tidak_lengkap(self, data_partisipasi):
        hasil = agregasi_per_employee(data_partisipasi)
        status_n3 = hasil.loc[hasil["NRP BARU"] == "N3", "RESULT_FINAL"].iloc[0]
        assert status_n3 == STATUS_DATA_TIDAK_LENGKAP

    def test_employee_campuran_tanpa_lulus_bukan_semua_tidak_lulus(self, data_partisipasi):
        """
        N4: [TIDAK LULUS, DATA TIDAK LENGKAP] -> tidak ada LULUS, dan TIDAK
        semua baris TIDAK LULUS -> harus DATA TIDAK LENGKAP, bukan TIDAK LULUS.
        Ini edge case penting: jangan sampai employee dirugikan dianggap
        'Tidak Lulus' padahal sebagian datanya belum lengkap.
        """
        hasil = agregasi_per_employee(data_partisipasi)
        status_n4 = hasil.loc[hasil["NRP BARU"] == "N4", "RESULT_FINAL"].iloc[0]
        assert status_n4 == STATUS_DATA_TIDAK_LENGKAP

    def test_jumlah_training_diikuti_terhitung_benar(self, data_partisipasi):
        hasil = agregasi_per_employee(data_partisipasi)
        jumlah_n1 = hasil.loc[hasil["NRP BARU"] == "N1", "jumlah_training_diikuti"].iloc[0]
        assert jumlah_n1 == 2

    def test_jumlah_baris_sesuai_unique_employee(self, data_partisipasi):
        hasil = agregasi_per_employee(data_partisipasi)
        assert len(hasil) == data_partisipasi["NRP BARU"].nunique()
        assert len(hasil) == 4  # N1, N2, N3, N4

    def test_kolom_wajib_hilang_raise_keyerror(self):
        df = pd.DataFrame({"KOLOM_LAIN": [1, 2]})
        with pytest.raises(KeyError):
            agregasi_per_employee(df)

    def test_kolom_id_custom(self, data_partisipasi):
        df = data_partisipasi.rename(columns={"NRP BARU": "ID_LAIN"})
        hasil = agregasi_per_employee(df, kolom_id="ID_LAIN")
        assert "ID_LAIN" in hasil.columns


# =========================================================
# TEST: siapkan_data_kpi
# =========================================================
class TestSiapkanDataKpi:
    def test_level_per_partisipasi_tidak_diagregasi(self, data_partisipasi):
        hasil = siapkan_data_kpi(data_partisipasi, LEVEL_PER_PARTISIPASI)
        assert len(hasil) == len(data_partisipasi)

    def test_level_per_employee_teragregasi(self, data_partisipasi):
        hasil = siapkan_data_kpi(data_partisipasi, LEVEL_PER_EMPLOYEE)
        assert len(hasil) == data_partisipasi["NRP BARU"].nunique()

    def test_level_tidak_dikenal_raise_valueerror(self, data_partisipasi):
        with pytest.raises(ValueError):
            siapkan_data_kpi(data_partisipasi, "Level Ngasal")

    def test_input_asli_tidak_termutasi(self, data_partisipasi):
        """siapkan_data_kpi tidak boleh mengubah DataFrame input asli."""
        salinan = data_partisipasi.copy()
        siapkan_data_kpi(data_partisipasi, LEVEL_PER_PARTISIPASI)
        pd.testing.assert_frame_equal(data_partisipasi, salinan)


# =========================================================
# TEST: hitung_kpi_dasar
# =========================================================
class TestHitungKpiDasar:
    def test_total_sesuai_jumlah_baris(self, data_partisipasi):
        kpi = hitung_kpi_dasar(data_partisipasi)
        assert kpi["total"] == 7

    def test_total_lulus_benar(self, data_partisipasi):
        kpi = hitung_kpi_dasar(data_partisipasi)
        assert kpi["total_lulus"] == 1  # cuma baris pertama N1

    def test_total_tidak_lulus_benar(self, data_partisipasi):
        kpi = hitung_kpi_dasar(data_partisipasi)
        assert kpi["total_tidak_lulus"] == 3  # N1(1), N2(1), N4(1)

    def test_total_tidak_lengkap_benar(self, data_partisipasi):
        kpi = hitung_kpi_dasar(data_partisipasi)
        assert kpi["total_tidak_lengkap"] == 3  # N3(2), N4(1)

    def test_pass_rate_dan_fail_rate_dihitung_benar(self, data_partisipasi):
        kpi = hitung_kpi_dasar(data_partisipasi)
        assert kpi["pass_rate"] == round(1 / 7 * 100, 1)
        assert kpi["fail_rate"] == round(3 / 7 * 100, 1)

    def test_total_lulus_tidak_lulus_tidak_lengkap_menjumlah_ke_total(self, data_partisipasi):
        """Invariant penting: 3 kategori status harus habis membagi total."""
        kpi = hitung_kpi_dasar(data_partisipasi)
        jumlah = kpi["total_lulus"] + kpi["total_tidak_lulus"] + kpi["total_tidak_lengkap"]
        assert jumlah == kpi["total"]

    def test_dataframe_kosong_tidak_error(self, data_kosong):
        """
        Regression test kritis: dulu ini bisa ZeroDivisionError kalau user
        filter kombinasi yang hasilnya 0 baris. Sekarang harus return 0,
        bukan crash.
        """
        kpi = hitung_kpi_dasar(data_kosong)
        assert kpi["total"] == 0
        assert kpi["pass_rate"] == 0.0
        assert kpi["fail_rate"] == 0.0

    def test_semua_lulus_pass_rate_100_persen(self):
        df = pd.DataFrame({"RESULT_FINAL": [STATUS_LULUS, STATUS_LULUS]})
        kpi = hitung_kpi_dasar(df)
        assert kpi["pass_rate"] == 100.0
        assert kpi["fail_rate"] == 0.0


# =========================================================
# TEST: hitung_kpi_per_kategori
# =========================================================
class TestHitungKpiPerKategori:
    def test_kolom_kategori_tidak_ada_raise_keyerror(self, data_partisipasi):
        with pytest.raises(KeyError):
            hitung_kpi_per_kategori(data_partisipasi, "KOLOM_TIDAK_ADA")

    def test_breakdown_by_area_jumlah_baris_sesuai_unique_area(self, data_partisipasi):
        tabel = hitung_kpi_per_kategori(data_partisipasi, "AREA")
        assert len(tabel) == data_partisipasi["AREA"].nunique()

    def test_kolom_status_selalu_lengkap_meski_nilai_nol(self):
        """
        Kalau satu kategori tidak punya baris LULUS sama sekali, kolom LULUS
        tetap harus muncul di tabel (bernilai 0), bukan hilang -- supaya
        chart/tabel di komponen UI tidak error karena KeyError kolom hilang.
        """
        df = pd.DataFrame({
            "AREA": ["PLANT A", "PLANT A"],
            "RESULT_FINAL": [STATUS_TIDAK_LULUS, STATUS_TIDAK_LULUS],
        })
        tabel = hitung_kpi_per_kategori(df, "AREA")
        assert STATUS_LULUS in tabel.columns
        assert tabel.loc["PLANT A", STATUS_LULUS] == 0

    def test_total_per_kategori_benar(self, data_partisipasi):
        tabel = hitung_kpi_per_kategori(data_partisipasi, "AREA")
        # PLANT A: N1(2 baris) + N3(2 baris) = 4 baris
        assert tabel.loc["PLANT A", "Total"] == 4

    def test_pass_rate_per_kategori_benar(self, data_partisipasi):
        tabel = hitung_kpi_per_kategori(data_partisipasi, "AREA")
        # PLANT A: 4 total, 1 lulus (dari N1) -> 25.0%
        assert tabel.loc["PLANT A", "Pass Rate (%)"] == 25.0

    def test_terurut_dari_total_terbesar(self, data_partisipasi):
        tabel = hitung_kpi_per_kategori(data_partisipasi, "AREA")
        totals = tabel["Total"].tolist()
        assert totals == sorted(totals, reverse=True)


# =========================================================
# TEST INTEGRASI: alur lengkap partisipasi -> employee -> KPI
# =========================================================
class TestIntegrasiAlurKpi:
    def test_kpi_level_partisipasi_vs_level_employee_beda_hasil(self, data_partisipasi):
        """
        Sanity check: dua level agregasi HARUS menghasilkan angka KPI
        yang berbeda untuk dataset yang sama x employee yang mengikuti
        lebih dari satu training. Kalau hasilnya identik, kemungkinan
        besar ada bug di agregasi_per_employee.
        """
        df_partisipasi = siapkan_data_kpi(data_partisipasi, LEVEL_PER_PARTISIPASI)
        df_employee = siapkan_data_kpi(data_partisipasi, LEVEL_PER_EMPLOYEE)

        kpi_partisipasi = hitung_kpi_dasar(df_partisipasi)
        kpi_employee = hitung_kpi_dasar(df_employee)

        assert kpi_partisipasi["total"] == 7
        assert kpi_employee["total"] == 4
        assert kpi_partisipasi["pass_rate"] != kpi_employee["pass_rate"]