"""
Unit test untuk src/data/normalizer.py.

Jalankan dengan:
    pytest tests/test_normalizer.py -v
"""

import numpy as np
import pandas as pd
import pytest

from src.data.normalizer import (
    filter_job_aktif,
    jalankan_pipeline_normalisasi,
    normalisasi_duplikat,
    normalisasi_kategori_kosong,
    normalisasi_nrp,
    normalisasi_nilai_teori,
    normalisasi_result,
    normalisasi_teks,
    normalisasi_tipe_data,
    parse_tanggal_indonesia,
)
from config.settings import (
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)


# =========================================================
# FIXTURE — DATA DUMMY DENGAN EDGE CASE
# =========================================================
@pytest.fixture
def data_mentah():
    """Dataset dummy yang sengaja mencakup edge case penting."""
    return pd.DataFrame({
        "NRP LAMA": ["L1", "L2", "L3", "L4", "L5", "L6", "L6"],
        "NRP BARU": ["N1", "N2", "N3", None, "N5", "N6", "N6"],  # N4 kosong → fallback NRP LAMA
        "AREA": [" plant a ", "Plant B", None, "plant a", "Plant C", "Plant B", "Plant B"],
        "SUPPORT AREA": ["X", "Y", "X", None, "Y", "X", "X"],
        # PENTING: 'CPO' bukan 'COP' — sesuai data asli
        "JOB": ["CPO", "ADM_SERVICE", "CPO", "PTO", None, "CPO", "CPO"],
        "BULAN": ["JULI", "JULI", "AGUSTUS", "AGUSTUS", "JULI", "SEPTEMBER", "SEPTEMBER"],
        "MODUL TRAINING": ["Safety", "Safety", "Teknis", "Teknis", "Safety", "Teknis", "Teknis"],
        "SPESIALISASI": ["-"] * 7,
        "GROUP": ["G1", "G1", "G2", "G2", "G1", "G2", "G2"],
        "TAHUN": [2024, 2024, "2023", 2023, 2024, 2025, 2025],
        "START": ["01 Januari 2024"] * 7,
        "END": ["05 Januari 2024"] * 7,
        # TEORI: 9000→90 (1000-10000 /100), 8→80 (<10 *10)
        "TEORI": [85, 60, np.nan, 9000, 8, 82, 82],
        "PRAKTEK": [np.nan] * 7,
        "RESULT": ["Lulus", "Tidak Lulus", "Finished", "Finished", "Aneh_value", "Finished", "Finished"],
    })


# =========================================================
# TEST: normalisasi_teks
# =========================================================
class TestNormalisasiTeks:
    def test_trim_dan_uppercase(self, data_mentah):
        df = normalisasi_teks(data_mentah)
        assert df.loc[0, "AREA"] == "PLANT A"

    def test_spasi_ganda_dirapikan(self):
        df = pd.DataFrame({"AREA": ["Plant   A"]})
        df = normalisasi_teks(df, kolom_list=["AREA"])
        assert df.loc[0, "AREA"] == "PLANT A"

    def test_none_tetap_nan_bukan_string(self, data_mentah):
        """Regression test: None jangan sampai berubah jadi string 'NAN'."""
        df = normalisasi_teks(data_mentah)
        assert pd.isna(df.loc[2, "AREA"])

    def test_tidak_mengubah_dataframe_asli(self, data_mentah):
        """Pastikan fungsi tidak mutate DataFrame input (side-effect free)."""
        area_asli = data_mentah["AREA"].copy()
        normalisasi_teks(data_mentah)
        pd.testing.assert_series_equal(data_mentah["AREA"], area_asli)


