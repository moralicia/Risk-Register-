"""kriteria.py - Tabel kriteria penilaian (Likelihood dan Dampak) untuk risk owner.

Isi tabel ada di bagian DATA di bawah. Cara mengubah:
  - Ubah teks di dalam tanda kutip "...". Jangan hapus koma di akhir baris.
  - Setiap baris harus berisi TEPAT 5 teks (untuk nilai 1 sampai 5).
  - Untuk menambah baris dampak, salin satu baris ("Keuangan" / "Non Keuangan", ...) lalu ubah isinya.
"""
import html

# ---------------------------------------------------------------------------
# DATA: Tabel Likelihood (Tingkat Keterjadian Risiko)
# ---------------------------------------------------------------------------
LIKELIHOOD_LEVELS = ["Rare", "Unlikely", "Moderate", "Likely", "Almost Certain"]

# (nama baris, [teks nilai 1, 2, 3, 4, 5], baris kuantitatif yang disorot?)
LIKELIHOOD_ROWS = [
    ("Deskripsi Kualitatif",
     ["Hampir tidak pernah terjadi", "Jarang terjadi", "Cukup sering terjadi",
      "Sering terjadi", "Sangat sering terjadi"], False),
    ("Keterjadian risiko dalam Jangka Waktu 1 tahun",
     ["Dalam jangka waktu 1 tahun hanya 1-5 kejadian",
      "Dalam jangka waktu 1 tahun antara 6-10 kejadian",
      "Dalam jangka waktu 1 tahun antara 11-15 kejadian",
      "Dalam jangka waktu 1 tahun antara 16-20 kejadian",
      "Dalam jangka waktu 1 tahun lebih dari 20 kejadian"], True),
    ("Peluang keterjadian",
     ["P < 10% dari total kejadian", "10% < P ≤ 20% dari total kejadian",
      "20% < P ≤ 30% dari total kejadian", "30% < P ≤ 40% dari total kejadian",
      "P > 40% dari total kejadian"], False),
    ("Insidentil",
     ["Kemungkinan Terjadi 1 kali dalam 5 tahun", "Kemungkinan Terjadi 2 s/d 5 kali dalam 5 tahun",
      "Kemungkinan Terjadi 6 s/d 10 kali dalam 5 tahun", "Kemungkinan Terjadi 11 s/d 20 kali dalam 5 tahun",
      "Kemungkinan Terjadi lebih dari 20 kali dalam 5 tahun"], False),
]

# ---------------------------------------------------------------------------
# DATA: Tabel Dampak (Tingkat Keparahan Dampak)
# ---------------------------------------------------------------------------
IMPACT_LEVELS = ["Insignificant", "Minor", "Moderate", "Major", "Catastrophic"]

# (kelompok, kriteria, [teks nilai 1, 2, 3, 4, 5], baris kuantitatif yang disorot?)
IMPACT_ROWS = [
    ("Keuangan", "Kerugian Finansial",
     ["<= Rp 5 Juta", "> Rp 5 juta s/d Rp 10 juta", "> Rp 10 juta s/d Rp 25 juta",
      "> Rp 25 juta s/d Rp 50 juta", "> Rp 50 juta"], True),
    ("Non Keuangan", "Keluhan Pelanggan (Customer Satisfaction Index)",
     ["CSI 78%", "CSI 76% - 78%", "CSI 74% - 76%", "CSI 73% - 74%", "CSI <= 72%"], False),
    ("Non Keuangan", "Reputasi (area Publikasi)",
     ["Tidak berdampak pada reputasi", "publikasi negatif pada area operasional setempat",
      "publikasi negatif pada area kantor cabang", "publikasi negatif pada area kantor wilayah",
      "publikasi negatif pada skala nasional"], False),
    ("Non Keuangan", "Keluhan Kepegawaian",
     ["Keluhan pegawai dapat diselesaikan oleh satuan kerja terkait",
      "Keluhan pegawai dapat diselesaikan oleh atasan terkait",
      "Keluhan pegawai dapat diselesaikan oleh atasan terkait dan HRD",
      "Keluhan pegawai dapat diselesaikan oleh HRD dan Direksi",
      "Keluhan pegawai dapat diselesaikan oleh Depnaker"], False),
    ("Non Keuangan", "Kesehatan dan Keselamatan (Tingkat cedera)",
     ["Tindakan berbahaya", "cidera kecil (mampu kembali bekerja di hari yang sama)",
      "cidera ringan (tidak mampu melakukan tugas > 1 hari s/d 3 minggu)",
      "cidera berat (tidak mampu melakukan tugas > 3 minggu atau mengakibatkan cacat tetap)",
      "kejadian fatal/kematian"], False),
    ("Non Keuangan", "Keterlambatan Pencapaian Tujuan Strategis",
     ["Tujuan strategis terlambat < 40% dari target waktu pencapaian",
      "Tujuan strategis terlambat > 40% s/d 60% dari target waktu pencapaian",
      "Tujuan strategis terlambat > 60% s/d 80% dari target waktu pencapaian",
      "Tujuan strategis terlambat > 80% s/d 100% dari target waktu pencapaian",
      "Tujuan strategis terlambat > 100% dari target waktu pencapaian"], False),
    ("Non Keuangan", "Delik Hukum/Legal",
     ["Tidak ada tuntutan hukum", "Adanya Penuntutan namun tidak terbukti",
      "Proses hukum yang dapat diselesaikan secara musyawarah",
      "adanya litigasi dan class action", "Vonis bersalah oleh pengadilan"], False),
    ("Non Keuangan", "Peringatan atau pembatasan aktivitas oleh regulasi/regulator",
     ["Peringatan informal/Verbal", "Peringatan tertulis tanpa sanksi", "Peringatan tertulis dikenakan sanksi",
      "Penghentian sementara aktivitas", "Pembekuan Usaha"], False),
    ("Non Keuangan", "Tingkat efisiensi (Budget)",
     ["Tidak ada variasi dari anggaran", "Kenaikan s/d 1% pada Anggaran",
      "Kenaikan > 1% s/d 5% pada Anggaran", "Kenaikan > 5% s/d 10% pada Anggaran",
      "Kenaikan >10% pada Anggaran"], False),
    ("Non Keuangan", "Aplikasi dan infrastruktur IT",
     ["Tidak berfungsi selama 1 jam", "Tidak berfungsi selama 3 jam", "Tidak berfungsi selama 1 hari",
      "Tidak berfungsi selama 2 hari", "Tidak berfungsi selama 3 hari"], False),
    # Baris berikutnya di tabel asli terpotong pada screenshot. Tambahkan di sini dengan pola yang sama.
]

