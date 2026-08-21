"""
Unit test untuk src/components/sidebar_filter.py.

Catatan cakupan test:
- `terapkan_filter()` dan `FilterState` di-test penuh karena murni logic,
  tidak bergantung Streamlit.
- `render_sidebar_filters()` SENGAJA TIDAK di-unit-test di sini karena
  isinya murni pemanggilan widget Streamlit (st.sidebar.multiselect, dst.)
  -- ini alasan utama kenapa logic filtering dipisah ke `terapkan_filter()`
  di awal: supaya bagian yang paling penting untuk benar (logic filter)
  tetap testable, sementara bagian UI-nya cukup divalidasi manual/visual.

Jalankan dengan:
    pytest tests/test_sidebar_filter.py -v
"""

import pandas as pd
import pytest

import src.components.sidebar_filter as sidebar_filter_module
from src.components.sidebar_filter import FilterState, terapkan_filter
from config.settings import LEVEL_PER_EMPLOYEE, LEVEL_PER_PARTISIPASI


# =========================================================
# FIXTURE
# =========================================================
@pytest.fixture
def data_dummy():
    return pd.DataFrame({
        "NRP BARU": ["N1", "N2", "N3", "N4", "N5"],
        "AREA": ["PLANT A", "PLANT B", "PLANT A", "PLANT C", "PLANT B"],
        "JOB": ["OPERATOR", "MEKANIK", "OPERATOR", "MEKANIK", "OPERATOR"],
        "TAHUN": [2024, 2024, 2023, 2025, 2024],
        "MODUL TRAINING": ["SAFETY", "SAFETY", "TEKNIS", "TEKNIS", "SAFETY"],
        "RESULT_FINAL": ["LULUS", "TIDAK LULUS", "LULUS", "TIDAK LULUS", "LULUS"],
    })


# =========================================================
# TEST: FilterState (dataclass default)
# =========================================================
class TestFilterState:
    def test_default_semua_filter_kosong(self):
        """Default FilterState harus 'tidak memfilter apapun' (list kosong)."""
        state = FilterState()
        assert state.area == []
        assert state.job == []
        assert state.tahun == []
        assert state.modul_training == []
        assert state.status_kelulusan == []
        assert state.atribut_master == {}

    def test_default_level_agregasi_per_partisipasi(self):
        state = FilterState()
        assert state.level_agregasi == LEVEL_PER_PARTISIPASI

    def test_setiap_instance_punya_list_independen(self):
        """
        Regression test penting untuk dataclass dengan default list:
        pastikan mutable default (field(default_factory=list)) tidak
        ke-share antar instance -- kalau salah implementasi (misal pakai
        `area: list = []` langsung tanpa default_factory), semua instance
        bakal 'nempel' ke list yang sama.
        """
        state_1 = FilterState()
        state_2 = FilterState()
        state_1.area.append("PLANT A")
        state_1.atribut_master["Gender"] = ["L"]
        assert state_2.area == []
        assert state_2.atribut_master == {}

    def test_bisa_diisi_manual(self):
        state = FilterState(area=["PLANT A"], job=["OPERATOR"], tahun=[2024])
        assert state.area == ["PLANT A"]
        assert state.job == ["OPERATOR"]
        assert state.tahun == [2024]


# =========================================================
# TEST: terapkan_filter — kondisi kosong (tidak ada filter aktif)
# =========================================================
class TestTerapkanFilterKosong:
    def test_filter_semua_kosong_return_semua_baris(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState())
        assert len(hasil) == len(data_dummy)

    def test_tidak_memutasi_dataframe_asli(self, data_dummy):
        salinan = data_dummy.copy()
        terapkan_filter(data_dummy, FilterState(area=["PLANT A"]))
        pd.testing.assert_frame_equal(data_dummy, salinan)


# =========================================================
# TEST: terapkan_filter — filter tunggal per kolom
# =========================================================
class TestTerapkanFilterTunggal:
    def test_filter_area_tunggal(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState(area=["PLANT A"]))
        assert len(hasil) == 2
        assert set(hasil["AREA"]) == {"PLANT A"}

    def test_filter_area_multi_value(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState(area=["PLANT A", "PLANT B"]))
        assert len(hasil) == 4
        assert set(hasil["AREA"]) == {"PLANT A", "PLANT B"}

    def test_filter_job(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState(job=["OPERATOR"]))
        assert len(hasil) == 3
        assert set(hasil["JOB"]) == {"OPERATOR"}

    def test_filter_tahun(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState(tahun=[2024]))
        assert len(hasil) == 3

    def test_filter_modul_training(self, data_dummy):
        hasil = terapkan_filter(data_dummy, FilterState(modul_training=["TEKNIS"]))
        assert len(hasil) == 2
        assert set(hasil["MODUL TRAINING"]) == {"TEKNIS"}

    def test_filter_status_kelulusan(self, data_dummy):
        hasil = terapkan_filter(
            data_dummy,
            FilterState(status_kelulusan=["TIDAK LULUS"]),
        )
        assert len(hasil) == 2
        assert set(hasil["RESULT_FINAL"]) == {"TIDAK LULUS"}

    def test_filter_dengan_nilai_tidak_ada_di_data(self, data_dummy):
        """Filter dengan value yang tidak match apapun harus return 0 baris, bukan error."""
        hasil = terapkan_filter(data_dummy, FilterState(area=["PLANT Z"]))
        assert len(hasil) == 0