# =========================================================
# TEST: parse_tanggal_indonesia — regression test untuk bug nyata
# =========================================================
class TestParseTanggalIndonesia:
    """
    Bug asal: pd.to_datetime() bawaan TIDAK bisa parse format tanggal
    Indonesia seperti '04 Juli 2019' -- dengan errors='coerce', hasilnya
    diam-diam jadi NaT tanpa ada tanda error yang jelas. Ditemukan saat
    mentor kasih contoh data asli (kolom START/END). Class ini memastikan
    bug itu tidak muncul lagi di masa depan.
    """

    def test_format_tanggal_indonesia_asli_dari_data_real(self):
        hasil = parse_tanggal_indonesia(pd.Series(["04 Juli 2019", "05 Juli 2019"]))
        assert hasil.notna().all()
        assert hasil.iloc[0] == pd.Timestamp("2019-07-04")
        assert hasil.iloc[1] == pd.Timestamp("2019-07-05")

    def test_semua_nama_bulan_indonesia(self):
        """Pastikan ke-12 nama bulan Indonesia semuanya bisa diparse, bukan cuma Juli."""
        tanggal_per_bulan = [
            "01 Januari 2024", "01 Februari 2024", "01 Maret 2024", "01 April 2024",
            "01 Mei 2024", "01 Juni 2024", "01 Juli 2024", "01 Agustus 2024",
            "01 September 2024", "01 Oktober 2024", "01 November 2024", "01 Desember 2024",
        ]
        hasil = parse_tanggal_indonesia(pd.Series(tanggal_per_bulan))
        assert hasil.notna().all()
        assert hasil.iloc[0].month == 1
        assert hasil.iloc[11].month == 12

    def test_format_tidak_dikenal_tetap_nat_bukan_crash(self):
        """Format aneh yang tidak bisa diparse harus jadi NaT, bukan raise exception."""
        hasil = parse_tanggal_indonesia(pd.Series(["format aneh sekali"]))
        assert pd.isna(hasil.iloc[0])

    def test_nilai_kosong_tetap_nat(self):
        hasil = parse_tanggal_indonesia(pd.Series([None, np.nan]))
        assert hasil.isna().all()


# =========================================================
# TEST: normalisasi_tipe_data
# =========================================================
class TestNormalisasiTipeData:
    def test_teori_jadi_numerik(self, data_mentah):
        df = normalisasi_tipe_data(data_mentah)
        assert pd.api.types.is_numeric_dtype(df["TEORI"])
        assert pd.isna(df.loc[2, "TEORI"])

    def test_tahun_jadi_integer_nullable(self, data_mentah):
        df = normalisasi_tipe_data(data_mentah)
        assert df["TAHUN"].dtype.name == "Int64"
        # String "2023" harus berhasil dikonversi jadi int, bukan NaN
        assert df.loc[2, "TAHUN"] == 2023

    def test_tanggal_jadi_datetime(self, data_mentah):
        df = normalisasi_tipe_data(data_mentah)
        assert pd.api.types.is_datetime64_any_dtype(df["START"])

    def test_tanggal_format_indonesia_terparse_benar(self, data_mentah):
        """
        Regression test kunci: fixture data_mentah pakai format tanggal
        Indonesia ('01 Januari 2024'). Kalau normalisasi_tipe_data() balik
        pakai pd.to_datetime() polos tanpa parse_tanggal_indonesia(),
        test ini akan gagal karena semua baris START/END jadi NaT.
        """
        df = normalisasi_tipe_data(data_mentah)
        assert df["START"].notna().all()
        assert df["END"].notna().all()
        assert df.loc[0, "START"] == pd.Timestamp("2024-01-01")
        assert df.loc[0, "END"] == pd.Timestamp("2024-01-05")

    def test_durasi_training_bisa_dihitung_setelah_parsing(self, data_mentah):
        """
        Sanity check end-to-end: setelah parsing benar, durasi training
        (END - START) harus bisa dihitung sebagai angka, bukan NaT.
        Ini tujuan akhir kenapa fix parsing tanggal ini penting.
        """
        df = normalisasi_tipe_data(data_mentah)
        durasi = (df["END"] - df["START"]).dt.days
        assert durasi.notna().all()
        assert durasi.iloc[0] == 4

    def test_nilai_tidak_valid_jadi_nan_bukan_error(self):
        """Nilai teks aneh di kolom numerik tidak boleh bikin fungsi crash."""
        df = pd.DataFrame({"TEORI": ["abc", "90"], "PRAKTEK": [None, None], "TAHUN": [2024, 2024]})
        df = normalisasi_tipe_data(df)
        assert pd.isna(df.loc[0, "TEORI"])
        assert df.loc[1, "TEORI"] == 90


