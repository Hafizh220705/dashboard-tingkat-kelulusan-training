"""Normalisasi nilai per soal dan agregasi percobaan training karyawan."""

from dataclasses import dataclass

import pandas as pd

from config.settings import (
    STATUS_DATA_TIDAK_LENGKAP,
    STATUS_LULUS,
    STATUS_TIDAK_LULUS,
    THRESHOLD_KELULUSAN,
)


BATAS_PERCOBAAN = 3


@dataclass(frozen=True)
class RingkasanAgregasiPercobaan:
    jumlah_karyawan: int
    jumlah_percobaan: int
    jumlah_percobaan_diabaikan: int
    jumlah_baris_tanpa_nrp: int


def _angka_nilai(series: pd.Series) -> pd.Series:
    teks = (
        series.astype("string")
        .str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(teks, errors="coerce")


def normalisasi_nilai_pertanyaan(df: pd.DataFrame) -> pd.DataFrame:
    """Satukan dua variasi skala pertanyaan menjadi nilai efektif.

    Untuk pertanyaan 1–5, kolom skala 10 menjadi pilihan utama. Jika kosong
    atau tidak numerik, nilai diambil dari kolom skala 20. Pertanyaan 6–10
    hanya memakai kolom skala 10. Selain nilai mentah, dibuat persentase agar
    skor dengan maksimum berbeda tetap dapat dibandingkan.
    """
    hasil = df.copy()

    for nomor in range(1, 11):
        kolom_10 = f"Q. {nomor} /10.00"
        nilai_10 = (
            _angka_nilai(hasil[kolom_10])
            if kolom_10 in hasil.columns
            else pd.Series(float("nan"), index=hasil.index)
        )
        nilai_10 = nilai_10.where(nilai_10.between(0, 10))

        nilai_efektif = nilai_10.copy()
        maksimal = pd.Series(10.0, index=hasil.index).where(nilai_10.notna())
        sumber = pd.Series("/10.00", index=hasil.index).where(nilai_10.notna())

        if nomor <= 5:
            kolom_20 = f"Q. {nomor} /20.00"
            nilai_20 = (
                _angka_nilai(hasil[kolom_20])
                if kolom_20 in hasil.columns
                else pd.Series(float("nan"), index=hasil.index)
            )
            nilai_20 = nilai_20.where(nilai_20.between(0, 20))
            pakai_skala_20 = nilai_efektif.isna() & nilai_20.notna()
            nilai_efektif = nilai_efektif.where(~pakai_skala_20, nilai_20)
            maksimal = maksimal.where(~pakai_skala_20, 20.0)
            sumber = sumber.where(~pakai_skala_20, "/20.00")

        hasil[f"Q. {nomor} NILAI"] = nilai_efektif
        hasil[f"Q. {nomor} MAKSIMAL"] = maksimal
        hasil[f"Q. {nomor} PERSEN"] = (nilai_efektif / maksimal * 100).round(2)
        hasil[f"Q. {nomor} SUMBER"] = sumber

    return hasil


def _tanggal_urutan(df: pd.DataFrame) -> pd.Series:
    tanggal = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    for kolom in ["Completed", "Started"]:
        if kolom not in df.columns:
            continue
        kandidat = pd.to_datetime(df[kolom], errors="coerce", format="mixed")
        tanggal = tanggal.fillna(kandidat)
    return tanggal


def agregasi_percobaan_per_karyawan(
    df: pd.DataFrame,
    threshold: float = THRESHOLD_KELULUSAN,
    batas_percobaan: int = BATAS_PERCOBAAN,
) -> tuple[pd.DataFrame, pd.DataFrame, RingkasanAgregasiPercobaan]:
    """Bentuk satu status akhir per NRP dari maksimal tiga percobaan.

    Percobaan diurutkan dari kolom ``Completed``, lalu ``Started``, dan terakhir
    urutan baris sumber. Baris di atas batas tetap disimpan untuk audit tetapi
    tidak memengaruhi nilai/status akhir.
    """
    kolom_wajib = ["NRP_ID", "NILAI_FINAL", "RESULT_FINAL"]
    kolom_hilang = [kolom for kolom in kolom_wajib if kolom not in df.columns]
    if kolom_hilang:
        raise KeyError(
            f"Data percobaan belum lengkap: {', '.join(kolom_hilang)}."
        )
    if batas_percobaan < 1:
        raise ValueError("Batas percobaan minimal satu.")

    percobaan = df.copy().reset_index(drop=True)
    percobaan["__URUTAN_ASLI__"] = range(len(percobaan))
    percobaan["__TANGGAL_URUTAN__"] = _tanggal_urutan(percobaan)
    percobaan["__KUNCI_KARYAWAN__"] = percobaan["NRP_ID"].astype("string")

    mask_tanpa_nrp = percobaan["__KUNCI_KARYAWAN__"].isna()
    percobaan.loc[mask_tanpa_nrp, "__KUNCI_KARYAWAN__"] = [
        f"__TANPA_NRP_{indeks}__" for indeks in percobaan.index[mask_tanpa_nrp]
    ]

    percobaan = percobaan.sort_values(
        ["__KUNCI_KARYAWAN__", "__TANGGAL_URUTAN__", "__URUTAN_ASLI__"],
        na_position="last",
        kind="stable",
    )
    percobaan["PERCOBAAN_KE"] = (
        percobaan.groupby("__KUNCI_KARYAWAN__", sort=False).cumcount() + 1
    )
    percobaan["DIGUNAKAN_DALAM_HASIL"] = percobaan["PERCOBAAN_KE"] <= batas_percobaan

    data_digunakan = percobaan[percobaan["DIGUNAKAN_DALAM_HASIL"]]
    baris_karyawan: list[pd.Series] = []

    for _, grup in data_digunakan.groupby("__KUNCI_KARYAWAN__", sort=False):
        nilai = pd.to_numeric(grup["NILAI_FINAL"], errors="coerce")
        if nilai.notna().any():
            indeks_terbaik = nilai.idxmax()
            baris = grup.loc[indeks_terbaik].copy()
            nilai_terbaik = float(nilai.max())
            status_akhir = (
                STATUS_LULUS
                if nilai_terbaik >= threshold
                else STATUS_TIDAK_LULUS
            )
        else:
            baris = grup.iloc[-1].copy()
            nilai_terbaik = float("nan")
            status_akhir = STATUS_DATA_TIDAK_LENGKAP

        for urutan in range(1, batas_percobaan + 1):
            nilai_percobaan = nilai[grup["PERCOBAAN_KE"] == urutan]
            baris[f"NILAI_PERCOBAAN_{urutan}"] = (
                nilai_percobaan.iloc[0] if len(nilai_percobaan) else float("nan")
            )

        percobaan_lulus = grup.loc[
            nilai.ge(threshold).fillna(False), "PERCOBAAN_KE"
        ]
        baris["JUMLAH_PERCOBAAN"] = len(grup)
        baris["NILAI_TERBAIK"] = nilai_terbaik
        baris["NILAI_FINAL"] = nilai_terbaik
        baris["RESULT_FINAL"] = status_akhir
        baris["LULUS_PADA_PERCOBAAN"] = (
            int(percobaan_lulus.iloc[0]) if len(percobaan_lulus) else pd.NA
        )
        baris_karyawan.append(baris)

    hasil_karyawan = pd.DataFrame(baris_karyawan).reset_index(drop=True)
    if len(hasil_karyawan):
        hasil_karyawan["LULUS_PADA_PERCOBAAN"] = hasil_karyawan[
            "LULUS_PADA_PERCOBAAN"
        ].astype("Int64")

    kolom_internal = [
        "__URUTAN_ASLI__",
        "__TANGGAL_URUTAN__",
        "__KUNCI_KARYAWAN__",
    ]
    hasil_karyawan = hasil_karyawan.drop(columns=kolom_internal, errors="ignore")
    percobaan = percobaan.drop(columns=kolom_internal, errors="ignore")

    ringkasan = RingkasanAgregasiPercobaan(
        jumlah_karyawan=len(hasil_karyawan),
        jumlah_percobaan=len(percobaan),
        jumlah_percobaan_diabaikan=int((~percobaan["DIGUNAKAN_DALAM_HASIL"]).sum()),
        jumlah_baris_tanpa_nrp=int(mask_tanpa_nrp.sum()),
    )
    return hasil_karyawan, percobaan, ringkasan
