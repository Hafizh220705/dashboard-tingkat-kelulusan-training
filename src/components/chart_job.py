"""
Komponen visualisasi "Tingkat Kelulusan berdasarkan Job".

Dipakai vertical bar chart (bukan horizontal seperti chart_area.py)
karena asumsi jumlah kategori Job jauh lebih sedikit dibanding Area
(mis. Operator, Mekanik, Supervisor, dst.) sehingga label sumbu X
masih nyaman dibaca tanpa perlu di-rotate atau kepotong.

Kalau nanti ternyata jumlah kategori Job juga banyak (>15-an), pola
horizontal bar dari chart_area.py bisa langsung diadaptasi ke sini.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics.kpi import hitung_kpi_per_kategori
from config.settings import URUTAN_STATUS, WARNA_STATUS

NAMA_KOLOM_JOB = "JOB"

def render_chart_job(df: pd.DataFrame) -> None:
    """
    Render vertical bar chart + tabel rekap untuk breakdown by Job.

    Parameters
    ----------
    df : pd.DataFrame
        Data level partisipasi yang SUDAH difilter (hasil dari
        terapkan_filter()), harus punya kolom JOB dan RESULT_FINAL.
    """
    st.subheader("Tingkat Kelulusan berdasarkan Job")

    if df[NAMA_KOLOM_JOB].nunique() == 0:
        st.info("Tidak ada data Job untuk ditampilkan.")
        return

    # --- Chart ---
    rekap_long = (
        df.groupby([NAMA_KOLOM_JOB, "RESULT_FINAL"])
        .size()
        .reset_index(name="Jumlah")
    )

    fig = px.bar(
        rekap_long,
        x=NAMA_KOLOM_JOB,
        y="Jumlah",
        color="RESULT_FINAL",
        color_discrete_map=WARNA_STATUS,
        category_orders={"RESULT_FINAL": URUTAN_STATUS},
    )
    fig.update_layout(
        xaxis={"categoryorder": "total descending"},
        legend_title_text="Status",
        xaxis_title="Job",
        yaxis_title="Jumlah Peserta",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Tabel rekap detail ---
    st.markdown("**Tabel Rekap Detail per Job**")
    tabel = hitung_kpi_per_kategori(df, NAMA_KOLOM_JOB)
    st.dataframe(tabel, use_container_width=True)