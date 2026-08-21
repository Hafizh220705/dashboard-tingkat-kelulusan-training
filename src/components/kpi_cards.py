"""
Komponen untuk merender KPI cards di bagian atas dashboard.

Modul ini HANYA bertanggung jawab atas tampilan (rendering st.metric).
Perhitungan angka KPI sudah selesai dilakukan oleh
`src.metrics.kpi.hitung_kpi_dasar()` -- komponen ini tinggal terima
hasilnya dalam bentuk dict dan render, TIDAK melakukan kalkulasi apapun.

Pemisahan ini memastikan kalau nanti mentor minta ubah cara hitung KPI,
yang diubah cukup `src/metrics/kpi.py`, dan kalau mentor minta ubah
TAMPILAN kpi card (misal ganti warna, tambah ikon), yang diubah cukup
file ini -- dua hal ini tidak akan pernah tabrakan di file yang sama.
"""

import streamlit as st

def render_kpi_cards(kpi: dict, label_total: str = "Total Peserta") -> None:
    """
    Render 6 KPI card dalam satu baris menggunakan st.columns + st.metric.

    Parameters
    ----------
    kpi : dict
        Output dari `src.metrics.kpi.hitung_kpi_dasar()`. Harus punya key:
        total, total_lulus, total_tidak_lulus, total_tidak_lengkap,
        pass_rate, fail_rate.
    label_total : str
        Label untuk card pertama. Beda tergantung level agregasi yang
        dipilih user di sidebar -- "Total Employee" kalau level per
        employee, "Total Partisipasi" kalau level per partisipasi.
        Dioper dari app.py, bukan ditentukan di sini, supaya komponen ini
        tidak perlu tahu soal konsep "level agregasi" sama sekali.
    """
    kolom_wajib = {
        "total", "total_lulus", "total_tidak_lulus",
        "total_tidak_lengkap", "pass_rate", "fail_rate",
    }
    kolom_hilang = kolom_wajib - kpi.keys()
    if kolom_hilang:
        raise KeyError(
            f"Dict kpi tidak lengkap, key hilang: {kolom_hilang}. "
            "Pastikan dict berasal dari hitung_kpi_dasar()."
        )

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    k1.metric(label_total, f"{kpi['total']:,}")
    k2.metric("Total Lulus", f"{kpi['total_lulus']:,}")
    k3.metric("Total Tidak Lulus", f"{kpi['total_tidak_lulus']:,}")
    k4.metric("Pass Rate", f"{kpi['pass_rate']:.1f}%")
    k5.metric("Fail Rate", f"{kpi['fail_rate']:.1f}%")
    k6.metric("Data Tidak Lengkap", f"{kpi['total_tidak_lengkap']:,}")