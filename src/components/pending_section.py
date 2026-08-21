"""
Komponen placeholder untuk fitur yang datanya masih pending:
Masa Kerja dan Reason Tidak Lulus.

Modul ini sengaja dipisah jadi komponen sendiri (bukan cuma st.warning
inline di app.py) supaya:
  1. Kalau data-nya sudah tersedia nanti, tinggal GANTI ISI FUNGSI INI
     dengan chart/tabel sungguhan -- pemanggilan di app.py tidak perlu
     berubah sama sekali (import & pemanggilan fungsi tetap sama).
  2. Status "pending" dan alasannya terdokumentasi di satu tempat yang
     jelas, gampang ditemukan siapapun yang buka source code.
"""

import streamlit as st


def render_pending_section() -> None:
    """
    Render tab placeholder untuk Masa Kerja & Reason Tidak Lulus.

    Dipanggil dari app.py selama data pendukung kedua fitur ini belum
    tersedia. Lihat Project Charter, section "Support Required", untuk
    daftar data yang perlu diminta ke stakeholder/mentor.
    """
    st.subheader("Masa Kerja & Reason Tidak Lulus")

    col_masa_kerja, col_reason = st.columns(2)

    with col_masa_kerja:
        _render_kartu_pending(
            judul="📅 Tingkat Kelulusan berdasarkan Masa Kerja",
            alasan=(
                "Membutuhkan data tanggal join karyawan dari sistem HR "
                "untuk menghitung kategori **< 2 Tahun** / **≥ 2 Tahun**. "
                "Dataset training saat ini belum punya kolom tanggal join."
            ),
        )

    with col_reason:
        _render_kartu_pending(
            judul="📝 Reason / Penyebab Tidak Lulus",
            alasan=(
                "Kolom `RESULT` pada dataset saat ini hanya berisi status "
                "akhir (Lulus/Tidak Lulus/Finished), bukan penyebab "
                "kegagalan. Membutuhkan kolom tambahan yang mencatat "
                "alasan spesifik (misal: tidak hadir, nilai kurang, "
                "mengundurkan diri)."
            ),
        )

    st.caption(
        "Kedua item di atas sudah dicatat sebagai pending item di Project "
        "Charter, section *Support Required*, dan akan diaktifkan setelah "
        "data pendukungnya tersedia."
    )


def _render_kartu_pending(judul: str, alasan: str) -> None:
    """Helper internal: render satu kartu placeholder yang konsisten."""
    with st.container(border=True):
        st.markdown(f"**{judul}**")
        st.warning(f"🚧 Belum tersedia.\n\n{alasan}")