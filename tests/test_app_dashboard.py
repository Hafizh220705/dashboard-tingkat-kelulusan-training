"""Test orkestrasi dashboard gabungan pada app.py."""

from types import SimpleNamespace

import pandas as pd

import app
from src.components.sidebar_filter import FilterState


def test_master_dan_training_selalu_dirender_pada_halaman_yang_sama(monkeypatch):
    df_karyawan = pd.DataFrame(
        {
            "NRP_ID": ["123", "456"],
            "NILAI_FINAL": [90, 70],
            "RESULT_FINAL": ["LULUS", "TIDAK LULUS"],
            "AREA": ["A", "B"],
            "ID": [1, 2],
            "Nama Lengkap": ["Andi", "Siti"],
            "NRP": [123, 456],
        }
    )
    df_percobaan = df_karyawan.copy()
    ringkasan = SimpleNamespace()
    ringkasan_percobaan = SimpleNamespace()
    panggilan = []

    monkeypatch.setattr(
        app,
        "_hubungkan_laporan_training_cached",
        lambda *_: (df_karyawan, df_percobaan, ringkasan, ringkasan_percobaan),
    )
    monkeypatch.setattr(
        app,
        "siapkan_data_dashboard_laporan",
        lambda df: df,
    )
    monkeypatch.setattr(
        app,
        "render_sidebar_filters",
        lambda _df: FilterState(area=["A"]),
    )
    monkeypatch.setattr(
        app,
        "render_master_dashboard",
        lambda df, gunakan_filter_sidebar: panggilan.append(
            ("master", gunakan_filter_sidebar, df)
        ),
    )
    monkeypatch.setattr(
        app,
        "_render_konten_hasil_training",
        lambda *args: panggilan.append(("training", args[-1])),
    )
    monkeypatch.setattr(app.st, "markdown", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app.st, "divider", lambda *_args, **_kwargs: None)

    app._render_dashboard_laporan_training(pd.DataFrame(), pd.DataFrame())

    assert [item[0] for item in panggilan] == ["master", "training"]
    assert panggilan[0][1] is False
    assert panggilan[0][2]["NRP_ID"].tolist() == ["123"]
    assert panggilan[1][1]["NRP_ID"].tolist() == ["123"]
