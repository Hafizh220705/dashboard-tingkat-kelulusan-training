"""
Modul untuk memuat (load) file data training yang diupload user.
Tanggung jawab modul ini HANYA soal I/O (baca file) & validasi struktur
kolom — TIDAK termasuk logic normalisasi/pembersihan isi data
(itu tanggung jawab `src/data/normalizer.py`).
"""

import pandas as pd

from config.settings import (
    KOLOM_WAJIB,
    KOLOM_WAJIB_LAPORAN_TRAINING,
    KOLOM_WAJIB_MASTER,
)

JENIS_DATA_TRAINING = "training"
JENIS_DATA_MASTER = "master"
JENIS_DATA_LAPORAN_TRAINING = "laporan_training"

BARIS_MAKS_SCAN_HEADER = 15  # cari baris header di antara 15 baris pertama

# Kolom historis/placeholder pada master employee yang tidak dipakai dashboard.
# Nama header dinormalisasi dulu agar variasi line break seperti "04\nRESIGN"
# tetap dikenali sebagai "04 RESIGN".
KOLOM_MASTER_DIHAPUS = {
    "DEC-25",
    "12/25 RESIGN",
    "01",
    "01 RESIGN",
    "02",
    "02 RESIGN",
    "03",
    "03 RESIGN",
    "04",
    "04 RESIGN",
    "05",
    "05 RESIGN",
    "06",
    "06 RESIGN",
    "07",
    "07 RESIGN",
    "08",
    "COLUMN1",
    "COLUMN2",
    "COLUMN3",
}

class FileFormatError(Exception):
    """Exception khusus saat file gagal dibaca atau formatnya tidak didukung."""
    pass

class KolomHilangError(Exception):
    """Exception khusus saat kolom wajib tidak ditemukan di file."""

    def __init__(self, kolom_hilang: list):
        self.kolom_hilang = kolom_hilang
        pesan = (
            "File tidak memiliki kolom wajib berikut: "
            f"{', '.join(kolom_hilang)}"
        )
        super().__init__(pesan)

