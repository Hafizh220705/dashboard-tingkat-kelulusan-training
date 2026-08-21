"""Executive overview untuk master data employee."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


WARNA_UT = [
    "#FFD100",  # kuning United Tractors
    "#0054A6",  # biru Astra
    "#1D1D1B",  # charcoal UT
    "#E87722",  # oranye aksen
    "#4D8AC8",  # biru muda
    "#7A7D81",  # abu-abu
    "#F2B705",  # amber
    "#2E7D32",  # hijau status
    "#00A6B2",  # teal
    "#B23A48",  # merah muted
]

FILTER_MASTER = [
    ("Jabatan", "Jabatan"),
    ("Gender", "Gender"),
    ("Nama Perusahaan", "Nama Perusahaan"),
    ("BA", "BA"),
    ("Plant", "Plant"),
    ("Div (Penempatan Saat Ini)", "Divisi"),
    ("S-Loc", "S-Loc"),
    ("Perusahaan", "Perusahaan"),
    ("CAB / SITE", "Cab/Site"),
]

# Titik awal palet dibedakan agar setiap panel punya karakter warna sendiri,
# tetapi keseluruhan dashboard tetap konsisten.
OFFSET_WARNA = {
    "Plant": 0,
    "Div (Penempatan Saat Ini)": 2,
    "Nama Perusahaan": 4,
    "Perusahaan": 4,
    "Pendidikan Terakhir": 1,
    "Jabatan": 3,
    "BA": 6,
    "CAB / SITE": 8,
}


def _rapikan(fig, tinggi: int = 360):
    fig.update_layout(
        height=tinggi,
        margin=dict(l=20, r=20, t=35, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial", color="#263238"),
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(gridcolor="#EEF2F6", zeroline=False)
    fig.update_yaxes(gridcolor="#EEF2F6", zeroline=False)
    return fig


def _angka(series: pd.Series) -> pd.Series:
    """Ambil angka dari nilai seperti '32 Tahun' atau '5,5'."""
    teks = series.astype("string").str.replace(",", ".", regex=False)
    return pd.to_numeric(teks.str.extract(r"(-?\d+(?:\.\d+)?)", expand=False), errors="coerce")


def _interval(
    series: pd.Series, batas: list[float], label: list[str]
) -> pd.Series:
    """Kelompokkan series numerik ke interval berurutan."""
    return pd.cut(_angka(series), bins=batas, labels=label, include_lowest=True)


def _kolom_pertama(df: pd.DataFrame, kandidat: list[str]) -> str | None:
    return next((kolom for kolom in kandidat if kolom in df.columns), None)


def _distribusi(df: pd.DataFrame, kolom: str, top_n: int = 10) -> pd.DataFrame:
    nilai = df[kolom].astype("string").str.strip()
    nilai = nilai.mask(nilai.isin(["", "nan", "None", "<NA>"]), "Tidak diketahui")
    hasil = nilai.fillna("Tidak diketahui").value_counts().head(top_n).reset_index()
    hasil.columns = [kolom, "Jumlah"]
    return hasil


def _donut(df: pd.DataFrame, kolom: str):
    data = _distribusi(df, kolom, 8)
    fig = go.Figure(
        go.Pie(
            labels=data[kolom],
            values=data["Jumlah"],
            hole=0.62,
            marker_colors=WARNA_UT,
            textinfo="percent",
            hovertemplate="%{label}<br>%{value:,} employee (%{percent})<extra></extra>",
        )
    )
    fig.add_annotation(text=f"<b>{len(df):,}</b><br>Employee", showarrow=False)
    fig.update_layout(legend=dict(orientation="h", y=-0.08))
    return _rapikan(fig)


def _bar_horizontal(df: pd.DataFrame, kolom: str, top_n: int = 10):
    data = _distribusi(df, kolom, top_n).sort_values("Jumlah")
    offset = OFFSET_WARNA.get(kolom, 0)
    palet = WARNA_UT[offset:] + WARNA_UT[:offset]
    fig = px.bar(
        data,
        x="Jumlah",
        y=kolom,
        orientation="h",
        text="Jumlah",
        color=kolom,
        color_discrete_sequence=palet,
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_color="rgba(255,255,255,.85)",
        marker_line_width=1,
    )
    fig.update_layout(xaxis_title="Employee", yaxis_title=None, showlegend=False)
    return _rapikan(fig, max(340, len(data) * 34 + 75))


def _bar_interval(series: pd.Series, jenis: str):
    if jenis == "usia":
        kelompok = _interval(
            series,
            [0, 20, 25, 30, 35, 40, 45, 50, 55, 60, float("inf")],
            ["≤20", "21–25", "26–30", "31–35", "36–40", "41–45", "46–50", "51–55", "56–60", ">60"],
        )
    else:
        kelompok = pd.cut(
            _angka(series),
            bins=[0, 2, float("inf")],
            labels=["< 2 tahun", "≥ 2 tahun"],
            include_lowest=True,
            right=False,
        )
    jumlah = kelompok.value_counts(sort=False).reset_index()
    jumlah.columns = ["Interval", "Jumlah"]
    jumlah = jumlah[jumlah["Jumlah"] > 0]
    fig = px.bar(
        jumlah,
        x="Interval",
        y="Jumlah",
        text="Jumlah",
        color="Interval",
        color_discrete_sequence=WARNA_UT,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title="Tahun", yaxis_title="Employee", showlegend=False)
    return _rapikan(fig, 340)


def terapkan_filter_master(df: pd.DataFrame, pilihan: dict[str, list]) -> pd.DataFrame:
    """Terapkan seluruh pilihan filter tanpa memutasi data sumber."""
    hasil = df.copy()
    for kolom, nilai_dipilih in pilihan.items():
        if nilai_dipilih and kolom in hasil.columns:
            hasil = hasil[
                hasil[kolom].astype("string").str.strip().isin(nilai_dipilih)
            ]
    return hasil


def _render_filter_master(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filter Master Employee")
    st.sidebar.caption("Semua visual dan KPI mengikuti filter ini.")

    def reset_filter() -> None:
        for kolom, _ in FILTER_MASTER:
            st.session_state.pop(f"filter_master_{kolom}", None)

    st.sidebar.button(
        "Reset semua filter", use_container_width=True, on_click=reset_filter
    )
    pilihan = {}
    for kolom, label in FILTER_MASTER:
        if kolom not in df.columns:
            continue
        opsi = sorted(df[kolom].dropna().astype("string").str.strip().unique().tolist())
        pilihan[kolom] = st.sidebar.multiselect(
            label, opsi, key=f"filter_master_{kolom}"
        )
    hasil = terapkan_filter_master(df, pilihan)
    st.sidebar.caption(f"Menampilkan {len(hasil):,} dari {len(df):,} employee")
    return hasil


def _insight(df: pd.DataFrame) -> str:
    sorotan = []
    for kolom, label in [("Plant", "plant"), ("Div (Penempatan Saat Ini)", "divisi")]:
        if kolom in df.columns and df[kolom].notna().any():
            data = _distribusi(df, kolom, 1).iloc[0]
            persen = data["Jumlah"] / len(df) * 100 if len(df) else 0
            sorotan.append(
                f"{label.title()} terbesar **{data[kolom]}** ({data['Jumlah']:,} employee; {persen:.1f}%)"
            )
    return "; sementara ".join(sorotan) + "." if sorotan else "Data berhasil dimuat dan siap dianalisis."


def render_master_dashboard(
    df: pd.DataFrame,
    gunakan_filter_sidebar: bool = True,
) -> None:
    """Render ringkasan master employee yang mudah dipindai stakeholder."""
    df_sumber = df
    df = _render_filter_master(df_sumber) if gunakan_filter_sidebar else df_sumber.copy()
    st.success("File master employee berhasil diupload dan dibersihkan.")
    if df.empty:
        st.warning("Tidak ada employee yang cocok dengan kombinasi filter. Ubah pilihan filter di sidebar.")
        return
    st.markdown("### Executive overview")
    st.info("💡 " + _insight(df))

    perusahaan = _kolom_pertama(df, ["Nama Perusahaan", "Perusahaan"])
    usia = _angka(df["USIA"]) if "USIA" in df.columns else pd.Series(dtype=float)
    lama_kerja = _angka(df["LAMA KERJA"]) if "LAMA KERJA" in df.columns else pd.Series(dtype=float)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Employee", f"{len(df):,}")
    k2.metric("NRP Unik", f"{df['NRP'].nunique(dropna=True):,}")
    k3.metric("Perusahaan", f"{df[perusahaan].nunique(dropna=True):,}" if perusahaan else "–")
    k4.metric("Rata-rata Usia", f"{usia.mean():.1f} tahun" if usia.notna().any() else "–")
    k5.metric(
        "Rata-rata Masa Kerja",
        f"{lama_kerja.mean():.1f} tahun" if lama_kerja.notna().any() else "–",
    )

    if len(df) != len(df_sumber):
        st.caption(f"Visual menampilkan {len(df):,} dari total {len(df_sumber):,} employee.")

    kiri, kanan = st.columns([0.8, 1.3], gap="large")
    with kiri:
        if "Gender" in df.columns:
            st.markdown("#### Komposisi gender")
            st.plotly_chart(_donut(df, "Gender"), use_container_width=True, config={"displayModeBar": False})
    with kanan:
        if "Plant" in df.columns:
            st.markdown("#### Sebaran employee per plant")
            st.plotly_chart(_bar_horizontal(df, "Plant"), use_container_width=True, config={"displayModeBar": False})

    kandidat_chart = [
        ("Div (Penempatan Saat Ini)", "Employee per divisi"),
        (perusahaan, "Employee per perusahaan"),
        ("Pendidikan Terakhir", "Komposisi pendidikan"),
        ("Jabatan", "Jabatan terbanyak"),
        ("BA", "Employee per BA"),
        ("CAB / SITE", "Employee per cabang/site"),
    ]
    kandidat_chart = [(kolom, judul) for kolom, judul in kandidat_chart if kolom and kolom in df.columns]
    for index in range(0, len(kandidat_chart), 2):
        pasangan = kandidat_chart[index:index + 2]
        kolom_ui = st.columns(len(pasangan), gap="large")
        for container, (kolom, judul) in zip(kolom_ui, pasangan):
            with container:
                st.markdown(f"#### {judul}")
                st.plotly_chart(_bar_horizontal(df, kolom), use_container_width=True, config={"displayModeBar": False})

    chart_interval = []
    if "USIA" in df.columns and _angka(df["USIA"]).notna().any():
        chart_interval.append(("Distribusi interval usia", _bar_interval(df["USIA"], "usia")))
    if "LAMA KERJA" in df.columns and _angka(df["LAMA KERJA"]).notna().any():
        chart_interval.append(("Distribusi interval masa kerja", _bar_interval(df["LAMA KERJA"], "masa_kerja")))
    if chart_interval:
        st.markdown("### Profil usia dan masa kerja")
        kolom_ui = st.columns(len(chart_interval), gap="large")
        for container, (judul, fig) in zip(kolom_ui, chart_interval):
            with container:
                st.markdown(f"#### {judul}")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("Lihat master data lengkap"):
        st.dataframe(df, use_container_width=True, hide_index=True)
