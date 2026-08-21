"""Test untuk konversi CSV dan penggabungan file Excel."""

from io import BytesIO
from zipfile import ZipFile

import pandas as pd
import pytest

from config.settings import (
    KOLOM_WAJIB_LAPORAN_TRAINING,
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)
from src.data.file_tools import (
    PengolahanFileError,
    baca_csv_umum,
    gabungkan_excel_ke_bytes,
    gabungkan_file_excel,
    hubungkan_laporan_dengan_master,
    konversi_banyak_csv_ke_zip,
    konversi_csv_ke_excel,
    siapkan_laporan_training,
)


def _file_bytes(data: bytes, nama: str) -> BytesIO:
    file_obj = BytesIO(data)
    file_obj.name = nama
    return file_obj


def _file_excel(df: pd.DataFrame, nama: str) -> BytesIO:
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    return _file_bytes(output.getvalue(), nama)


def _laporan_training(nrp: list, grade: list) -> pd.DataFrame:
    jumlah_baris = len(nrp)
    data = {
        kolom: [None] * jumlah_baris
        for kolom in KOLOM_WAJIB_LAPORAN_TRAINING
    }
    data["First name"] = nrp
    data["Grade/100.00"] = grade
    return pd.DataFrame(data)


def test_baca_csv_mendeteksi_titik_koma_dan_encoding_utf8():
    csv_file = _file_bytes("NAMA;NILAI\nAndi;90\nSiti;85".encode(), "nilai.csv")

    hasil = baca_csv_umum(csv_file)

    assert list(hasil.columns) == ["NAMA", "NILAI"]
    assert hasil.to_dict("records") == [
        {"NAMA": "Andi", "NILAI": 90},
        {"NAMA": "Siti", "NILAI": 85},
    ]


def test_konversi_csv_menghasilkan_workbook_valid():
    csv_file = _file_bytes(b"NAMA,NILAI\nAndi,90", "nilai.csv")

    df, hasil_excel = konversi_csv_ke_excel(csv_file)
    hasil_baca_ulang = pd.read_excel(BytesIO(hasil_excel), engine="openpyxl")

    pd.testing.assert_frame_equal(hasil_baca_ulang, df)


def test_csv_kosong_ditolak():
    with pytest.raises(PengolahanFileError, match="kosong"):
        baca_csv_umum(_file_bytes(b"", "kosong.csv"))


def test_konversi_banyak_csv_menghasilkan_zip_berisi_semua_excel():
    file_a = _file_bytes(b"ID,NAMA\n1,Andi", "pegawai.csv")
    file_b = _file_bytes(b"ID;NILAI\n2;90", "nilai.csv")

    ringkasan, hasil_zip = konversi_banyak_csv_ke_zip([file_a, file_b])

    assert [item.nama_file_hasil for item in ringkasan] == [
        "pegawai.xlsx",
        "nilai.xlsx",
    ]
    with ZipFile(BytesIO(hasil_zip)) as arsip:
        assert arsip.namelist() == ["pegawai.xlsx", "nilai.xlsx"]
        hasil_pegawai = pd.read_excel(BytesIO(arsip.read("pegawai.xlsx")))
        hasil_nilai = pd.read_excel(BytesIO(arsip.read("nilai.xlsx")))

    assert hasil_pegawai.loc[0, "NAMA"] == "Andi"
    assert hasil_nilai.loc[0, "NILAI"] == 90


def test_konversi_batch_membuat_nama_unik_untuk_file_duplikat():
    file_a = _file_bytes(b"ID\n1", "data.csv")
    file_b = _file_bytes(b"ID\n2", "DATA.csv")

    ringkasan, hasil_zip = konversi_banyak_csv_ke_zip([file_a, file_b])

    assert [item.nama_file_hasil for item in ringkasan] == [
        "data.xlsx",
        "DATA_2.xlsx",
    ]
    with ZipFile(BytesIO(hasil_zip)) as arsip:
        assert len(arsip.namelist()) == 2


def test_gabung_excel_mengikuti_urutan_dan_union_kolom():
    file_a = _file_excel(
        pd.DataFrame({"ID": [1, 2], "NAMA": ["A", "B"]}),
        "a.xlsx",
    )
    file_b = _file_excel(
        pd.DataFrame({"ID": [3], "AREA": ["Jakarta"]}),
        "b.xlsx",
    )

    hasil = gabungkan_file_excel([file_a, file_b])

    assert list(hasil.columns) == ["ID", "NAMA", "AREA"]
    assert hasil["ID"].tolist() == [1, 2, 3]
    assert pd.isna(hasil.loc[2, "NAMA"])
    assert hasil.loc[2, "AREA"] == "Jakarta"


