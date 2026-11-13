import asyncio

from sqlalchemy import select

from app.db import Order
from app.services import build_recap, build_shopping_list, import_batch
from tests.test_import_service import CONTOH, Tiruan, pesanan


def test_rekap_hanya_menghitung_pesanan_yang_disetujui(db, katalog, batch):
    asyncio.run(import_batch(db, "b-1", CONTOH, extractor=Tiruan()))
    rekap = build_recap(db, "b-1")
    assert rekap == {"produksi": [], "urutan_kirim": [], "omzet": 0, "belum_bayar": [], "menunggu_persetujuan": 3}
    assert build_shopping_list(db, "b-1") == []

    rina, anton, budi = pesanan(db, "Bu Rina"), pesanan(db, "Pak Anton"), pesanan(db, "Mas Budi")
    rina.status, rina.jam_kirim = "dikonfirmasi", "12:00"
    anton.status = "dibayar"
    budi.status = "batal"
    db.commit()

    rekap = build_recap(db, "b-1")
    assert rekap["produksi"] == [
        {"product_id": "p-ayam", "nama": "Ayam Bakar", "qty": 4, "stok_sisa": 26},
        {"product_id": "p-teh", "nama": "Es Teh", "qty": 1, "stok_sisa": None},
    ]
    assert rekap["omzet"] == 54000 + 23000
    assert rekap["belum_bayar"] == [{"order_id": rina.id, "nama": "Bu Rina", "total": 54000}]
    assert rekap["menunggu_persetujuan"] == 0
    assert len(rekap["urutan_kirim"]) == 1 and rekap["urutan_kirim"][0]["jam"] == "12:00"
    assert set(rekap["urutan_kirim"][0]["order_ids"]) == {rina.id, anton.id}


def test_urutan_kirim_per_jam_dan_tanpa_jam_di_akhir(db, katalog, batch):
    asyncio.run(import_batch(db, "b-1", CONTOH, extractor=Tiruan()))
    for o, jam in zip(db.scalars(select(Order).order_by(Order.total)), ["13:00", None, "11:30"], strict=True):
        o.status, o.jam_kirim = "dikonfirmasi", jam
    db.commit()
    assert [u["jam"] for u in build_recap(db, "b-1")["urutan_kirim"]] == ["11:30", "13:00", None]


def test_daftar_belanja_dari_resep(db, katalog, batch):
    asyncio.run(import_batch(db, "b-1", CONTOH, extractor=Tiruan()))
    for nama in ("Bu Rina", "Pak Anton"):
        pesanan(db, nama).status = "dikonfirmasi"
    db.commit()
    # 4 ayam bakar: 4 x 0.25 kg ayam, 4 x 0.1 kg beras. Es teh tanpa resep.
    assert build_shopping_list(db, "b-1") == [
        {"bahan": "Ayam", "jumlah": 1.0, "satuan": "kg"},
        {"bahan": "Beras", "jumlah": 0.4, "satuan": "kg"},
    ]
