"""
Training Performance Dashboard — Entry Point
==============================================
PT United Tractors Tbk — Monitoring Kelulusan Training Karyawan.

File ini SENGAJA dijaga tetap pendek: hanya orkestrasi (baca file ->
normalisasi -> filter -> render komponen). Semua logic detail ada di
modul masing-masing (src/data, src/metrics, src/components).

Kalau butuh ubah:
  - Cara baca/validasi file       -> src/data/loader.py
  - Cara bersihin/klasifikasi data -> src/data/normalizer.py
  - Cara hitung KPI                -> src/metrics/kpi.py
  - Tampilan filter sidebar        -> src/components/sidebar_filter.py
  - Tampilan KPI card              -> src/components/kpi_cards.py
  - Tampilan chart per breakdown   -> src/components/chart_*.py
  - Konstanta/threshold/warna      -> config/settings.py
"""

from pathlib import Path

import streamlit as st

from config.settings import (
    APP_ICON,
    APP_SUBTITLE,
    APP_TITLE,
    LEVEL_PER_EMPLOYEE,
    PAGE_LAYOUT,
)
from src.data.loader import (
    FileFormatError,
    JENIS_DATA_LAPORAN_TRAINING,
    JENIS_DATA_MASTER,
    JENIS_DATA_TRAINING,
    KolomHilangError,
    muat_dan_validasi,
    tentukan_jenis_data,
)
from src.data.file_tools import (
    PengolahanFileError,
    hubungkan_laporan_dengan_master,
    siapkan_laporan_training,
)
from src.data.normalizer import jalankan_pipeline_normalisasi
from src.data.training_attempts import agregasi_percobaan_per_karyawan
from src.metrics.kpi import hitung_kpi_dasar, siapkan_data_kpi
from src.components.sidebar_filter import render_sidebar_filters, terapkan_filter
from src.components.kpi_cards import render_kpi_cards
from src.components.executive_dashboard import render_executive_dashboard
from src.components.file_tools import render_file_tools
from src.components.master_dashboard import render_master_dashboard
from src.components.training_results_dashboard import (
    render_detail_hasil_training,
    render_visualisasi_percobaan,
    siapkan_data_dashboard_laporan,
)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout=PAGE_LAYOUT)
    _terapkan_tema_presentasi()
    _render_header()
    render_file_tools()
    st.divider()

    df_master, df_training_raw = _ambil_file_upload_dashboard()
    if df_training_raw is None:
        if df_master is not None:
            _render_master_employee(df_master)
        return

    jenis_training = tentukan_jenis_data(df_training_raw)
    if jenis_training == JENIS_DATA_LAPORAN_TRAINING:
        if df_master is None:
            st.warning(
                "Upload master employee agar NRP pada nilai training dapat "
                "dicocokkan sebelum dashboard ditampilkan."
            )
            return
        _render_dashboard_laporan_training(df_training_raw, df_master)
        return

    _render_dashboard_training_lama(df_training_raw)


def _render_dashboard_training_lama(df_raw) -> None:
    """Pertahankan alur dashboard untuk schema training versi sebelumnya."""
    df = _muat_data_ternormalisasi(df_raw)
    if df is None:
        return

    filter_state = render_sidebar_filters(df)
    df_filtered = terapkan_filter(df, filter_state)

    if len(df_filtered) == 0:
        st.warning("⚠️ Tidak ada data untuk kombinasi filter yang dipilih. Coba ubah filter di sidebar.")
        return

    _render_kpi_section(df_filtered, filter_state.level_agregasi)
    _render_visualisasi_section(df_filtered)


def _render_dashboard_laporan_training(df_training_raw, df_master) -> None:
    """Hubungkan laporan nilai dengan master lalu tampilkan dashboard hasil."""
    try:
        df, df_percobaan, ringkasan, ringkasan_percobaan = (
            _hubungkan_laporan_training_cached(
                df_training_raw,
                df_master,
            )
        )
        df_dashboard = siapkan_data_dashboard_laporan(df)
    except (KeyError, PengolahanFileError) as exc:
        st.error(f"❌ {exc}")
        return

    filter_state = render_sidebar_filters(df_dashboard)
    df_filtered = terapkan_filter(df_dashboard, filter_state)
    if len(df_filtered) == 0:
        st.warning("Tidak ada hasil training untuk filter yang dipilih.")
        return

    st.markdown("## Profil Employee Peserta Training")
    st.caption(
        "Visual master berikut menampilkan karyawan yang memiliki hasil training "
        "dan mengikuti pilihan Filter Utama."
    )
    render_master_dashboard(df_filtered, gunakan_filter_sidebar=False)

    st.divider()
    st.markdown("## Dashboard Hasil Training")
    st.caption(
        "Status akhir dihitung per karyawan dari maksimal tiga percobaan."
    )
    _render_konten_hasil_training(
        df,
        df_percobaan,
        ringkasan,
        ringkasan_percobaan,
        df_filtered,
    )


