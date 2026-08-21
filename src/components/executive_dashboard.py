"""Visualisasi satu halaman untuk presentasi stakeholder."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import STATUS_LULUS, URUTAN_STATUS, WARNA_STATUS
from src.metrics.kpi import hitung_kpi_per_kategori


def _rapikan(fig, tinggi=380):
    fig.update_layout(
        height=tinggi, margin=dict(l=20, r=20, t=45, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial", color="#263238"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_yaxes(gridcolor="#EEF2F6", zeroline=False)
    fig.update_xaxes(gridcolor="#EEF2F6", zeroline=False)
    return fig


def _status_chart(df: pd.DataFrame, label_unit: str = "Partisipasi"):
    jumlah = df["RESULT_FINAL"].value_counts().reindex(URUTAN_STATUS, fill_value=0)
    fig = go.Figure(go.Pie(
        labels=jumlah.index, values=jumlah.values, hole=.68,
        marker_colors=[WARNA_STATUS[x] for x in jumlah.index], textinfo="percent",
        hovertemplate=(
            f"%{{label}}<br>%{{value:,}} {label_unit.lower()} "
            "(%{percent})<extra></extra>"
        ),
    ))
    fig.add_annotation(
        text=f"<b>{len(df):,}</b><br><span style='font-size:12px'>{label_unit}</span>",
        x=.5, y=.5, showarrow=False, font_size=22,
    )
    return _rapikan(fig)


def _trend_chart(df: pd.DataFrame, label_unit: str = "Partisipasi"):
    valid = df[df["TAHUN"].notna()]
    tren = (valid.groupby("TAHUN")["RESULT_FINAL"]
            .agg(Partisipasi="size", Lulus=lambda x: (x == STATUS_LULUS).sum())
            .reset_index())
    tren["Pass Rate"] = (tren["Lulus"] / tren["Partisipasi"] * 100).round(1)
    fig = go.Figure()
    fig.add_bar(x=tren["TAHUN"].astype(str), y=tren["Partisipasi"], name="Partisipasi",
                marker_color="#DCE6F2", hovertemplate="%{x}: %{y:,}<extra></extra>")
    fig.add_scatter(
        x=tren["TAHUN"].astype(str), y=tren["Pass Rate"], name="Pass Rate",
        mode="lines+markers+text", text=tren["Pass Rate"].map(lambda x: f"{x:.1f}%"),
        textposition="top center", yaxis="y2", line=dict(color="#F59E0B", width=3),
    )
    fig.update_layout(
        yaxis_title=label_unit, bargap=.48,
        yaxis2=dict(title="Pass Rate", overlaying="y", side="right", range=[0, 110], ticksuffix="%"),
    )
    return _rapikan(fig)


def _pass_rate_bar(df: pd.DataFrame, kolom: str, top_n: int = 10):
    tabel = hitung_kpi_per_kategori(df, kolom).reset_index()
    tabel = tabel.nlargest(top_n, "Total").sort_values("Pass Rate (%)")
    fig = px.bar(
        tabel, x="Pass Rate (%)", y=kolom, orientation="h", text="Pass Rate (%)",
        color="Pass Rate (%)", color_continuous_scale=["#C62828", "#F59E0B", "#2E7D32"],
        range_color=[0, 100], custom_data=["Total"],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}%", textposition="outside",
        hovertemplate="<b>%{y}</b><br>Pass Rate: %{x:.1f}%<br>Total: %{customdata[0]:,}<extra></extra>",
    )
    fig.update_layout(
        coloraxis_showscale=False, xaxis=dict(range=[0, 108], ticksuffix="%"),
        xaxis_title="Pass Rate", yaxis_title=None, showlegend=False,
    )
    return _rapikan(fig, max(350, len(tabel) * 34 + 90))


def _job_chart(df: pd.DataFrame, label_unit: str = "Partisipasi"):
    data = df.groupby(["JOB", "RESULT_FINAL"]).size().reset_index(name="Jumlah")
    fig = px.bar(
        data, x="JOB", y="Jumlah", color="RESULT_FINAL", barmode="stack",
        color_discrete_map=WARNA_STATUS, category_orders={"RESULT_FINAL": URUTAN_STATUS},
    )
    fig.update_layout(xaxis_title=None, yaxis_title=label_unit, legend_title_text="")
    return _rapikan(fig)


def _insight(df: pd.DataFrame) -> str:
    area = hitung_kpi_per_kategori(df, "AREA")
    signifikan = area[area["Total"] >= max(3, int(len(df) * .01))]
    if signifikan.empty:
        return "Data terfilter belum cukup untuk menghasilkan sorotan area yang representatif."
    terbaik = signifikan["Pass Rate (%)"].idxmax()
    perhatian = signifikan["Pass Rate (%)"].idxmin()
    return (f"Area dengan performa tertinggi adalah **{terbaik}** "
            f"({signifikan.loc[terbaik, 'Pass Rate (%)']:.1f}%), sementara **{perhatian}** "
            f"perlu perhatian lebih lanjut ({signifikan.loc[perhatian, 'Pass Rate (%)']:.1f}%).")


def render_executive_dashboard(
    df: pd.DataFrame,
    label_unit: str = "Partisipasi",
) -> None:
    st.markdown("### Executive overview")
    st.info("💡 " + _insight(df))

    kiri, kanan = st.columns([.82, 1.35], gap="large")
    with kiri:
        st.markdown("#### Komposisi hasil")
        st.plotly_chart(_status_chart(df, label_unit), use_container_width=True, config={"displayModeBar": False})
    with kanan:
        st.markdown("#### Perkembangan performa")
        st.plotly_chart(_trend_chart(df, label_unit), use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Perbandingan kinerja")
    kiri, kanan = st.columns(2, gap="large")
    with kiri:
        st.markdown("#### Pass rate per area")
        st.plotly_chart(_pass_rate_bar(df, "AREA"), use_container_width=True,
                        config={"displayModeBar": False})
    with kanan:
        st.markdown("#### Hasil berdasarkan job")
        st.plotly_chart(_job_chart(df, label_unit), use_container_width=True, config={"displayModeBar": False})

    st.markdown("#### Modul dengan volume peserta terbesar")
    st.plotly_chart(_pass_rate_bar(df, "MODUL TRAINING", 12), use_container_width=True,
                    config={"displayModeBar": False})

    with st.expander("📋 Lihat data ringkasan"):
        st.dataframe(hitung_kpi_per_kategori(df, "AREA"), use_container_width=True)