def bersihkan_nama_kolom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bersihkan nama kolom dari whitespace berlebih di awal/akhir.
    Tidak mengubah huruf besar/kecil supaya tetap cocok dengan
    KOLOM_WAJIB di config/settings.py (yang pakai UPPERCASE).
    """
    df = df.copy()
    df.columns = [" ".join(str(kolom).split()) for kolom in df.columns]
    return df


def hapus_kolom_master_tidak_digunakan(df: pd.DataFrame) -> pd.DataFrame:
    """Hapus kolom periode resign dan placeholder dari master dataset.

    Pencocokan tidak sensitif huruf besar/kecil dan whitespace, sehingga
    header Excel yang mengandung line break tetap terhapus dengan benar.
    """
    df = df.copy()
    kolom_dihapus = [
        kolom for kolom in df.columns
        if " ".join(str(kolom).split()).upper() in KOLOM_MASTER_DIHAPUS
    ]
    return df.drop(columns=kolom_dihapus, errors="ignore")

def deteksi_baris_header(preview_df: pd.DataFrame, kolom_wajib: list = None) -> int:
    """
    Cari baris mana yang merupakan header sungguhan, dengan cara scan
    beberapa baris pertama dan cari baris yang isinya paling banyak
    cocok dengan nama-nama kolom wajib.

    Diperlukan karena file sumber sering punya baris metadata di atas
    header asli (contoh nyata: baris "UPDATE :", tanggal, jam update,
    baris kosong -- baru setelah itu baris header sungguhan).

    Parameters
    ----------
    preview_df : pd.DataFrame
        Hasil baca file TANPA header (header=None), beberapa baris awal saja.
    kolom_wajib : list, optional
        Default pakai KOLOM_WAJIB dari config/settings.py.

    Returns
    -------
    int
        Index baris (0-based) yang terdeteksi sebagai header.
        Fallback ke 0 (baris pertama) kalau tidak ada baris yang cocok
        -- supaya perilaku tetap seperti sebelumnya untuk file yang
        memang headernya di baris pertama.
    """
    kandidat_schema = [kolom_wajib] if kolom_wajib else [
        KOLOM_WAJIB,
        KOLOM_WAJIB_MASTER,
        KOLOM_WAJIB_LAPORAN_TRAINING,
    ]

    for idx in range(len(preview_df)):
        nilai_baris = {
            " ".join(str(nilai).split()).upper()
            for nilai in preview_df.iloc[idx].tolist()
        }
        for schema in kandidat_schema:
            ambang_minimal_cocok = max(2, len(schema) // 2)
            jumlah_cocok = sum(
                1 for kolom in schema if kolom.upper() in nilai_baris
            )
            if jumlah_cocok >= ambang_minimal_cocok:
                return idx

    return 0

def baca_file(uploaded_file) -> pd.DataFrame:
    """
    Baca file upload (.xlsx atau .csv) jadi DataFrame mentah.

    Otomatis mendeteksi baris header yang sebenarnya (lihat
    `deteksi_baris_header()`), jadi tidak selalu asumsi baris pertama
    file adalah header.

    Parameters
    ----------
    uploaded_file : file-like object
        Objek file dari st.file_uploader (punya atribut .name).

    Returns
    -------
    pd.DataFrame
        Data mentah, kolom sudah dibersihkan namanya.

    Raises
    ------
    FileFormatError
        Jika file gagal dibaca atau ekstensi tidak didukung.
    """
    nama_file = uploaded_file.name.lower()

    try:
        if nama_file.endswith(".csv"):
            preview = pd.read_csv(uploaded_file, header=None, nrows=BARIS_MAKS_SCAN_HEADER)
            idx_header = deteksi_baris_header(preview)
            uploaded_file.seek(0)  # reset posisi file setelah dibaca untuk preview
            df = pd.read_csv(uploaded_file, header=idx_header)

        elif nama_file.endswith((".xlsx", ".xls")):
            preview = pd.read_excel(uploaded_file, header=None, nrows=BARIS_MAKS_SCAN_HEADER)
            idx_header = deteksi_baris_header(preview)
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, header=idx_header)

        else:
            raise FileFormatError(
                f"Format file '{uploaded_file.name}' tidak didukung. "
                "Gunakan file .xlsx atau .csv."
            )
    except FileFormatError:
        raise
    except Exception as e:
        raise FileFormatError(f"Gagal membaca file '{uploaded_file.name}': {e}")

    df = bersihkan_nama_kolom(df)
    df = hapus_kolom_master_tidak_digunakan(df)
    return df

def validasi_kolom_wajib(df: pd.DataFrame, kolom_wajib: list = None) -> list:
    """
    Cek kolom wajib yang hilang dari DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
    kolom_wajib : list, optional
        Default pakai KOLOM_WAJIB dari config/settings.py.

    Returns
    -------
    list
        Daftar nama kolom yang hilang. List kosong berarti semua kolom lengkap.
    """
    if kolom_wajib is None:
        kolom_wajib = KOLOM_WAJIB
    return [kolom for kolom in kolom_wajib if kolom not in df.columns]


def tentukan_jenis_data(df: pd.DataFrame) -> str | None:
    """Kenali training lama, laporan nilai training, atau master employee."""
    kolom = {str(nama).upper() for nama in df.columns}
    if all(nama.upper() in kolom for nama in KOLOM_WAJIB):
        return JENIS_DATA_TRAINING
    if all(nama.upper() in kolom for nama in KOLOM_WAJIB_MASTER):
        return JENIS_DATA_MASTER
    if all(nama.upper() in kolom for nama in KOLOM_WAJIB_LAPORAN_TRAINING):
        return JENIS_DATA_LAPORAN_TRAINING
    return None

def muat_dan_validasi(uploaded_file) -> pd.DataFrame:
    """
    Fungsi utama yang dipanggil dari app.py / komponen lain.
    Menggabungkan baca file + validasi kolom wajib dalam satu langkah.

    Parameters
    ----------
    uploaded_file : file-like object
        Objek file dari st.file_uploader.

    Returns
    -------
    pd.DataFrame
        Data mentah yang sudah lolos validasi struktur kolom.

    Raises
    ------
    FileFormatError
        Jika file gagal dibaca.
    KolomHilangError
        Jika ada kolom wajib yang hilang.
    """
    df = baca_file(uploaded_file)

    jenis_data = tentukan_jenis_data(df)
    if jenis_data is None:
        kolom_training_hilang = validasi_kolom_wajib(df, KOLOM_WAJIB)
        kolom_master_hilang = validasi_kolom_wajib(df, KOLOM_WAJIB_MASTER)
        kolom_laporan_hilang = validasi_kolom_wajib(
            df, KOLOM_WAJIB_LAPORAN_TRAINING
        )
        raise FileFormatError(
            "Schema file tidak dikenali sebagai data training, laporan nilai, "
            "maupun master employee. "
            f"Penanda master yang belum ditemukan: {', '.join(kolom_master_hilang)}. "
            f"Kolom training lama yang belum ditemukan: {', '.join(kolom_training_hilang)}. "
            f"Kolom laporan nilai yang belum ditemukan: {', '.join(kolom_laporan_hilang)}."
        )

    if len(df) == 0:
        raise FileFormatError("File berhasil dibaca tapi tidak berisi data (0 baris).")

    return df
