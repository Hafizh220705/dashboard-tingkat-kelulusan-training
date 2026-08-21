"""Adapter dan tabel detail untuk dashboard laporan nilai training."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import (
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
    WARNA_STATUS,
)


LABEL_TIDAK_DIKETAHUI = "TIDAK DIKETAHUI"


def _kolom_teks_atau_default(
    df: pd.DataFrame,
    nama_kolom: str,
    default: str = LABEL_TIDAK_DIKETAHUI,
) -> pd.Series:
    if nama_kolom not in df.columns:
        return pd.Series(default, index=df.index, dtype="string")

    hasil = df[nama_kolom].astype("string").str.strip()
    return hasil.mask(hasil.isna() | (hasil == ""), default)


def siapkan_data_dashboard_laporan(df: pd.DataFrame) -> pd.DataFrame:
    """Petakan laporan+master ke nama dimensi yang dipakai dashboard lama."""
    kolom_wajib = ["NRP_ID", "NILAI_FINAL", "RESULT_FINAL"]
    kolom_hilang = [kolom for kolom in kolom_wajib if kolom not in df.columns]
    if kolom_hilang:
        raise KeyError(
            f"Data hasil training belum lengkap: {', '.join(kolom_hilang)}."
        )

    hasil = df.copy()
    hasil["AREA"] = _kolom_teks_atau_default(hasil, "Plant")
    hasil["JOB"] = _kolom_teks_atau_default(hasil, "Jabatan")

    if "SUMBER_FILE" in hasil.columns:
        modul = _kolom_teks_atau_default(hasil, "SUMBER_FILE", "TRAINING")
        hasil["MODUL TRAINING"] = modul.map(
            lambda nama: Path(str(nama)).stem if nama != "TRAINING" else nama
        )
    else:
        hasil["MODUL TRAINING"] = "TRAINING"

    kolom_tanggal = "Completed" if "Completed" in hasil.columns else "Started"
    if kolom_tanggal in hasil.columns:
        tanggal = pd.to_datetime(hasil[kolom_tanggal], errors="coerce", format="mixed")
        hasil["TAHUN"] = tanggal.dt.year.astype("Int64")
    else:
        hasil["TAHUN"] = pd.Series(pd.NA, index=hasil.index, dtype="Int64")

    return hasil


def rekap_kelulusan_percobaan(df: pd.DataFrame) -> pd.DataFrame:
    """Hitung karyawan lulus pada percobaan 1/2/3 atau belum lulus."""
    kategori = pd.Series("Belum Lulus", index=df.index, dtype="string")
    kategori.loc[df["RESULT_FINAL"] == STATUS_DATA_TIDAK_LENGKAP] = (
        "Data Tidak Lengkap"
    )

    mask_lulus = df["RESULT_FINAL"] == STATUS_LULUS
    nomor = df.get("LULUS_PADA_PERCOBAAN", pd.Series(pd.NA, index=df.index))
    kategori.loc[mask_lulus] = nomor.loc[mask_lulus].map(
        lambda nilai: f"Percobaan {int(nilai)}" if pd.notna(nilai) else "Lulus"
    )

    urutan = [
        "Percobaan 1",
        "Percobaan 2",
        "Percobaan 3",
        "Lulus",
        "Belum Lulus",
        "Data Tidak Lengkap",
    ]
    jumlah = kategori.value_counts().reindex(urutan, fill_value=0)
    return jumlah.rename_axis("Kategori").reset_index(name="Jumlah")


def render_visualisasi_percobaan(df: pd.DataFrame) -> None:
    """Render efektivitas percobaan dan distribusi nilai terbaik."""
    st.markdown("### Analisis percobaan")
    kiri, kanan = st.columns(2, gap="large")

    with kiri:
        st.markdown("#### Kelulusan berdasarkan percobaan")
        rekap = rekap_kelulusan_percobaan(df)
        warna = {
            "Percobaan 1": "#1B5E20",
            "Percobaan 2": "#43A047",
            "Percobaan 3": "#81C784",
            "Lulus": WARNA_STATUS[STATUS_LULUS],
            "Belum Lulus": WARNA_STATUS[STATUS_TIDAK_LULUS],
            "Data Tidak Lengkap": WARNA_STATUS[STATUS_DATA_TIDAK_LENGKAP],
        }
        fig = px.bar(
            rekap,
            x="Kategori",
            y="Jumlah",
            color="Kategori",
            text="Jumlah",
            color_discrete_map=warna,
        )
        fig.update_layout(
            showlegend=False,
            xaxis_title=None,
            yaxis_title="Jumlah Karyawan",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with kanan:
        st.markdown("#### Distribusi nilai terbaik")
        nilai_valid = df[df["NILAI_TERBAIK"].notna()]
        fig = px.histogram(
            nilai_valid,
            x="NILAI_TERBAIK",
            color="RESULT_FINAL",
            nbins=10,
            color_discrete_map=WARNA_STATUS,
            category_orders={
                "RESULT_FINAL": [STATUS_LULUS, STATUS_TIDAK_LULUS]
            },
        )
        fig.add_vline(x=80, line_dash="dash", line_color="#1D1D1B")
        fig.update_layout(
            xaxis_title="Nilai Terbaik",
            yaxis_title="Jumlah Karyawan",
            legend_title_text="Status",
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_detail_hasil_training(
    df: pd.DataFrame,
    df_percobaan: pd.DataFrame | None = None,
) -> None:
    """Tampilkan status per karyawan setelah filter dashboard diterapkan."""
    st.markdown("### Detail hasil per karyawan")
    kolom_prioritas = [
        "NRP_ID",
        "Nama Lengkap",
        "NILAI_PERCOBAAN_1",
        "NILAI_PERCOBAAN_2",
        "NILAI_PERCOBAAN_3",
        "NILAI_TERBAIK",
        "JUMLAH_PERCOBAAN",
        "LULUS_PADA_PERCOBAAN",
        "RESULT_FINAL",
        "MODUL TRAINING",
        "Plant",
        "Jabatan",
        "Div (Penempatan Saat Ini)",
        "Email address",
        "Started",
        "Completed",
        "Duration",
    ]
    kolom_tampil = [kolom for kolom in kolom_prioritas if kolom in df.columns]
    st.dataframe(
        df[kolom_tampil],
        use_container_width=True,
        hide_index=True,
        column_config={
            "NILAI_PERCOBAAN_1": st.column_config.NumberColumn("Nilai 1", format="%.2f"),
            "NILAI_PERCOBAAN_2": st.column_config.NumberColumn("Nilai 2", format="%.2f"),
            "NILAI_PERCOBAAN_3": st.column_config.NumberColumn("Nilai 3", format="%.2f"),
            "NILAI_TERBAIK": st.column_config.NumberColumn("Nilai Terbaik", format="%.2f"),
            "RESULT_FINAL": st.column_config.TextColumn("Status Kelulusan"),
            "MODUL TRAINING": st.column_config.TextColumn("Training/Modul"),
        },
    )

    if df_percobaan is None:
        return

    nrp_terpilih = set(df["NRP_ID"].dropna().astype("string"))
    mask_detail = df_percobaan["NRP_ID"].astype("string").isin(nrp_terpilih)
    if df["NRP_ID"].isna().any():
        mask_detail = mask_detail | df_percobaan["NRP_ID"].isna()
    detail = df_percobaan[mask_detail].copy()
    kolom_detail = [
        "NRP_ID",
        "Nama Lengkap",
        "PERCOBAAN_KE",
        "NILAI_FINAL",
        "RESULT_FINAL",
        "DIGUNAKAN_DALAM_HASIL",
        "Started",
        "Completed",
    ]
    for nomor in range(1, 11):
        kolom_detail.append(f"Q. {nomor} NILAI")
        if nomor <= 5:
            kolom_detail.append(f"Q. {nomor} SUMBER")
    kolom_detail = [kolom for kolom in kolom_detail if kolom in detail.columns]

    with st.expander("📋 Riwayat seluruh percobaan dan nilai per soal"):
        st.caption(
            "Untuk soal 1–5, kolom SUMBER menunjukkan apakah nilai diambil "
            "dari skala /10.00 atau fallback /20.00."
        )
        st.dataframe(
            detail[kolom_detail],
            use_container_width=True,
            hide_index=True,
        )
