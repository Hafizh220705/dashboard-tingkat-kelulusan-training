"""
Konfigurasi & konstanta global untuk Training Performance Dashboard.
Semua nilai yang berpotensi berubah (nama kolom, threshold, warna, dsb.)
DIPUSATKAN di sini — jangan hardcode di file lain.
"""

# =========================================================
# METADATA APLIKASI
# =========================================================
APP_TITLE = "Training Performance Dashboard"
APP_SUBTITLE = "PT United Tractors Tbk — Monitoring Kelulusan Training Karyawan"
APP_ICON = "📊"
PAGE_LAYOUT = "wide"


# =========================================================
# STRUKTUR KOLOM DATASET
# =========================================================
# Kolom yang WAJIB ada di file yang diupload user.
# Kalau salah satu kolom ini hilang, aplikasi harus stop & kasih pesan error.
KOLOM_WAJIB = [
    "NRP LAMA",     # identifier utama; NRP BARU sering kosong di data asli
    "AREA",
    "JOB",
    "MODUL TRAINING",
    "TAHUN",
    "TEORI",
    "RESULT",
]

# Penanda minimum untuk mengenali file master employee. Kolom lain pada master
# bersifat informatif dan boleh berubah mengikuti kebutuhan HR.
KOLOM_WAJIB_MASTER = ["ID", "Nama Lengkap", "NRP"]

# Template laporan hasil training. Pada export yang dipakai saat ini, NRP
# karyawan berada di "First name" dan nilai akhir berada di "Grade/100.00".
KOLOM_WAJIB_LAPORAN_TRAINING = [
    "Last name",
    "First name",
    "Email address",
    "Status",
    "Started",
    "Completed",
    "Duration",
    "Grade/100.00",
    "Q. 1 /10.00",
    "Q. 2 /10.00",
    "Q. 3 /10.00",
    "Q. 4 /10.00",
    "Q. 5 /10.00",
    "Q. 6 /10.00",
    "Q. 7 /10.00",
    "Q. 8 /10.00",
    "Q. 9 /10.00",
    "Q. 10 /10.00",
    "Q. 1 /20.00",
    "Q. 2 /20.00",
    "Q. 3 /20.00",
    "Q. 4 /20.00",
    "Q. 5 /20.00",
]
KOLOM_NRP_LAPORAN_TRAINING = "First name"
KOLOM_NILAI_LAPORAN_TRAINING = "Grade/100.00"

# Kolom kategorikal yang perlu dinormalisasi teksnya (trim, uppercase, dsb.)
KOLOM_KATEGORI = [
    "AREA",
    "SUPPORT AREA",
    "JOB",
    "MODUL TRAINING",
    "BULAN",
    "SPESIALISASI",
    "GROUP",
]

# Kolom numerik yang perlu dipastikan tipe datanya
KOLOM_NUMERIK = ["TEORI", "PRAKTEK"]

# Kolom tanggal
KOLOM_TANGGAL = ["START", "END"]

# Kombinasi kolom untuk deteksi baris duplikat.
# Pakai NRP_ID (kolom yang dibuat normalizer.normalisasi_nrp) bukan NRP BARU
# langsung, supaya fallback ke NRP LAMA juga ikut terdeteksi sebagai duplikat.
KOLOM_KUNCI_DUPLIKAT = ["NRP_ID", "MODUL TRAINING", "TAHUN"]


# =========================================================
# BUSINESS RULE — KELULUSAN
# =========================================================
# Threshold nilai TEORI untuk menentukan LULUS/TIDAK LULUS.
# RESULT_FINAL selalu diklasifikasikan ulang dari TEORI (bukan dari kolom RESULT asli).
# TEORI >= 80 → LULUS, < 80 → TIDAK LULUS, NaN → DATA TIDAK LENGKAP.
THRESHOLD_KELULUSAN = 80

# Mapping label RESULT final yang dipakai konsisten di seluruh aplikasi
STATUS_LULUS = "LULUS"
STATUS_TIDAK_LULUS = "TIDAK LULUS"
STATUS_DATA_TIDAK_LENGKAP = "DATA TIDAK LENGKAP"

URUTAN_STATUS = [STATUS_LULUS, STATUS_TIDAK_LULUS, STATUS_DATA_TIDAK_LENGKAP]


# =========================================================
# TAMPILAN — WARNA & STYLE
# =========================================================
WARNA_STATUS = {
    STATUS_LULUS: "#2E7D32",              # hijau
    STATUS_TIDAK_LULUS: "#C62828",        # merah
    STATUS_DATA_TIDAK_LENGKAP: "#9E9E9E", # abu-abu
}

# Warna per KPI card (dipakai kalau nanti custom KPI card, bukan st.metric bawaan)
WARNA_KPI = {
    "total": "#1565C0",       # biru
    "lulus": "#2E7D32",       # hijau
    "tidak_lulus": "#C62828", # merah
    "pass_rate": "#2E7D32",
    "fail_rate": "#C62828",
    "tidak_lengkap": "#757575",
}


# =========================================================
# FILTER JOB AKTIF
# =========================================================
# ⚠️ Hanya baris dengan JOB di daftar ini yang masuk ke visualisasi.
# Nilai harus UPPERCASE — konsisten dengan hasil normalisasi_teks().
JOB_FILTER_AKTIF = ["COP", "PTO", "ADM_SERVICE"]


# =========================================================
# LEVEL AGREGASI KPI
# =========================================================
LEVEL_PER_PARTISIPASI = "Per Partisipasi (Employee x Modul)"
LEVEL_PER_EMPLOYEE = "Per Employee (unique)"

PILIHAN_LEVEL_AGREGASI = [LEVEL_PER_PARTISIPASI, LEVEL_PER_EMPLOYEE]

# =========================================================
# MAPPING BULAN INDONESIA -> INGGRIS
# =========================================================

MAPPING_BULAN_INDONESIA = {
    "Januari": "January",
    "Februari": "February",
    "Maret": "March",
    "April": "April",
    "Mei": "May",
    "Juni": "June",
    "Juli": "July",
    "Agustus": "August",
    "September": "September",
    "Oktober": "October",
    "November": "November",
    "Desember": "December",
}