def _render_konten_hasil_training(
    df,
    df_percobaan,
    ringkasan,
    ringkasan_percobaan,
    df_filtered,
) -> None:
    """Render seluruh KPI, grafik, dan detail hasil training."""
    nrp_terpilih = set(df_filtered["NRP_ID"].dropna().astype("string"))
    mask_percobaan = df_percobaan["NRP_ID"].astype("string").isin(nrp_terpilih)
    if df_filtered["NRP_ID"].isna().any():
        mask_percobaan = mask_percobaan | df_percobaan["NRP_ID"].isna()
    jumlah_percobaan_terfilter = int(mask_percobaan.sum())
    kpi_filtered = hitung_kpi_dasar(df_filtered)

    st.markdown("### Hasil kelulusan training")
    with st.expander("🔗 Ringkasan data terfilter & pencocokan NRP", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Percobaan terfilter", f"{jumlah_percobaan_terfilter:,}")
        c2.metric("Karyawan terfilter", f"{len(df_filtered):,}")
        c3.metric("Lulus terfilter", f"{kpi_filtered['total_lulus']:,}")
        c4.metric("Tidak lulus terfilter", f"{kpi_filtered['total_tidak_lulus']:,}")
        st.caption(
            f"Pencocokan awal sebelum filter: {ringkasan.jumlah_cocok:,} baris "
            f"cocok dan {ringkasan.jumlah_tidak_cocok:,} baris tidak cocok."
        )
        if ringkasan.jumlah_duplikat_master_dihapus > 0:
            st.warning(
                f"Ada {ringkasan.jumlah_duplikat_master_dihapus:,} baris NRP "
                "duplikat di master. Kemunculan pertama yang digunakan."
            )
        if ringkasan.jumlah_tidak_cocok > 0:
            st.caption(
                "Baris yang tidak cocok tetap masuk dashboard, tetapi atribut "
                "master seperti nama, plant, dan jabatan akan kosong."
            )
        if ringkasan_percobaan.jumlah_percobaan_diabaikan > 0:
            st.warning(
                f"Ada {ringkasan_percobaan.jumlah_percobaan_diabaikan:,} "
                "percobaan di atas batas tiga kali; baris tersebut tetap ada "
                "di audit tetapi tidak memengaruhi status akhir."
            )

    render_kpi_cards(
        kpi_filtered,
        label_total="Total Karyawan",
    )
    _render_visualisasi_section(df_filtered, label_unit="Karyawan")
    render_visualisasi_percobaan(df_filtered)
    render_detail_hasil_training(df_filtered, df_percobaan)


def _terapkan_tema_presentasi() -> None:
    st.markdown("""
    <style>
      .stApp {background: linear-gradient(135deg, #FFE66B 0%, #FFF2A3 48%, #FFD83D 100%);}
      .stApp,
      .stApp p,
      .stApp label,
      .stApp button,
      .stApp input,
      .stApp textarea,
      .stApp [role="option"],
      .stApp [data-baseweb="select"] > div,
      .stApp [data-testid="stCaptionContainer"],
      .stApp [data-testid="stDataFrame"],
      .stApp [data-testid="stMetricLabel"],
      .stApp [data-testid="stMetricValue"] {font-weight:700 !important;}
      .stApp h1, .stApp h2, .stApp h3, .stApp h4,
      .stApp h5, .stApp h6 {font-weight:800 !important;}
      .stApp [data-testid="stPlotlyChart"] text {
        color:#000000 !important; fill:#000000 !important;
        font-weight:700 !important;
      }
      .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1500px;}
      [data-testid="stSidebar"] {background: #101010; border-right: 1px solid #333333;}
      [data-testid="stSidebar"]::before {content:""; display:block; height:6px; background:#FFD100;}
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] p,
      [data-testid="stSidebar"] span {color:#FFFFFF;}
      [data-testid="stSidebar"] [data-baseweb="select"] > div,
      [data-testid="stSidebar"] .stButton > button {
        color:#FFFFFF; background:#242424; border-color:#555555;
      }
      [data-testid="stSidebar"] [data-baseweb="tag"] {background:#FFD100;}
      [data-testid="stSidebar"] [data-baseweb="tag"] span {color:#101010;}
      [data-testid="stSidebar"] .stButton > button:hover {
        color:#101010; background:#FFD100; border-color:#FFD100;
      }
      [data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #E0E3E7;
        border-top: 4px solid #FFD100; border-radius: 12px; padding: 16px 18px;
        box-shadow: 0 4px 14px rgba(29,29,27,.07);}
      [data-testid="stMetricLabel"] {color: #5D6268;}
      [data-testid="stMetricValue"] {color: #1D1D1B; font-weight: 750;}
      .eyebrow {color:#0054A6; font-size:.75rem; font-weight:750;
        letter-spacing:.14em; margin-bottom:.25rem;}
      .ut-header {padding-top:.35rem;}
      .ut-header h1 {margin:.1rem 0 .25rem;}
      h1, h2, h3, h4 {color:#1D1D1B;}
      div[data-testid="stAlert"] {border-radius: 10px; border-left:4px solid #FFD100;}
      .stButton > button {border-color:#E0B800; border-radius:8px;}
      .stButton > button:hover {border-color:#1D1D1B; color:#1D1D1B; background:#FFF4B3;}
    </style>
    """, unsafe_allow_html=True)


def _render_header() -> None:
    """Render logo perusahaan di kiri atas dan judul dashboard di kanan."""
    logo, teks = st.columns([1.25, 3.4], gap="large", vertical_alignment="center")
    with logo:
        lokasi_logo = Path(__file__).resolve().parent / "logo.png"
        if lokasi_logo.exists():
            st.image(str(lokasi_logo), use_container_width=True)
    with teks:
        st.markdown(
            """
            <div class="ut-header">
              <div class="eyebrow">PEOPLE DEVELOPMENT ANALYTICS</div>
              <h1>Employee & Training Dashboard</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _ambil_file_upload_dashboard():
    """Render uploader master dan nilai training sebagai dua input terpisah."""
    st.markdown("## Data Dashboard")
    kolom_master, kolom_training = st.columns(2, gap="large")

    with kolom_master:
        st.markdown("#### 1. Master Employee")
        uploaded_master = st.file_uploader(
            "Upload master employee",
            type=["xlsx", "csv"],
            key="dashboard_master_employee",
            help="Minimal memiliki kolom ID, Nama Lengkap, dan NRP.",
        )

    with kolom_training:
        st.markdown("#### 2. Nilai Training")
        uploaded_training = st.file_uploader(
            "Upload hasil merge nilai training",
            type=["xlsx", "csv"],
            key="dashboard_nilai_training",
            help=(
                "NRP dibaca dari First name dan kelulusan dihitung dari "
                "Grade/100.00."
            ),
        )

    df_master = _muat_upload_sesuai_jenis(
        uploaded_master,
        jenis_diizinkan={JENIS_DATA_MASTER},
        label="master employee",
    )
    df_training = _muat_upload_sesuai_jenis(
        uploaded_training,
        jenis_diizinkan={JENIS_DATA_TRAINING, JENIS_DATA_LAPORAN_TRAINING},
        label="nilai training",
    )

    if uploaded_training is None:
        hasil_merge = st.session_state.get("dashboard_nilai_training_hasil_merge")
        if hasil_merge is not None:
            df_training = hasil_merge.copy()
            st.info(
                f"🔄 Menggunakan hasil merge terbaru sebagai Nilai Training "
                f"({len(df_training):,} baris)."
            )

    if uploaded_master is None and uploaded_training is None and df_training is None:
        st.info("⬆️ Silakan upload master employee dan nilai training.")
    return df_master, df_training


def _muat_upload_sesuai_jenis(uploaded_file, jenis_diizinkan: set[str], label: str):
    if uploaded_file is None:
        return None

    try:
        df = muat_dan_validasi(uploaded_file)
    except (KolomHilangError, FileFormatError) as exc:
        st.error(f"❌ Gagal membaca {label}: {exc}")
        return None

    if tentukan_jenis_data(df) not in jenis_diizinkan:
        st.error(f"❌ File yang dipilih bukan {label} yang sesuai.")
        return None
    st.success(f"✅ {uploaded_file.name}: {len(df):,} baris berhasil dimuat.")
    return df


@st.cache_data(show_spinner="Menghitung hasil training & mencocokkan NRP...")
def _hubungkan_laporan_training_cached(df_training_raw, df_master):
    df_training = siapkan_laporan_training(df_training_raw)
    df_terhubung, ringkasan_master = hubungkan_laporan_dengan_master(
        df_training,
        df_master,
    )
    df_karyawan, df_percobaan, ringkasan_percobaan = (
        agregasi_percobaan_per_karyawan(df_terhubung)
    )
    return df_karyawan, df_percobaan, ringkasan_master, ringkasan_percobaan


@st.cache_data(show_spinner="Memproses & menormalisasi data...")
def _jalankan_normalisasi_cached(df_raw):
    """Wrapper cache terpisah dari jalankan_pipeline_normalisasi() di normalizer.py,
    supaya normalizer.py sendiri tetap tidak bergantung pada Streamlit."""
    return jalankan_pipeline_normalisasi(df_raw)


def _muat_data_ternormalisasi(df_raw):
    """Jalankan pipeline normalisasi dan tampilkan ringkasan hasilnya."""
    hasil = _jalankan_normalisasi_cached(df_raw)
    df = hasil["data"]

    if len(df) == 0:
        st.warning("Data hasil normalisasi kosong. Cek kembali isi file yang diupload.")
        return None

    with st.expander("🔍 Ringkasan proses normalisasi data"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Total partisipasi training", len(df))
        c2.metric("Job di luar COP/PTO/ADM_SERVICE (dibuang)", hasil["jumlah_job_dibuang"])
        c3.metric("Data Tidak Lengkap (TEORI kosong)", int((df["RESULT_FINAL"] == "DATA TIDAK LENGKAP").sum()))
        st.caption(
            "Hanya baris dengan JOB = COP, PTO, atau ADM_SERVICE yang masuk ke visualisasi. "
            "Kategori 'DATA TIDAK LENGKAP' muncul saat nilai TEORI kosong/tidak valid."
        )

    # Diagnostik JOB — tampilkan jika ada baris yang dibuang supaya user tahu persis
    # nilai JOB apa yang ada di datanya vs. yang kita filter.
    if hasil["jumlah_job_dibuang"] > 0:
        _render_diagnostik_job(hasil)

    return df


def _render_master_employee(df) -> None:
    """Tampilkan executive overview master employee."""
    render_master_dashboard(df)



def _render_diagnostik_job(hasil: dict) -> None:
    """
    Tampilkan tabel distribusi JOB dari data sebelum filter aktif.
    Tujuan: membantu user mengidentifikasi apakah ada nama JOB di Excel
    yang tidak cocok dengan JOB_FILTER_AKTIF (COP/PTO/ADM_SERVICE),
    misalnya karena perbedaan spasi/underscore atau ada suffix angka.
    """
    from config.settings import JOB_FILTER_AKTIF
    import pandas as pd

    distribusi = hasil.get("distribusi_job_sebelum_filter", {})
    if not distribusi:
        return

    with st.expander("⚠️ Diagnostik JOB — ada baris yang dibuang, klik untuk cek"):
        st.markdown(
            "Tabel di bawah menampilkan **semua nilai JOB yang ditemukan di data** "
            "(setelah normalisasi teks) beserta jumlah barisnya. "
            "Baris dengan JOB **berwarna merah** = **dibuang** dari visualisasi. "
            "Jika ada JOB yang seharusnya masuk tapi ditandai merah, "
            "beri tahu developer agar `JOB_FILTER_AKTIF` diperbarui di `config/settings.py`."
        )

        baris_tabel = []
        for job, jumlah in sorted(distribusi.items(), key=lambda x: -x[1]):
            lolos = job in JOB_FILTER_AKTIF
            baris_tabel.append({
                "Nilai JOB (setelah normalisasi)": job,
                "Jumlah Baris": jumlah,
                "Status": "✅ Masuk dashboard" if lolos else "❌ Dibuang (tidak ada di filter)",
            })

        df_diag = pd.DataFrame(baris_tabel)
        st.dataframe(df_diag, use_container_width=True, hide_index=True)

        job_dibuang = [r["Nilai JOB (setelah normalisasi)"] for r in baris_tabel
                       if r["Status"].startswith("❌")]
        if job_dibuang:
            st.info(
                f"**Nilai JOB yang dibuang:** `{'`, `'.join(job_dibuang)}`\n\n"
                "Jika nilai-nilai di atas seharusnya masuk ke dashboard, "
                "update `JOB_FILTER_AKTIF` di `config/settings.py` dengan nilai yang tepat "
                "(sesuai kolom 'Nilai JOB (setelah normalisasi)' di atas, bukan nilai mentah di Excel)."
            )


def _render_kpi_section(df_filtered, level_agregasi: str) -> None:
    df_kpi = siapkan_data_kpi(df_filtered, level_agregasi)
    kpi = hitung_kpi_dasar(df_kpi)
    label_total = "Total Employee" if level_agregasi == LEVEL_PER_EMPLOYEE else "Total Partisipasi"
    render_kpi_cards(kpi, label_total=label_total)


def _render_visualisasi_section(
    df_filtered,
    label_unit: str = "Partisipasi",
) -> None:
    render_executive_dashboard(df_filtered, label_unit=label_unit)


if __name__ == "__main__":
    main()