def test_gabung_excel_dapat_menambahkan_nama_sumber():
    file_a = _file_excel(pd.DataFrame({"ID": [1]}), "a.xlsx")
    file_b = _file_excel(pd.DataFrame({"ID": [2]}), "b.xlsx")

    hasil = gabungkan_file_excel(
        [file_a, file_b],
        tambah_sumber_file=True,
    )

    assert hasil["SUMBER_FILE"].tolist() == ["a.xlsx", "b.xlsx"]


def test_gabung_excel_tidak_menimpa_kolom_sumber_yang_sudah_ada():
    file_a = _file_excel(
        pd.DataFrame({"ID": [1], "SUMBER_FILE": ["asli"]}),
        "a.xlsx",
    )
    file_b = _file_excel(pd.DataFrame({"ID": [2]}), "b.xlsx")

    hasil = gabungkan_file_excel(
        [file_a, file_b],
        tambah_sumber_file=True,
    )

    assert "SUMBER_FILE_2" in hasil.columns
    assert hasil["SUMBER_FILE_2"].tolist() == ["a.xlsx", "b.xlsx"]
    assert hasil.loc[0, "SUMBER_FILE"] == "asli"


def test_gabung_excel_minimal_dua_file():
    satu_file = _file_excel(pd.DataFrame({"ID": [1]}), "satu.xlsx")

    with pytest.raises(PengolahanFileError, match="minimal dua"):
        gabungkan_file_excel([satu_file])


def test_hasil_gabung_dapat_diunduh_dan_dibaca_ulang():
    file_a = _file_excel(pd.DataFrame({"ID": [1]}), "a.xlsx")
    file_b = _file_excel(pd.DataFrame({"ID": [2]}), "b.xlsx")

    df, hasil_excel = gabungkan_excel_ke_bytes([file_a, file_b])
    hasil_baca_ulang = pd.read_excel(BytesIO(hasil_excel), engine="openpyxl")

    pd.testing.assert_frame_equal(hasil_baca_ulang, df)


def test_laporan_training_memakai_first_name_sebagai_nrp_dan_grade_sebagai_status():
    laporan = _laporan_training(
        ["00123", 456.0, "NRP-7", None, "008"],
        [80, 79.99, "85,5", "-", None],
    )

    hasil = siapkan_laporan_training(laporan)

    assert hasil["NRP_ID"].tolist()[:3] == ["123", "456", "NRP-7"]
    assert pd.isna(hasil.loc[3, "NRP_ID"])
    assert hasil["RESULT_FINAL"].tolist() == [
        STATUS_LULUS,
        STATUS_TIDAK_LULUS,
        STATUS_LULUS,
        STATUS_DATA_TIDAK_LENGKAP,
        STATUS_DATA_TIDAK_LENGKAP,
    ]
    assert hasil.loc[2, "NILAI_FINAL"] == 85.5


def test_laporan_training_ditolak_jika_template_tidak_lengkap():
    laporan = _laporan_training(["123"], [90]).drop(columns=["Q. 5 /20.00"])

    with pytest.raises(PengolahanFileError, match="Q. 5 /20.00"):
        siapkan_laporan_training(laporan)


def test_setiap_file_merge_divalidasi_terhadap_template_training():
    file_valid = _file_excel(_laporan_training(["123"], [90]), "valid.xlsx")
    file_tidak_valid = _file_excel(
        _laporan_training(["456"], [70]).drop(columns=["Duration"]),
        "tidak_valid.xlsx",
    )

    with pytest.raises(PengolahanFileError, match="Duration"):
        gabungkan_file_excel(
            [file_valid, file_tidak_valid],
            kolom_wajib=KOLOM_WAJIB_LAPORAN_TRAINING,
        )


def test_laporan_training_dihubungkan_ke_master_melalui_nrp_tanpa_duplikasi():
    training = siapkan_laporan_training(
        _laporan_training(["00123", "456", "999"], [90, 70, 80])
    )
    master = pd.DataFrame(
        {
            "ID": [1, 2, 3],
            "Nama Lengkap": ["Andi", "Andi Duplikat", "Siti"],
            "NRP": [123, "00123", "000456"],
            "Plant": ["A", "B", "C"],
        }
    )

    hasil, ringkasan = hubungkan_laporan_dengan_master(training, master)

    assert len(hasil) == len(training)
    assert hasil.loc[0, "Nama Lengkap"] == "Andi"
    assert hasil.loc[1, "Nama Lengkap"] == "Siti"
    assert pd.isna(hasil.loc[2, "Nama Lengkap"])
    assert ringkasan.jumlah_cocok == 2
    assert ringkasan.jumlah_tidak_cocok == 1
    assert ringkasan.jumlah_duplikat_master_dihapus == 1
