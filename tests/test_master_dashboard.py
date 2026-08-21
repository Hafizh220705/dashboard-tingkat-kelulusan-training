import pandas as pd

from src.components.master_dashboard import (
    _angka,
    _bar_horizontal,
    _distribusi,
    _insight,
    _interval,
    terapkan_filter_master,
)


def test_angka_menerima_satuan_dan_koma_desimal():
    hasil = _angka(pd.Series(["32 Tahun", "5,5", None, "tidak diketahui"]))

    assert hasil.iloc[0] == 32
    assert hasil.iloc[1] == 5.5
    assert hasil.iloc[2:].isna().all()


def test_distribusi_menggabungkan_nilai_kosong():
    df = pd.DataFrame({"Plant": ["Jakarta", "Jakarta", None, " "]})

    hasil = _distribusi(df, "Plant")

    assert hasil.set_index("Plant").loc["Jakarta", "Jumlah"] == 2
    assert hasil.set_index("Plant").loc["Tidak diketahui", "Jumlah"] == 2


def test_insight_menampilkan_plant_dan_divisi_terbesar():
    df = pd.DataFrame(
        {
            "Plant": ["A", "A", "B"],
            "Div (Penempatan Saat Ini)": ["OPS", "OPS", "HR"],
        }
    )

    hasil = _insight(df)

    assert "Plant terbesar **A**" in hasil
    assert "Divisi terbesar **OPS**" in hasil


def test_bar_memakai_warna_berbeda_per_kategori():
    fig = _bar_horizontal(pd.DataFrame({"Plant": ["A", "B", "C"]}), "Plant")

    warna = [trace.marker.color for trace in fig.data]
    assert len(set(warna)) == 3


def test_interval_masa_kerja_sesuai_batas():
    hasil = _interval(
        pd.Series([0, 2, 3, 5, 6, 10, 11]),
        [0, 2, 5, 10, float("inf")],
        ["0–2", ">2–5", ">5–10", ">10"],
    )

    assert hasil.astype("string").tolist() == ["0–2", "0–2", ">2–5", ">2–5", ">5–10", ">5–10", ">10"]


def test_visual_masa_kerja_memakai_dua_kelompok():
    from src.components.master_dashboard import _bar_interval

    fig = _bar_interval(pd.Series([1, 2, 3]), "masa_kerja")
    label = {trace.name for trace in fig.data}

    assert label == {"< 2 tahun", "≥ 2 tahun"}


def test_filter_master_menggabungkan_beberapa_dimensi():
    df = pd.DataFrame(
        {
            "Jabatan": ["A", "A", "B"],
            "Gender": ["L", "P", "L"],
            "Plant": ["X", "X", "Y"],
        }
    )

    hasil = terapkan_filter_master(df, {"Jabatan": ["A"], "Gender": ["P"]})

    assert len(hasil) == 1
    assert hasil.iloc[0]["Gender"] == "P"
