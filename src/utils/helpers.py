"""
Fungsi utilitas umum yang dipakai lintas modul (formatting angka,
persen, dsb.) — supaya format tampilan konsisten di semua komponen,
tidak ditulis ulang berbeda-beda di tiap file chart/KPI.
"""


def format_angka(nilai: int) -> str:
    """Format angka dengan pemisah ribuan, contoh: 1234 -> '1,234'."""
    return f"{nilai:,}"


def format_persen(nilai: float, desimal: int = 1) -> str:
    """Format angka jadi persen dengan jumlah desimal tertentu, contoh: 78.456 -> '78.5%'."""
    return f"{nilai:.{desimal}f}%"


def singkat_teks(teks: str, panjang_maksimal: int = 30) -> str:
    """
    Potong teks yang kepanjangan untuk ditampilkan di label chart
    (misal nama Modul Training yang panjang), tambahkan '...' di akhir.
    """
    teks = str(teks)
    if len(teks) <= panjang_maksimal:
        return teks
    return teks[: panjang_maksimal - 3] + "..."