# =========================================================
# TEST: normalisasi_result — INI PALING KRITIS
# =========================================================
class TestNormalisasiResult:
    def test_result_lulus_eksplisit(self):
        df = pd.DataFrame({"RESULT": ["Lulus"], "TEORI": [50]})
        df = normalisasi_result(df)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_result_tidak_lulus_eksplisit(self):
        df = pd.DataFrame({"RESULT": ["Tidak Lulus"], "TEORI": [95]})
        df = normalisasi_result(df)
        # RESULT eksplisit "Tidak Lulus" harus menang, TIDAK dicek ulang ke TEORI
        assert df.loc[0, "RESULT_FINAL"] == STATUS_TIDAK_LULUS

    def test_finished_dengan_teori_di_atas_threshold(self):
        df = pd.DataFrame({"RESULT": ["Finished"], "TEORI": [90]})
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_finished_dengan_teori_di_bawah_threshold(self):
        df = pd.DataFrame({"RESULT": ["Finished"], "TEORI": [70]})
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_TIDAK_LULUS

    def test_finished_tepat_di_threshold_dianggap_lulus(self):
        """Edge case: TEORI == threshold (bukan cuma > threshold)."""
        df = pd.DataFrame({"RESULT": ["Finished"], "TEORI": [80]})
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_finished_tapi_teori_kosong(self):
        """Kasus PRAKTEK & TEORI kosong dua-duanya -> tidak boleh dipaksa Tidak Lulus."""
        df = pd.DataFrame({"RESULT": ["Finished"], "TEORI": [np.nan]})
        df = normalisasi_result(df)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP

    def test_result_value_tidak_dikenal(self):
        df = pd.DataFrame({"RESULT": ["Aneh_Value"], "TEORI": [90]})
        df = normalisasi_result(df)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP

    def test_result_kosong(self):
        df = pd.DataFrame({"RESULT": [None], "TEORI": [90]})
        df = normalisasi_result(df)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP

    def test_result_case_insensitive(self):
        """RESULT 'finished' (lowercase) harus tetap dikenali sama seperti 'Finished'."""
        df = pd.DataFrame({"RESULT": ["finished"], "TEORI": [85]})
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_kolom_result_asli_tidak_terhapus(self):
        """Audit trail: kolom RESULT mentah harus tetap ada setelah normalisasi."""
        df = pd.DataFrame({"RESULT": ["Lulus"], "TEORI": [90]})
        df = normalisasi_result(df)
        assert "RESULT" in df.columns
        assert df.loc[0, "RESULT"] == "Lulus"

    def test_custom_threshold(self):
        """Threshold bisa di-override, tidak hardcode ke 80."""
        df = pd.DataFrame({"RESULT": ["Finished"], "TEORI": [75]})
        df_default = normalisasi_result(df.copy(), threshold=80)
        df_custom = normalisasi_result(df.copy(), threshold=70)
        assert df_default.loc[0, "RESULT_FINAL"] == STATUS_TIDAK_LULUS
        assert df_custom.loc[0, "RESULT_FINAL"] == STATUS_LULUS


# =========================================================
# TEST: normalisasi_kategori_kosong
# =========================================================
class TestNormalisasiKategoriKosong:
    def test_nan_diganti_label_default(self, data_mentah):
        df = normalisasi_teks(data_mentah)
        df = normalisasi_kategori_kosong(df)
        assert df["AREA"].isna().sum() == 0
        assert "TIDAK DIKETAHUI" in df["AREA"].values

    def test_label_custom(self):
        df = pd.DataFrame({"AREA": [None, "PLANT A"]})
        df = normalisasi_kategori_kosong(df, kolom_list=["AREA"], label="UNKNOWN")
        assert df.loc[0, "AREA"] == "UNKNOWN"

    def test_kolom_tanpa_nan_tidak_berubah(self):
        df = pd.DataFrame({"AREA": ["PLANT A", "PLANT B"]})
        hasil = normalisasi_kategori_kosong(df, kolom_list=["AREA"])
        pd.testing.assert_series_equal(hasil["AREA"], df["AREA"])