# ---------------------------------------------------------------------------
# Tampilan (tidak perlu diubah)
# ---------------------------------------------------------------------------
HEADER_BG = "#DCE6F1"
HIGHLIGHT_BG = "#FFF2CC"
_CELL = "border:1px solid #4b5563;padding:6px 8px;color:#111827;vertical-align:middle;font-size:0.82em"


def _e(text) -> str:
    return html.escape(str(text))


def _levels_header(levels, group_title: str, first_cols: int, first_label: str) -> str:
    head = f"background:{HEADER_BG};font-weight:700;text-align:center"
    names = "".join(f"<td style='{_CELL};{head}'>{_e(n)}</td>" for n in levels)
    values = "".join(f"<td style='{_CELL};{head}'>Nilai : {i}</td>" for i, _ in enumerate(levels, 1))
    return (
        f"<tr><td rowspan='3' colspan='{first_cols}' style='{_CELL};{head}'>{_e(first_label)}</td>"
        f"<td colspan='5' style='{_CELL};{head}'>{_e(group_title)}</td></tr>"
        f"<tr>{names}</tr><tr>{values}</tr>"
    )


def likelihood_table_html() -> str:
    rows = _levels_header(LIKELIHOOD_LEVELS, "Tingkat Keterjadian Risiko", 1, "Tipe Kejadian/Event")
    for label, values, highlight in LIKELIHOOD_ROWS:
        bg = f"background:{HIGHLIGHT_BG};" if highlight else "background:#ffffff;"
        cells = "".join(f"<td style='{_CELL};{bg}text-align:center'>{_e(v)}</td>" for v in values)
        rows += f"<tr><td style='{_CELL};{bg}font-weight:700;text-align:center'>{_e(label)}</td>{cells}</tr>"
    return f"<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%'>{rows}</table></div>"


def impact_table_html() -> str:
    rows = _levels_header(IMPACT_LEVELS, "Tingkat Keparahan Dampak", 2, "Kriteria Penilaian")
    groups = [g for g, *_ in IMPACT_ROWS]
    for idx, (group, label, values, highlight) in enumerate(IMPACT_ROWS):
        bg = f"background:{HIGHLIGHT_BG};" if highlight else "background:#ffffff;"
        group_cell = ""
        if idx == 0 or groups[idx - 1] != group:  # merge the group cell down (Keuangan / Non Keuangan)
            span = 1
            for later in groups[idx + 1:]:
                if later != group:
                    break
                span += 1
            group_cell = (f"<td rowspan='{span}' style='{_CELL};background:#ffffff;font-weight:700'>"
                          f"{_e(group)}</td>")
        cells = "".join(f"<td style='{_CELL};{bg}text-align:center'>{_e(v)}</td>" for v in values)
        rows += f"<tr>{group_cell}<td style='{_CELL};{bg}font-weight:700'>{_e(label)}</td>{cells}</tr>"
    return f"<div style='overflow-x:auto'><table style='border-collapse:collapse;width:100%'>{rows}</table></div>"
