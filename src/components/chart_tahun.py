"""
Komponen visualisasi "Tren Kelulusan berdasarkan Tahun Training".

Beda dari chart_area.py & chart_job.py: modul ini punya 2 visual
sekaligus -- (1) bar chart breakdown jumlah per status per tahun, dan
(2) line chart tren Pass Rate antar tahun -- karena tujuan utamanya
memang melihat TREN dari waktu ke waktu, bukan cuma breakdown sesaat.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.metrics.kpi import hitung_kpi_per_kategori
from config.settings import STATUS_LULUS, URUTAN_STATUS, WARNA_STATUS

NAMA_KOLOM_TAHUN = "TAHUN"


def _hitung_pass_rate_per_tahun(df: pd.DataFrame) -> pd.DataFrame:
    """
    Helper internal: hitung Pass Rate (%) per tahun untuk line chart tren.

    Sengaja dipisah dari hitung_kpi_per_kategori() di kpi.py karena
    output yang dibutuhkan di sini beda bentuk (long format 2 kolom
    untuk px.line), bukan tabel rekap lengkap seperti breakdown Area/Job.
    """
    return (
        df.groupby(NAMA_KOLOM_TAHUN)["RESULT_FINAL"]
        .apply(lambda s: round((s == STATUS_LULUS).sum() / len(s) * 100, 1))
        .reset_index(name="Pass Rate (%)")
        .sort_values(NAMA_KOLOM_TAHUN)
    )


def render_chart_tahun(df: pd.DataFrame) -> None:
    """
    Render bar chart breakdown + line chart tren Pass Rate untuk
    Tahun Training.

    Parameters
    ----------
    df : pd.DataFrame
        Data level partisipasi yang SUDAH difilter, harus punya kolom
        TAHUN dan RESULT_FINAL.
    """
    st.subheader("Tren Kelulusan berdasarkan Tahun Training")

    df_valid_tahun = df[df[NAMA_KOLOM_TAHUN].notna()]

    if df_valid_tahun[NAMA_KOLOM_TAHUN].nunique() == 0:
        st.info("Tidak ada data Tahun Training untuk ditampilkan.")
        return

    if df_valid_tahun[NAMA_KOLOM_TAHUN].nunique() == 1:
        st.caption(
            "⚠️ Data hanya mencakup satu tahun training, sehingga tren "
            "antar tahun belum bisa dibandingkan. Grafik di bawah tetap "
            "menampilkan breakdown untuk tahun yang tersedia."
        )

    # --- Bar chart breakdown per status ---
    rekap_long = (
        df_valid_tahun.groupby([NAMA_KOLOM_TAHUN, "RESULT_FINAL"])
        .size()
        .reset_index(name="Jumlah")
    )

    fig_bar = px.bar(
        rekap_long,
        x=NAMA_KOLOM_TAHUN,
        y="Jumlah",
        color="RESULT_FINAL",
        barmode="group",
        color_discrete_map=WARNA_STATUS,
        category_orders={"RESULT_FINAL": URUTAN_STATUS},
    )
    fig_bar.update_layout(
        legend_title_text="Status",
        xaxis_title="Tahun Training",
        yaxis_title="Jumlah Peserta",
        xaxis={"type": "category"},  # cegah Plotly render 2024, 2024.5, 2025 di sumbu
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Line chart tren Pass Rate ---
    st.markdown("**Tren Pass Rate Antar Tahun**")
    tren_passrate = _hitung_pass_rate_per_tahun(df_valid_tahun)
    fig_line = px.line(
        tren_passrate, x=NAMA_KOLOM_TAHUN, y="Pass Rate (%)", markers=True
    )
    fig_line.update_layout(xaxis={"type": "category"})
    fig_line.update_traces(line_color=WARNA_STATUS[STATUS_LULUS])
    st.plotly_chart(fig_line, use_container_width=True)

    # --- Tabel rekap detail ---
    st.markdown("**Tabel Rekap Detail per Tahun**")
    tabel = hitung_kpi_per_kategori(df_valid_tahun, NAMA_KOLOM_TAHUN)
    st.dataframe(tabel, use_container_width=True)