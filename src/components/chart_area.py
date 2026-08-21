"""
Komponen visualisasi "Tingkat Kelulusan berdasarkan Area".

Dipakai horizontal bar chart (bukan vertical) karena jumlah kategori
Area di data asli cukup banyak -- vertical bar akan bikin label
sumpek/miring dan susah dibaca (lihat diskusi sebelumnya soal "Plant
kategorinya banyak"). Ditambah tabel rekap detail supaya user bisa
lihat angka pasti per Area, bukan cuma estimasi visual dari bar.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics.kpi import hitung_kpi_per_kategori
from config.settings import URUTAN_STATUS, WARNA_STATUS

NAMA_KOLOM_AREA = "AREA"


def render_chart_area(df: pd.DataFrame) -> None:
    """
    Render horizontal bar chart + tabel rekap untuk breakdown by Area.

    Parameters
    ----------
    df : pd.DataFrame
        Data level partisipasi yang SUDAH difilter (hasil dari
        terapkan_filter()), harus punya kolom AREA dan RESULT_FINAL.
    """
    st.subheader("Tingkat Kelulusan berdasarkan Area")

    if df[NAMA_KOLOM_AREA].nunique() == 0:
        st.info("Tidak ada data Area untuk ditampilkan.")
        return

    # --- Chart ---
    rekap_long = (
        df.groupby([NAMA_KOLOM_AREA, "RESULT_FINAL"])
        .size()
        .reset_index(name="Jumlah")
    )

    fig = px.bar(
        rekap_long,
        y=NAMA_KOLOM_AREA,
        x="Jumlah",
        color="RESULT_FINAL",
        orientation="h",
        color_discrete_map=WARNA_STATUS,
        category_orders={"RESULT_FINAL": URUTAN_STATUS},
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        legend_title_text="Status",
        xaxis_title="Jumlah Peserta",
        yaxis_title="Area",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Tabel rekap detail ---
    st.markdown("**Tabel Rekap Detail per Area**")
    tabel = hitung_kpi_per_kategori(df, NAMA_KOLOM_AREA)
    st.dataframe(tabel, use_container_width=True)