# =========================================================
# TEST: terapkan_filter — kombinasi banyak filter sekaligus
# =========================================================
class TestTerapkanFilterKombinasi:
    def test_kombinasi_area_dan_job(self, data_dummy):
        hasil = terapkan_filter(
            data_dummy, FilterState(area=["PLANT A"], job=["OPERATOR"])
        )
        # N1 (Plant A, Operator) dan N3 (Plant A, Operator) match
        assert len(hasil) == 2
        assert set(hasil["NRP BARU"]) == {"N1", "N3"}

    def test_kombinasi_semua_filter_sekaligus(self, data_dummy):
        hasil = terapkan_filter(
            data_dummy,
            FilterState(
                area=["PLANT A"],
                job=["OPERATOR"],
                tahun=[2024],
                modul_training=["SAFETY"],
            ),
        )
        # Hanya N1 yang match keempat kriteria sekaligus
        assert len(hasil) == 1
        assert hasil.iloc[0]["NRP BARU"] == "N1"

    def test_kombinasi_filter_saling_eksklusif_hasilnya_kosong(self, data_dummy):
        """
        Area PLANT A tidak pernah punya JOB=MEKANIK di data dummy ini
        -> kombinasi filter valid tapi hasilnya 0 baris (bukan error).
        """
        hasil = terapkan_filter(
            data_dummy, FilterState(area=["PLANT A"], job=["MEKANIK"])
        )
        assert len(hasil) == 0

    def test_filter_kombinasi_urutan_tidak_berpengaruh(self, data_dummy):
        """
        Sanity check: hasil filter tidak boleh berubah tergantung urutan
        field mana yang diisi duluan di FilterState (karena implementasi
        terapkan_filter menerapkan filter secara berurutan/chained).
        """
        state_a = FilterState(area=["PLANT A"], tahun=[2023])
        state_b = FilterState(tahun=[2023], area=["PLANT A"])
        hasil_a = terapkan_filter(data_dummy, state_a)
        hasil_b = terapkan_filter(data_dummy, state_b)
        pd.testing.assert_frame_equal(
            hasil_a.reset_index(drop=True), hasil_b.reset_index(drop=True)
        )

    def test_filter_atribut_master_dapat_dikombinasikan(self, data_dummy):
        data_dummy = data_dummy.assign(
            Gender=["L", "P", "L", "P", "L"],
            **{"Div (Penempatan Saat Ini)": ["OPS", "HR", "OPS", "HR", "OPS"]},
        )
        state = FilterState(
            status_kelulusan=["LULUS"],
            atribut_master={
                "Gender": ["L"],
                "Div (Penempatan Saat Ini)": ["OPS"],
            },
        )

        hasil = terapkan_filter(data_dummy, state)

        assert len(hasil) == 3
        assert set(hasil["Gender"]) == {"L"}
        assert set(hasil["Div (Penempatan Saat Ini)"]) == {"OPS"}


def test_renderer_sidebar_menampilkan_seluruh_filter_relevan(monkeypatch):
    class SidebarSpy:
        def __init__(self):
            self.label_multiselect = []

        def header(self, *_args, **_kwargs):
            pass

        def caption(self, *_args, **_kwargs):
            pass

        def markdown(self, *_args, **_kwargs):
            pass

        def button(self, *_args, **_kwargs):
            return False

        def multiselect(self, label, _options, **_kwargs):
            self.label_multiselect.append(label)
            return []

    sidebar_spy = SidebarSpy()
    monkeypatch.setattr(sidebar_filter_module.st, "sidebar", sidebar_spy)
    df = pd.DataFrame(
        {
            "TAHUN": [2026],
            "AREA": ["Jakarta"],
            "JOB": ["Operator"],
            "MODUL TRAINING": ["Safety"],
            "RESULT_FINAL": ["LULUS"],
            "Gender": ["L"],
            "Div (Penempatan Saat Ini)": ["OPS"],
        }
    )

    sidebar_filter_module.render_sidebar_filters(df)

    assert sidebar_spy.label_multiselect == [
        "Tahun Training",
        "Area / Plant",
        "Jabatan / Job",
        "Training / Modul",
        "Status Kelulusan",
        "Gender",
        "Divisi",
    ]