# =========================================================
# TEST: normalisasi_duplikat
# =========================================================
class TestNormalisasiDuplikat:
    def test_duplikat_terhapus(self, data_mentah):
        # Pakai subset eksplisit karena NRP_ID belum ada tanpa melalui normalisasi_nrp.
        # Di pipeline penuh, NRP_ID dibuat oleh normalisasi_nrp sebelum normalisasi_duplikat.
        df, jumlah_dihapus = normalisasi_duplikat(
            data_mentah, subset_kolom=["NRP BARU", "MODUL TRAINING", "TAHUN"]
        )
        assert jumlah_dihapus == 1  # baris index 5 & 6 identik
        assert len(df) == len(data_mentah) - 1

    def test_data_tanpa_duplikat_tidak_berubah(self):
        df = pd.DataFrame({"NRP_ID": ["N1", "N2"], "MODUL TRAINING": ["A", "B"], "TAHUN": [2024, 2024]})
        hasil, jumlah_dihapus = normalisasi_duplikat(df)
        assert jumlah_dihapus == 0
        assert len(hasil) == 2

    def test_kolom_kunci_tidak_lengkap_tidak_error(self):
        """Kalau kolom kunci duplikat tidak ada di df, jangan crash — return apa adanya."""
        df = pd.DataFrame({"KOLOM_LAIN": [1, 2]})
        hasil, jumlah_dihapus = normalisasi_duplikat(df, subset_kolom=["NRP_ID"])
        assert jumlah_dihapus == 0
        assert len(hasil) == 2


