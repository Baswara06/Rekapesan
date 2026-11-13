import asyncio

from sqlalchemy import func, select

from app.db import Batch, Customer, MessageRow, Order, OrderItem
from app.services import import_batch
from tests.test_import_service import CONTOH, Tiruan


def test_buat_dan_daftar_batch(client):
    res = client.post("/api/batches", json={"nama": "PO Sabtu", "tanggal_kirim": "2026-11-14", "tanggal_mulai": "2026-11-13"})
    assert res.status_code == 201
    b = res.json()
    assert b["nama"] == "PO Sabtu" and b["tanggal_kirim"] == "2026-11-14" and b["tanggal_mulai"] == "2026-11-13"
    assert [x["id"] for x in client.get("/api/batches").json()] == [b["id"]]


def test_tanggal_mulai_opsional_dan_tidak_boleh_setelah_tanggal_kirim(client):
    ok = client.post("/api/batches", json={"nama": "PO", "tanggal_kirim": "2026-11-14"})
    assert ok.status_code == 201 and ok.json()["tanggal_mulai"] is None
    res = client.post("/api/batches", json={"nama": "PO", "tanggal_kirim": "2026-11-14", "tanggal_mulai": "2026-11-15"})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"
    res = client.post("/api/batches", json={"nama": "", "tanggal_kirim": "bukan-tanggal"})
    assert res.status_code == 422


def test_hapus_batch_ikut_menghapus_pesan_mentah_pembeli_dan_pesanan(client, db, katalog, batch):
    asyncio.run(import_batch(db, "b-1", CONTOH, extractor=Tiruan()))
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(MessageRow)) == 9

    res = client.delete("/api/batches/b-1")
    assert res.status_code == 204 and res.content == b""

    db.expire_all()
    for model in (Batch, MessageRow, Customer, Order, OrderItem):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    res = client.delete("/api/batches/b-1")
    assert res.status_code == 404 and res.json()["error"]["kode"] == "tidak_ditemukan"
