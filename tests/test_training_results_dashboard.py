"""Test alur laporan nilai training menuju dashboard."""

import pandas as pd

from config.settings import (
    KOLOM_WAJIB_LAPORAN_TRAINING,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
)
from src.components.training_results_dashboard import (
    siapkan_data_dashboard_laporan,
)
from src.data.file_tools import (
    hubungkan_laporan_dengan_master,
    siapkan_laporan_training,
)
from src.data.loader import (
    JENIS_DATA_LAPORAN_TRAINING,
    deteksi_baris_header,
    tentukan_jenis_data,
)
from src.metrics.kpi import hitung_kpi_dasar


def _laporan_training() -> pd.DataFrame:
    data = {kolom: [None, None] for kolom in KOLOM_WAJIB_LAPORAN_TRAINING}
    data.update(
        {
            "First name": ["00123", "456"],
            "Grade/100.00": [80, 79],
            "Completed": ["10 August 2026, 3:22 PM", "11 August 2025, 8:00 AM"],
            "SUMBER_FILE": ["Safety.xlsx", "Technical.xlsx"],
        }
    )
    return pd.DataFrame(data)


def test_loader_mengenali_schema_laporan_nilai_training():
    assert tentukan_jenis_data(_laporan_training()) == JENIS_DATA_LAPORAN_TRAINING


def test_deteksi_header_laporan_training_setelah_metadata():
    header = KOLOM_WAJIB_LAPORAN_TRAINING
    preview = pd.DataFrame(
        [
            ["Report generated", None] + [None] * (len(header) - 2),
            [None] * len(header),
            header,
        ]
    )

    assert deteksi_baris_header(preview) == 2


def test_adapter_dashboard_memakai_atribut_master_dan_sumber_file():
    training = siapkan_laporan_training(_laporan_training())
    master = pd.DataFrame(
        {
            "ID": [1, 2],
            "Nama Lengkap": ["Andi", "Siti"],
            "NRP": [123, 456],
            "Plant": ["Jakarta", "Balikpapan"],
            "Jabatan": ["Mekanik", "Operator"],
        }
    )
    terhubung, _ = hubungkan_laporan_dengan_master(training, master)

    hasil = siapkan_data_dashboard_laporan(terhubung)

    assert hasil["AREA"].tolist() == ["Jakarta", "Balikpapan"]
    assert hasil["JOB"].tolist() == ["Mekanik", "Operator"]
    assert hasil["MODUL TRAINING"].tolist() == ["Safety", "Technical"]
    assert hasil["TAHUN"].tolist() == [2026, 2025]
    assert hasil["RESULT_FINAL"].tolist() == [STATUS_LULUS, STATUS_TIDAK_LULUS]


def test_alur_end_to_end_menghasilkan_kpi_lulus_dan_tidak_lulus():
    training = siapkan_laporan_training(_laporan_training())
    master = pd.DataFrame(
        {
            "ID": [1, 2],
            "Nama Lengkap": ["Andi", "Siti"],
            "NRP": [123, 456],
        }
    )
    terhubung, ringkasan = hubungkan_laporan_dengan_master(training, master)
    dashboard = siapkan_data_dashboard_laporan(terhubung)

    kpi = hitung_kpi_dasar(dashboard)

    assert ringkasan.jumlah_cocok == 2
    assert kpi["total"] == 2
    assert kpi["total_lulus"] == 1
    assert kpi["total_tidak_lulus"] == 1
    assert kpi["pass_rate"] == 50.0
