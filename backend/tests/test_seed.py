"""Uji data demo: isi sekali, idempoten, dan hasilnya dihitung mesin aturan (bukan angka tulisan tangan)."""

from sqlalchemy import func, select

from app.db import Batch, Order, Product
from app.seed import NAMA_BATCH, isi_data_demo


def test_seed_mengisi_katalog_batch_dan_pesanan(db):
    ringkasan = isi_data_demo(db)
    assert "3 pesanan" in ringkasan and "bukan keluaran LLM" in ringkasan
    db.expire_all()

    assert {p.nama for p in db.scalars(select(Product))} == {"Ayam Bakar", "Nasi Lodeh", "Es Teh"}
    batch = db.scalar(select(Batch).where(Batch.nama == NAMA_BATCH))
    assert batch is not None and batch.tanggal_mulai is not None

    pesanan = {o.customer.nama_tampil: o for o in db.scalars(select(Order))}
    assert set(pesanan) == {"Bu Rina", "Pak Anton", "Mas Budi"}
    assert pesanan["Bu Rina"].total == 54000 and pesanan["Bu Rina"].tanda == ["jam_kosong"]
    assert pesanan["Pak Anton"].total == 23000
    assert "jumlah_tidak_wajar" in pesanan["Mas Budi"].tanda  # contoh tanda kuning untuk demo
    assert {o.status for o in pesanan.values()} == {"perlu_cek"}  # penjual yang menyetujui, bukan seed


def test_seed_idempoten_dan_reset_tidak_menggandakan(db):
    isi_data_demo(db)
    assert "sudah ada" in isi_data_demo(db)
    isi_data_demo(db, reset=True)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Batch)) == 1
    assert db.scalar(select(func.count()).select_from(Product)) == 3
    assert db.scalar(select(func.count()).select_from(Order)) == 3