# =========================================================
# TEST: jalankan_pipeline_normalisasi (integration test)
# =========================================================
class TestPipelineNormalisasi:
    def test_pipeline_lengkap_tidak_error(self, data_mentah):
        hasil = jalankan_pipeline_normalisasi(data_mentah)
        assert "data" in hasil
        assert "jumlah_duplikat_dihapus" in hasil
        assert "jumlah_job_dibuang" in hasil

    def test_pipeline_hasil_akhir_konsisten(self, data_mentah):
        hasil = jalankan_pipeline_normalisasi(data_mentah)
        df = hasil["data"]

        # Duplikat sudah terhapus (baris 5 & 6 identik)
        assert hasil["jumlah_duplikat_dihapus"] == 1

        # Baris None-JOB (→ TIDAK DIKETAHUI) ikut dibuang oleh filter_job_aktif
        assert hasil["jumlah_job_dibuang"] == 1

        # Total: 7 asli - 1 dedup - 1 job filter = 5
        assert len(df) == 5

        # Semua baris yang tersisa harus memiliki JOB yang valid
        from config.settings import JOB_FILTER_AKTIF
        assert df["JOB"].isin(JOB_FILTER_AKTIF).all()

        # RESULT_FINAL sudah terbentuk untuk semua baris
        assert "RESULT_FINAL" in df.columns
        assert df["RESULT_FINAL"].isna().sum() == 0

        # Tidak ada lagi kategori kosong (NaN) di kolom kategorikal
        assert df["AREA"].isna().sum() == 0

        # START dan END sudah di-drop, digantikan TANGGAL (angka hari)
        assert "START" not in df.columns
        assert "END" not in df.columns
        assert "TANGGAL" in df.columns
        assert df["TANGGAL"].notna().all()  # semua baris harus punya hari

        # NRP_ID sudah terbentuk
        assert "NRP_ID" in df.columns

    def test_pipeline_urutan_transformasi_benar(self, data_mentah):
        """
        Regression test penting:
        1. normalisasi_nilai_teori HARUS jalan SEBELUM normalisasi_result
           supaya 9000 sudah jadi 90 sebelum dicek threshold 80.
        2. RESULT_FINAL sekarang selalu dari TEORI — bukan dari RESULT asli.
        """
        hasil = jalankan_pipeline_normalisasi(data_mentah)
        df = hasil["data"]

        # Baris dengan TEORI awal=9000 (→90.0 setelah normalisasi)
        # harus LULUS karena 90 >= 80 (logika pure TEORI, bukan RESULT asli)
        baris_terkait = df[df["TEORI"] == 90.0]
        assert len(baris_terkait) >= 1, "Baris TEORI=9000 harus menjadi 90 setelah normalisasi"
        assert (baris_terkait["RESULT_FINAL"] == STATUS_LULUS).all()

        # Baris dengan TEORI=60 harus TIDAK LULUS, meski RESULT aslinya "Tidak Lulus"
        baris_tidak_lulus = df[df["TEORI"] == 60.0]
        assert len(baris_tidak_lulus) >= 1
        assert (baris_tidak_lulus["RESULT_FINAL"] == STATUS_TIDAK_LULUS).all()

        # Baris dengan TEORI=NaN harus DATA TIDAK LENGKAP
        baris_nan = df[df["TEORI"].isna()]
        assert (baris_nan["RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP).all()


# =========================================================
# TEST: normalisasi_nrp
# =========================================================
class TestNormalisasiNrp:
    def test_nrp_baru_terisi_dipakai(self):
        df = pd.DataFrame({"NRP LAMA": ["L1"], "NRP BARU": ["B1"]})
        hasil = normalisasi_nrp(df)
        assert hasil.loc[0, "NRP_ID"] == "B1"

    def test_nrp_baru_kosong_fallback_ke_nrp_lama(self):
        df = pd.DataFrame({"NRP LAMA": ["L1"], "NRP BARU": [None]})
        hasil = normalisasi_nrp(df)
        assert hasil.loc[0, "NRP_ID"] == "L1"

    def test_nrp_baru_nan_string_fallback_ke_nrp_lama(self):
        """Setelah normalisasi_teks, NaN jadi string 'NAN' — harus tetap fallback."""
        df = pd.DataFrame({"NRP LAMA": ["L2"], "NRP BARU": ["NAN"]})
        hasil = normalisasi_nrp(df)
        assert hasil.loc[0, "NRP_ID"] == "L2"

    def test_tanpa_kolom_nrp_baru_pakai_nrp_lama(self):
        df = pd.DataFrame({"NRP LAMA": ["L3"]})
        hasil = normalisasi_nrp(df)
        assert hasil.loc[0, "NRP_ID"] == "L3"

    def test_tidak_mengubah_dataframe_asli(self):
        df = pd.DataFrame({"NRP LAMA": ["L1"], "NRP BARU": [None]})
        normalisasi_nrp(df)
        assert "NRP_ID" not in df.columns


# =========================================================
# TEST: normalisasi_nilai_teori
# =========================================================
class TestNormalisasiNilaiTeori:
    def test_nilai_normal_tidak_berubah(self):
        """Nilai di rentang 10-100 harus apa adanya."""
        df = pd.DataFrame({"TEORI": [83.0, 75.0, 100.0, 10.0]})
        hasil = normalisasi_nilai_teori(df)
        assert hasil.loc[0, "TEORI"] == 83.0
        assert hasil.loc[1, "TEORI"] == 75.0
        assert hasil.loc[2, "TEORI"] == 100.0
        assert hasil.loc[3, "TEORI"] == 10.0

    def test_nilai_di_atas_100_dibagi_100(self):
        """9000 → 90.0 (kemungkinan input desimal tanpa titik)."""
        df = pd.DataFrame({"TEORI": [9000.0, 8500.0]})
        hasil = normalisasi_nilai_teori(df)
        assert hasil.loc[0, "TEORI"] == 90.0
        assert hasil.loc[1, "TEORI"] == 85.0

    def test_nilai_di_bawah_10_dikali_10(self):
        """8 → 80 (kemungkinan digit terakhir terlewat saat input)."""
        df = pd.DataFrame({"TEORI": [8.0, 7.0, 9.0]})
        hasil = normalisasi_nilai_teori(df)
        assert hasil.loc[0, "TEORI"] == 80.0
        assert hasil.loc[1, "TEORI"] == 70.0
        assert hasil.loc[2, "TEORI"] == 90.0

    def test_nilai_nan_tetap_nan(self):
        df = pd.DataFrame({"TEORI": [np.nan]})
        hasil = normalisasi_nilai_teori(df)
        assert pd.isna(hasil.loc[0, "TEORI"])

    def test_nilai_nol_atau_negatif_jadi_nan(self):
        df = pd.DataFrame({"TEORI": [0.0, -5.0]})
        hasil = normalisasi_nilai_teori(df)
        assert pd.isna(hasil.loc[0, "TEORI"])
        assert pd.isna(hasil.loc[1, "TEORI"])

    def test_teori_9000_lulus_setelah_normalisasi(self):
        """End-to-end: 9000 → 90 → >= 80 → LULUS (bukan TIDAK LULUS)."""
        df = pd.DataFrame({"TEORI": [9000.0], "RESULT": ["Finished"]})
        df = normalisasi_nilai_teori(df)
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_teori_8_lulus_setelah_normalisasi(self):
        """End-to-end: 8 → 80 → tepat 80 → LULUS."""
        df = pd.DataFrame({"TEORI": [8.0], "RESULT": ["Finished"]})
        df = normalisasi_nilai_teori(df)
        df = normalisasi_result(df, threshold=80)
        assert df.loc[0, "RESULT_FINAL"] == STATUS_LULUS

    def test_tidak_mengubah_dataframe_asli(self):
        df = pd.DataFrame({"TEORI": [9000.0]})
        normalisasi_nilai_teori(df)
        assert df.loc[0, "TEORI"] == 9000.0


# =========================================================
# TEST: filter_job_aktif
# =========================================================
class TestFilterJobAktif:
    @pytest.fixture
    def df_job(self):
        return pd.DataFrame({
            "NRP_ID": ["N1", "N2", "N3", "N4", "N5"],
            # Perhatikan: 'CPO' bukan 'COP' — sesuai data asli PT United Tractors
            "JOB": ["CPO", "PTO", "ADM_SERVICE", "OPERATOR", "TIDAK DIKETAHUI"],
            "RESULT_FINAL": [STATUS_LULUS] * 5,
        })

    def test_hanya_job_aktif_yang_tersisa(self, df_job):
        hasil, jumlah_dibuang = filter_job_aktif(df_job)
        assert set(hasil["JOB"]) == {"CPO", "PTO", "ADM_SERVICE"}
        assert jumlah_dibuang == 2  # OPERATOR & TIDAK DIKETAHUI dibuang

    def test_jumlah_dibuang_benar(self, df_job):
        _, jumlah_dibuang = filter_job_aktif(df_job)
        assert jumlah_dibuang == 2

    def test_semua_job_valid_tidak_ada_yang_dibuang(self):
        df = pd.DataFrame({"JOB": ["CPO", "PTO", "ADM_SERVICE"]})
        hasil, jumlah_dibuang = filter_job_aktif(df)
        assert len(hasil) == 3
        assert jumlah_dibuang == 0

    def test_custom_job_list(self, df_job):
        """Job list bisa di-override via parameter."""
        hasil, jumlah_dibuang = filter_job_aktif(df_job, job_list=["CPO"])
        assert len(hasil) == 1
        assert hasil.iloc[0]["JOB"] == "CPO"

    def test_tanpa_kolom_job_tidak_error(self):
        df = pd.DataFrame({"KOLOM_LAIN": [1, 2]})
        hasil, jumlah_dibuang = filter_job_aktif(df)
        assert jumlah_dibuang == 0
        assert len(hasil) == 2

    def test_tidak_mengubah_dataframe_asli(self, df_job):
        salinan = df_job.copy()
        filter_job_aktif(df_job)
        pd.testing.assert_frame_equal(df_job, salinan)