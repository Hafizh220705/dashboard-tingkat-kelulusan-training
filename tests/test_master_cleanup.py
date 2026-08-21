import pandas as pd

from src.data.loader import (
    JENIS_DATA_MASTER,
    hapus_kolom_master_tidak_digunakan,
    tentukan_jenis_data,
)


def test_hapus_kolom_periode_resign_dan_placeholder():
    df = pd.DataFrame({
        "ID": [1],
        "Nama Lengkap": ["Contoh"],
        "Dec-25": ["x"],
        "12/25 RESIGN": [None],
        "01": ["x"],
        "04\nRESIGN": [None],
        "07\r\nRESIGN": [None],
        "08": ["x"],
        "Column1": [None],
        "Column2": [None],
        "Column3": [None],
        "month": [8],
        "year": [2026],
    })

    hasil = hapus_kolom_master_tidak_digunakan(df)

    assert list(hasil.columns) == ["ID", "Nama Lengkap", "month", "year"]


def test_seluruh_kolom_master_yang_tidak_dipakai_dihapus():
    kolom_dihapus = [
        "Dec-25",
        "12/25 RESIGN",
        "01",
        "01 RESIGN",
        "02",
        "02 RESIGN",
        "03",
        "03 RESIGN",
        "04",
        "04\nRESIGN",
        "05",
        "05\nRESIGN",
        "06",
        "06\nRESIGN",
        "07",
        "07\nRESIGN",
        "08",
        "Column1",
        "Column2",
        "Column3",
    ]
    kolom_dipertahankan = [
        "ID",
        "Nama Lengkap",
        "NRP",
        "Jabatan",
        "Email Kantor\u00a0",
        "Nomor Handphone",
        "Plant",
        "Div (Penempatan Saat Ini)",
        "month",
        "year",
    ]
    df = pd.DataFrame(
        {kolom: [None] for kolom in kolom_dipertahankan + kolom_dihapus}
    )

    hasil = hapus_kolom_master_tidak_digunakan(df)

    assert list(hasil.columns) == kolom_dipertahankan


def test_tidak_memutasi_dataframe_asli():
    df = pd.DataFrame({"ID": [1], "01": ["x"]})
    hapus_kolom_master_tidak_digunakan(df)
    assert "01" in df.columns


def test_schema_master_employee_dikenali():
    df = pd.DataFrame(
        {"ID": [1], "Nama Lengkap": ["Contoh"], "NRP": [12345], "Plant": ["A"]}
    )

    assert tentukan_jenis_data(df) == JENIS_DATA_MASTER
