"""
Komponen visualisasi "Tingkat Kelulusan berdasarkan Modul Training".

Ini fitur BONUS (di luar 5 requirement wajib di awal) -- relevan karena
struktur data asli ternyata 1 baris = 1 employee x 1 modul training,
jadi breakdown per modul jadi insight yang sangat natural untuk
dimunculkan (lihat diskusi sebelumnya soal perubahan struktur data).

Dipakai tabel sebagai visual utama (bukan chart) karena jumlah kategori
Modul Training berpotensi banyak juga seperti Area -- pola yang sama
dengan alasan "Plant kategorinya banyak" yang sudah kita bahas.
"""

import pandas as pd
import streamlit as st

from src.metrics.kpi import hitung_kpi_per_kategori

NAMA_KOLOM_MODUL = "MODUL TRAINING"


def render_chart_modul(df: pd.DataFrame) -> None:
    """
    Render tabel rekap kelulusan per Modul Training, dengan opsi
    highlight modul yang Pass Rate-nya paling rendah (perlu perhatian).

    Parameters
    ----------
    df : pd.DataFrame
        Data level partisipasi yang SUDAH difilter, harus punya kolom
        MODUL TRAINING dan RESULT_FINAL.
    """
    st.subheader("Tingkat Kelulusan berdasarkan Modul Training")

    if df[NAMA_KOLOM_MODUL].nunique() == 0:
        st.info("Tidak ada data Modul Training untuk ditampilkan.")
        return

    tabel = hitung_kpi_per_kategori(df, NAMA_KOLOM_MODUL)

    st.caption(
        "Diurutkan dari jumlah peserta terbanyak. Gunakan tabel ini untuk "
        "mengidentifikasi modul training dengan Pass Rate rendah yang "
        "mungkin perlu dievaluasi materinya."
    )

    st.dataframe(
        tabel.style.background_gradient(
            subset=["Pass Rate (%)"], cmap="RdYlGn", vmin=0, vmax=100
        ),
        use_container_width=True,
    )

    # --- Highlight modul dengan Pass Rate terendah ---
    _tampilkan_sorotan_modul_terlemah(tabel)


def _tampilkan_sorotan_modul_terlemah(tabel: pd.DataFrame, ambang_minimal_peserta: int = 5) -> None:
    """
    Helper internal: tampilkan peringatan untuk modul dengan Pass Rate
    terendah, TAPI hanya jika jumlah pesertanya cukup signifikan
    (>= ambang_minimal_peserta) supaya tidak menyesatkan.

    Alasan ambang batas: modul dengan cuma 1-2 peserta bisa punya
    Pass Rate 0% atau 100% murni karena sampel kecil, bukan berarti
    materinya benar-benar bermasalah/bagus.
    """
    tabel_signifikan = tabel[tabel["Total"] >= ambang_minimal_peserta]

    if tabel_signifikan.empty:
        st.caption(
            f"ℹ️ Belum ada modul dengan jumlah peserta ≥ {ambang_minimal_peserta} "
            "untuk dianalisis sorotannya."
        )
        return

    modul_terlemah = tabel_signifikan["Pass Rate (%)"].idxmin()
    pass_rate_terlemah = tabel_signifikan.loc[modul_terlemah, "Pass Rate (%)"]

    if pass_rate_terlemah < 50:
        st.warning(
            f"⚠️ Modul **{modul_terlemah}** memiliki Pass Rate terendah "
            f"({pass_rate_terlemah}%) dari peserta yang signifikan (≥{ambang_minimal_peserta} orang) "
            "-- kandidat untuk dievaluasi."
        )