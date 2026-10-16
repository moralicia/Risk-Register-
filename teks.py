"""teks.py - SEMUA teks yang tampil di halaman ada di file ini.

CARA MENGUBAH TEKS (tidak perlu paham Python):
  1. Cari baris yang teksnya ingin Anda ubah.
  2. Ubah HANYA tulisan di dalam tanda kutip "...".
     Contoh:  APP_TITLE = "Risk Register"   ->   APP_TITLE = "Daftar Risiko Perusahaan"
  3. Jangan hapus tanda kutip, tanda sama dengan (=), atau nama di sebelah kiri.
  4. Jangan memakai tanda kutip ganda (") di dalam teks. Pakai tanda kutip tunggal (') bila perlu.
  5. Simpan (Commit changes di GitHub), tunggu 1-2 menit, lalu muat ulang aplikasi.

Catatan:
  - Tulisan yang diapit **dua bintang** akan ditampilkan tebal.
  - Emoji boleh diganti atau dihapus.
  - Baris yang diawali tanda # hanyalah catatan dan tidak tampil di layar.
  - Judul kolom tabel/Sheet ada di file schema.py (HEADERS dan COMPACT_LABELS), bukan di sini.
"""

# ---------------------------------------------------------------------------
# Judul utama
# ---------------------------------------------------------------------------
APP_ICON = "📋"                      # ikon di judul dan tab browser
APP_TITLE = "Risk Register"          # judul besar halaman + judul tab browser
APP_SUBTITLE = (                     # kalimat kecil di bawah judul
    "Daftar risiko, penilaian, dan rencana mitigasi. "
    "Risk owner mengisi data di tab **Daftar Risiko**; manajemen melihat tab **Ringkasan**."
)

# ---------------------------------------------------------------------------
# Nama tab
# ---------------------------------------------------------------------------
TAB_REGISTER = "📝 Daftar Risiko"
TAB_SUMMARY = "📊 Ringkasan & Peta Risiko"

# ---------------------------------------------------------------------------
# Layar login
# ---------------------------------------------------------------------------
LOGIN_CAPTION = "Silakan masuk untuk melanjutkan."
LOGIN_PASSWORD_LABEL = "Password"
LOGIN_BUTTON = "Masuk"
LOGIN_ERROR = "Password salah."

# ---------------------------------------------------------------------------
# Tombol di bagian atas
# ---------------------------------------------------------------------------
BTN_REFRESH = "🔄 Muat ulang"
BTN_SIGNOUT = "Keluar"
BTN_ADD = "➕ Tambah risiko baru"
BTN_EDIT = "✏️ Ubah risiko terpilih"
BTN_EXPORT = "⬇️ Unduh CSV"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
DEMO_BANNER = (
    "**Mode demo:** data di bawah adalah contoh fiktif dan hanya tersimpan sementara. "
    "Sambungkan Google Sheets agar data tersimpan permanen dan dapat dipakai bersama."
)
NO_PASSWORD_WARNING = (
    "Aplikasi belum diproteksi password: siapa pun yang memiliki link dapat mengubah data. "
    "Atur password di bagian [auth] pada secrets."
)

# ---------------------------------------------------------------------------
# Tab "Daftar Risiko"
# ---------------------------------------------------------------------------
HOWTO_EDITOR = (
    "**Cara pakai:** klik **➕ Tambah risiko baru** untuk mengisi risiko baru. "
    "Untuk mengubah, **centang satu baris** di tabel lalu klik **✏️ Ubah risiko terpilih**."
)
HOWTO_VIEWER = "Mode lihat saja: Anda dapat melihat dan mengunduh data, tetapi tidak dapat mengubahnya."
SEARCH_PLACEHOLDER = "🔎 Cari berdasarkan kode, tujuan, atau potensi risiko..."
FILTER_EXPANDER = "Filter lainnya (divisi, kategori, status, level risiko)"

# Dua pilihan tampilan tabel (teksnya boleh diganti, tetapi jangan dikosongkan)
VIEW_COMPACT = "Tampilan ringkas"
VIEW_FULL = "Tampilan lengkap"

# ---------------------------------------------------------------------------
# Tab "Ringkasan & Peta Risiko" - kartu angka (judul + keterangan saat kursor diarahkan)
# ---------------------------------------------------------------------------
KPI_TOTAL = "Total risiko"
KPI_TOTAL_TIP = "Jumlah seluruh risiko yang tercatat."
KPI_CRITICAL = "Sangat tinggi"
KPI_CRITICAL_TIP = "Risiko dengan level target Very High (skor 20-25)."
KPI_HIGH = "Tinggi"
KPI_HIGH_TIP = "Risiko dengan level target High (skor 12-16)."
KPI_OVERDUE = "Review terlambat"
KPI_OVERDUE_TIP = "Tanggal review sudah lewat dan status belum Closed."
KPI_AVG = "Rata-rata skor target"
KPI_AVG_TIP = "Rata-rata Tingkat Risiko (Targeted), skala 1-25."

# ---------------------------------------------------------------------------
# Tab "Ringkasan & Peta Risiko" - heat map dan risiko teratas
# ---------------------------------------------------------------------------
HEATMAP_TITLE = "Peta risiko (heat map)"
HEATMAP_VIEW_LABEL = "Pilih sudut pandang"
HEATMAP_VIEW_TARGETED = "Target setelah mitigasi (Targeted)"
HEATMAP_VIEW_INHERENT = "Sebelum pengendalian (Inherent)"
TOP_RISKS_TITLE = "Risiko teratas"
TOP_RISKS_CAPTION = "Diurutkan berdasarkan level target (Targeted) tertinggi."
TOP_RISKS_EMPTY = "Belum ada risiko tercatat."

HEATMAP_TOLERANCE_LABEL = "Batas toleransi risiko"   # tulisan di dekat garis putus-putus merah
HEATMAP_MORE = "more"                                 # tampil di kotak yang berisi lebih dari 4 risiko
