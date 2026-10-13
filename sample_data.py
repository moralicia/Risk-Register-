"""Fictional sample risks for demo mode.

All data below is invented ("PT Contoh Sejahtera") so the public portfolio
deployment never contains any real company information.
"""
from __future__ import annotations

from datetime import date, timedelta


def _in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def sample_risks() -> list[dict]:
    today = date.today().isoformat()
    base = {"last_updated": today, "updated_by": "demo"}
    risks = [
        dict(kode="RSK-001", objective="Menjaga imbal hasil portofolio investasi sesuai target",
             potensi="Kenaikan suku bunga menurunkan nilai pasar portofolio obligasi",
             category="Market", cause="Perubahan kebijakan suku bunga bank sentral",
             sev_desc="Penurunan nilai wajar obligasi (mark-to-market)", sev_rp=12000,
             divisi="Investasi", dept="Fixed Income", unit="Portfolio Management", external="",
             control_exists="Ada", control_desc="Limit duration portofolio dan stress test bulanan",
             inh_l=4, inh_i=4, mit_option="Reduce",
             mit_desc="Diversifikasi tenor dan lindung nilai suku bunga",
             res_l=3, res_i=3, status="Mitigating", review_date=_in_days(20)),
        dict(kode="RSK-002", objective="Melindungi nilai aset dalam mata uang asing",
             potensi="Pelemahan rupiah terhadap USD meningkatkan kewajiban dalam valas",
             category="Market", cause="Volatilitas nilai tukar akibat sentimen global",
             sev_desc="Kerugian selisih kurs atas posisi valas terbuka", sev_rp=6500,
             divisi="Treasury", dept="Foreign Exchange", unit="Dealing Room", external="Bank mitra",
             control_exists="Ada", control_desc="Limit posisi valas terbuka harian",
             inh_l=4, inh_i=3, mit_option="Transfer",
             mit_desc="Kontrak forward untuk posisi valas material",
             res_l=3, res_i=2, status="Monitoring", review_date=_in_days(35)),
        dict(kode="RSK-003", objective="Mencapai pertumbuhan aset investasi yang berkelanjutan",
             potensi="Penurunan tajam harga saham pada portofolio ekuitas",
             category="Market", cause="Koreksi pasar modal dan sentimen negatif",
             sev_desc="Penurunan nilai portofolio saham", sev_rp=18000,
             divisi="Investasi", dept="Equity", unit="Portfolio Management", external="",
             control_exists="Ada", control_desc="Stop-loss dan batas konsentrasi per emiten",
             inh_l=4, inh_i=5, mit_option="Reduce",
             mit_desc="Rebalancing portofolio dan penurunan eksposur saham",
             res_l=3, res_i=4, status="Open", review_date=_in_days(-12)),
        dict(kode="RSK-004", objective="Menjaga kualitas aset investasi",
             potensi="Gagal bayar penerbit obligasi korporasi",
             category="Credit", cause="Penurunan kinerja keuangan penerbit",
             sev_desc="Kehilangan pokok dan kupon obligasi", sev_rp=9000,
             divisi="Risk Management", dept="Credit Risk", unit="Credit Analysis", external="Lembaga pemeringkat",
             control_exists="Ada", control_desc="Minimum rating investasi dan pemantauan triwulanan",
             inh_l=3, inh_i=5, mit_option="Reduce",
             mit_desc="Penguatan analisis kredit dan batas eksposur per penerbit",
             res_l=2, res_i=4, status="Mitigating", review_date=_in_days(10)),
        dict(kode="RSK-005", objective="Memenuhi kewajiban kepada pemegang polis tepat waktu",
             potensi="Aset investasi sulit dicairkan saat kebutuhan klaim meningkat",
             category="Liquidity", cause="Porsi aset kurang likuid terlalu besar",
             sev_desc="Penjualan aset dengan diskon besar untuk memenuhi klaim", sev_rp=5000,
             divisi="Treasury", dept="Liquidity Management", unit="Cash Management", external="",
             control_exists="Ada", control_desc="Proyeksi arus kas dan batas minimum aset likuid",
             inh_l=3, inh_i=4, mit_option="Reduce",
             mit_desc="Menaikkan porsi instrumen likuid dan fasilitas pendanaan standby",
             res_l=2, res_i=3, status="Monitoring", review_date=_in_days(45)),
        dict(kode="RSK-006", objective="Menjaga akurasi valuasi dan pencatatan transaksi",
             potensi="Kesalahan input transaksi atau valuasi instrumen",
             category="Operational", cause="Proses manual dan keterbatasan validasi sistem",
             sev_desc="Salah saji laporan posisi investasi", sev_rp=800,
             divisi="Operasional", dept="Investment Operations", unit="Settlement", external="",
             control_exists="Tidak Ada", control_desc="",
             inh_l=3, inh_i=3, mit_option="Reduce",
             mit_desc="Otomasi validasi dan rekonsiliasi harian",
             res_l=2, res_i=2, status="Open", review_date=_in_days(15)),
        dict(kode="RSK-007", objective="Mematuhi ketentuan regulator",
             potensi="Pelanggaran batas penempatan investasi yang ditetapkan regulator",
             category="Compliance", cause="Pemantauan batas belum terotomasi",
             sev_desc="Sanksi administratif dan reputasi", sev_rp=2500,
             divisi="Kepatuhan", dept="Compliance", unit="Regulatory Monitoring", external="Regulator",
             control_exists="Ada", control_desc="Pengecekan batas sebelum transaksi (pre-trade check)",
             inh_l=2, inh_i=5, mit_option="Reduce",
             mit_desc="Dashboard pemantauan batas otomatis",
             res_l=1, res_i=4, status="Monitoring", review_date=_in_days(60)),
        dict(kode="RSK-008", objective="Menjaga diversifikasi portofolio",
             potensi="Konsentrasi portofolio pada satu sektor ekonomi",
             category="Strategic", cause="Preferensi alokasi tanpa batas sektor yang tegas",
             sev_desc="Kerugian terkonsentrasi bila sektor tertekan", sev_rp=7500,
             divisi="Investasi", dept="Strategic Asset Allocation", unit="Portfolio Strategy", external="",
             control_exists="Ada", control_desc="Review alokasi aset tiap triwulan",
             inh_l=4, inh_i=4, mit_option="Accept",
             mit_desc="Menetapkan batas sektor dan memantau secara berkala",
             res_l=4, res_i=3, status="Open", review_date=_in_days(-3)),
    ]
    for risk in risks:
        risk.update(base)
    return risks
