"""Komponen Streamlit untuk konversi CSV dan penggabungan Excel."""

from pathlib import Path

import streamlit as st

from config.settings import (
    KOLOM_WAJIB_LAPORAN_TRAINING,
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)
from src.data.file_tools import (
    PengolahanFileError,
    dataframe_ke_excel,
    gabungkan_file_excel,
    hubungkan_laporan_dengan_master,
    konversi_banyak_csv_ke_zip,
    konversi_csv_ke_excel,
    siapkan_laporan_training,
)
from src.data.loader import (
    FileFormatError,
    JENIS_DATA_MASTER,
    muat_dan_validasi,
    tentukan_jenis_data,
)


def render_file_tools() -> None:
    """Render alat file mandiri tanpa memengaruhi data dashboard."""
    with st.expander("🛠️ Alat File — CSV ke Excel & Gabung Excel"):
        st.caption(
            "Gunakan alat ini untuk menyiapkan file. Hasil merge laporan "
            "training otomatis tersedia sebagai input Nilai Training di dashboard."
        )
        tab_konversi, tab_gabung = st.tabs(["CSV → Excel", "Gabung Excel"])

        with tab_konversi:
            _render_konversi_csv()

        with tab_gabung:
            _render_gabung_excel()


def _render_konversi_csv() -> None:
    st.write(
        "Upload satu atau beberapa file CSV sekaligus. Jika file lebih dari "
        "satu, seluruh hasil Excel akan dikemas dalam satu ZIP."
    )
    uploaded_files = st.file_uploader(
        "Pilih satu atau beberapa file CSV",
        type=["csv"],
        accept_multiple_files=True,
        key="alat_konversi_csv",
    )
    if not uploaded_files:
        return

    try:
        with st.spinner("Mengubah CSV menjadi Excel..."):
            if len(uploaded_files) == 1:
                df, hasil_excel = konversi_csv_ke_excel(uploaded_files[0])
            else:
                ringkasan, hasil_zip = konversi_banyak_csv_ke_zip(uploaded_files)
    except PengolahanFileError as exc:
        st.error(f"❌ {exc}")
        return

    if len(uploaded_files) == 1:
        nama_hasil = f"{Path(uploaded_files[0].name).stem}.xlsx"
        st.success(
            f"CSV berhasil dikonversi: {len(df):,} baris dan "
            f"{len(df.columns):,} kolom."
        )
        st.download_button(
            "⬇️ Download Excel",
            data=hasil_excel,
            file_name=nama_hasil,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_hasil_konversi_csv",
        )
        return

    total_baris = sum(item.jumlah_baris for item in ringkasan)
    st.success(
        f"{len(ringkasan)} CSV berhasil dikonversi "
        f"({total_baris:,} total baris)."
    )
    st.download_button(
        "⬇️ Download Semua Excel (.zip)",
        data=hasil_zip,
        file_name="hasil_konversi_csv.zip",
        mime="application/zip",
        key="download_hasil_konversi_csv_batch",
    )


def _render_gabung_excel() -> None:
    st.write(
        "Upload minimal dua laporan training `.xlsx`. Sheet pertama dari setiap "
        "file akan digabungkan, kemudian status ditentukan dari `Grade/100.00`."
    )
    st.caption(
        "Hasil berisi nilai data dalam satu sheet baru; format visual workbook "
        "asal tidak ikut disalin. Gabungkan file untuk satu training/test yang "
        "sama agar percobaan per NRP dapat dihitung dengan benar di dashboard."
    )
    tambah_sumber = st.checkbox(
        "Tambahkan kolom nama file sumber",
        value=True,
        key="alat_gabung_tambah_sumber",
        help="Memudahkan pelacakan asal setiap baris pada file hasil.",
    )
    uploaded_files = st.file_uploader(
        "Pilih beberapa laporan training Excel",
        type=["xlsx"],
        accept_multiple_files=True,
        key="alat_gabung_excel",
    )
    if not uploaded_files:
        return
    if len(uploaded_files) < 2:
        st.warning("Upload minimal dua file Excel untuk mulai menggabungkan.")
        return

    master_file = st.file_uploader(
        "Master employee untuk pencocokan NRP (opsional)",
        type=["xlsx", "csv"],
        key="alat_gabung_master_employee",
        help=(
            "NRP pada kolom 'First name' laporan training dicocokkan dengan "
            "kolom 'NRP' pada master employee."
        ),
    )

    try:
        with st.spinner("Menggabungkan file Excel..."):
            df = gabungkan_file_excel(
                uploaded_files,
                tambah_sumber_file=tambah_sumber,
                kolom_wajib=KOLOM_WAJIB_LAPORAN_TRAINING,
            )
            # Simpan data mentah hasil merge sebelum enrichment master agar
            # dashboard bisa langsung memakainya tanpa upload ulang.
            st.session_state["dashboard_nilai_training_hasil_merge"] = df.copy()
            df = siapkan_laporan_training(df)
            ringkasan_master = None

            if master_file is not None:
                df_master = muat_dan_validasi(master_file)
                if tentukan_jenis_data(df_master) != JENIS_DATA_MASTER:
                    raise PengolahanFileError(
                        "File master tidak dikenali sebagai master employee."
                    )
                df, ringkasan_master = hubungkan_laporan_dengan_master(
                    df,
                    df_master,
                )

            hasil_excel = dataframe_ke_excel(df, nama_sheet="Data Gabungan")
    except (PengolahanFileError, FileFormatError) as exc:
        st.error(f"❌ {exc}")
        return

    jumlah_lulus = int((df["RESULT_FINAL"] == STATUS_LULUS).sum())
    jumlah_tidak_lulus = int((df["RESULT_FINAL"] == STATUS_TIDAK_LULUS).sum())
    jumlah_tidak_lengkap = int(
        (df["RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP).sum()
    )
    st.success(
        f"{len(uploaded_files)} file berhasil digabungkan menjadi "
        f"{len(df):,} baris: {jumlah_lulus:,} lulus dan "
        f"{jumlah_tidak_lulus:,} tidak lulus, serta "
        f"{jumlah_tidak_lengkap:,} data tidak lengkap."
    )
    if ringkasan_master is not None:
        st.info(
            f"Pencocokan master: {ringkasan_master.jumlah_cocok:,} baris cocok "
            f"dan {ringkasan_master.jumlah_tidak_cocok:,} baris tidak cocok."
        )
        if ringkasan_master.jumlah_duplikat_master_dihapus > 0:
            st.warning(
                f"Ada {ringkasan_master.jumlah_duplikat_master_dihapus:,} baris "
                "NRP duplikat pada master; kemunculan pertama yang digunakan."
            )
    st.download_button(
        "⬇️ Download Hasil Training",
        data=hasil_excel,
        file_name="hasil_training_tergabung.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_hasil_gabung_excel",
    )
