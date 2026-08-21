"""Filter ringkas untuk dashboard presentasi stakeholder."""

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from config.settings import LEVEL_PER_PARTISIPASI


FILTER_ATRIBUT_MASTER = [
    ("Gender", "Gender"),
    ("Div (Penempatan Saat Ini)", "Divisi"),
    ("Nama Perusahaan", "Nama Perusahaan"),
    ("Perusahaan", "Perusahaan"),
    ("BA", "BA"),
    ("S-Loc", "S-Loc"),
    ("CAB / SITE", "Cab/Site"),
    ("Pendidikan Terakhir", "Pendidikan Terakhir"),
]


@dataclass
class FilterState:
    area: list = field(default_factory=list)
    job: list = field(default_factory=list)
    tahun: list = field(default_factory=list)
    modul_training: list = field(default_factory=list)
    status_kelulusan: list = field(default_factory=list)
    atribut_master: dict[str, list] = field(default_factory=dict)
    level_agregasi: str = LEVEL_PER_PARTISIPASI


def _opsi_teks(df: pd.DataFrame, kolom: str) -> list[str]:
    if kolom not in df.columns:
        return []
    nilai = df[kolom].dropna().astype("string").str.strip()
    return sorted(nilai[nilai != ""].unique().tolist())


def render_sidebar_filters(df: pd.DataFrame) -> FilterState:
    """Tampilkan seluruh filter training dan atribut master yang tersedia."""
    st.sidebar.header("🎯 Filter Utama")
    st.sidebar.caption(
        "Filter berlaku untuk KPI dan visual hasil training. Kosong berarti semua data."
    )

    semua_key = [
        "filter_training_tahun",
        "filter_training_area",
        "filter_training_job",
        "filter_training_modul",
        "filter_training_status",
    ] + [f"filter_training_master_{kolom}" for kolom, _ in FILTER_ATRIBUT_MASTER]

    def reset_filter() -> None:
        for key in semua_key:
            st.session_state.pop(key, None)

    st.sidebar.button(
        "↺ Reset semua filter",
        use_container_width=True,
        on_click=reset_filter,
        key="reset_filter_training",
    )

    tahun = (
        st.sidebar.multiselect(
            "Tahun Training",
            sorted(df["TAHUN"].dropna().unique().tolist()),
            key="filter_training_tahun",
        )
        if "TAHUN" in df.columns
        else []
    )
    area = st.sidebar.multiselect(
        "Area / Plant", _opsi_teks(df, "AREA"), key="filter_training_area"
    )
    job = st.sidebar.multiselect(
        "Jabatan / Job", _opsi_teks(df, "JOB"), key="filter_training_job"
    )
    modul = st.sidebar.multiselect(
        "Training / Modul",
        _opsi_teks(df, "MODUL TRAINING"),
        key="filter_training_modul",
    )
    status = st.sidebar.multiselect(
        "Status Kelulusan",
        _opsi_teks(df, "RESULT_FINAL"),
        key="filter_training_status",
    )

    atribut_master = {}
    filter_master_tersedia = [
        (kolom, label)
        for kolom, label in FILTER_ATRIBUT_MASTER
        if kolom in df.columns and _opsi_teks(df, kolom)
    ]
    if filter_master_tersedia:
        st.sidebar.markdown("**Atribut Master Employee**")
        for kolom, label in filter_master_tersedia:
            atribut_master[kolom] = st.sidebar.multiselect(
                label,
                _opsi_teks(df, kolom),
                key=f"filter_training_master_{kolom}",
            )

    return FilterState(
        area=area,
        job=job,
        tahun=tahun,
        modul_training=modul,
        status_kelulusan=status,
        atribut_master=atribut_master,
    )


def _filter_teks(df: pd.DataFrame, kolom: str, pilihan: list) -> pd.DataFrame:
    if not pilihan or kolom not in df.columns:
        return df
    return df[df[kolom].astype("string").str.strip().isin(pilihan)]


def terapkan_filter(df: pd.DataFrame, filter_state: FilterState) -> pd.DataFrame:
    """Terapkan filter aktif tanpa memutasi DataFrame sumber."""
    hasil = df.copy()
    hasil = _filter_teks(hasil, "AREA", filter_state.area)
    hasil = _filter_teks(hasil, "JOB", filter_state.job)
    if filter_state.tahun:
        hasil = hasil[hasil["TAHUN"].isin(filter_state.tahun)]
    hasil = _filter_teks(hasil, "MODUL TRAINING", filter_state.modul_training)
    hasil = _filter_teks(hasil, "RESULT_FINAL", filter_state.status_kelulusan)
    for kolom, pilihan in filter_state.atribut_master.items():
        hasil = _filter_teks(hasil, kolom, pilihan)
    return hasil
