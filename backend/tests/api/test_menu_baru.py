"""Uji menu yang dipesan tapi belum ada di katalog: dikelompokkan kode, ditambah penjual, pesanan lama dicocokkan ulang."""

from sqlalchemy import select

from app.api.menu_baru import kunci_menu
from app.db import Batch, Customer, Order, OrderItem, Product


def test_kunci_menu():
    assert kunci_menu("Nasi Ayam Geprek 2 ya kak") == "nasi ayam geprek"
    assert kunci_menu("2x nasi ayam geprek") == "nasi ayam geprek"


def _pesan_geprek(db, nama, qty, batch_id="b-1"):
    c = Customer(batch_id=batch_id, nama_tampil=nama)
    db.add(c)
    db.flush()
    o = Order(batch_id=batch_id, customer_id=c.id, status="perlu_cek", jam_kirim="12:00", alamat="Asrama", tanda=["item_tidak_dikenal"])
    o.items = [OrderItem(teks_asli=f"nasi ayam geprek {qty}", qty=qty)]
    db.add(o)
    db.commit()
    return o.id


def test_menu_belum_dikenal_ditambah_lalu_pesanan_dicocokkan(client, db, katalog, batch):
    a = _pesan_geprek(db, "Kak Nadia", 2)
    b = _pesan_geprek(db, "Mas Rio", 1)
    daftar = client.get("/api/menu-belum-dikenal").json()
    assert daftar == [{"kunci": "nasi ayam geprek", "nama": "Nasi Ayam Geprek", "jumlah_pesanan": 2, "total_porsi": 3, "contoh": "nasi ayam geprek 2"}]

    res = client.post("/api/menu-belum-dikenal/tambahkan", json={"kunci": "nasi ayam geprek", "nama": "Nasi Ayam Geprek", "harga": 16000})
    assert res.status_code == 201 and res.json()["pesanan_dicocokkan"] == 2
    db.expire_all()
    produk = db.scalar(select(Product).where(Product.nama == "Nasi Ayam Geprek"))
    assert produk.pemilik == "demo" and produk.harga == 16000
    nadia = db.get(Order, a)
    assert nadia.total == 32000 and "item_tidak_dikenal" not in nadia.tanda
    assert db.get(Order, b).items[0].harga_satuan == 16000
    assert client.get("/api/menu-belum-dikenal").json() == []
    # Menu yang sudah ada tidak bisa ditambah dua kali.
    assert client.post("/api/menu-belum-dikenal/tambahkan", json={"kunci": "x y", "nama": "nasi ayam geprek", "harga": 1}).status_code == 409


def test_menu_belum_dikenal_akun_lain_tidak_terlihat(client, db, katalog):
    from datetime import date

    db.add(Batch(id="b-asing", pemilik="bu_sari", nama="X", tanggal_kirim=date(2026, 11, 14)))
    db.commit()
    _pesan_geprek(db, "Orang lain", 5, batch_id="b-asing")
    assert client.get("/api/menu-belum-dikenal").json() == []
    client.post("/api/menu-belum-dikenal/tambahkan", json={"kunci": "nasi ayam geprek", "nama": "Nasi Ayam Geprek", "harga": 16000})
    db.expire_all()
    asing = db.scalar(select(Order).where(Order.batch_id == "b-asing"))
    assert asing.items[0].product_id is None  # pesanan akun lain tidak ikut dicocokkan
