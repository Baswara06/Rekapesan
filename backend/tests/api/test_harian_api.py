"""Uji endpoint buku pesanan harian dan lunas untuk pesanan terkirim (COD)."""

from app.db import Order
from tests.test_harian import SAMPEL, _ekstraktor, katalog_ratri  # noqa: F401 - fixture dipakai lewat nama


def test_endpoint_harian_dan_lunas_untuk_pesanan_terkirim(client, db, katalog_ratri, monkeypatch):
    from app import extractor as modul_extractor

    monkeypatch.setattr(modul_extractor, "extract_orders", _ekstraktor)
    teks = SAMPEL.decode()
    p = client.post("/api/impor/pratinjau", json={"text": teks})
    assert p.status_code == 200 and p.json()["penjual"] == "Ratri"
    r = client.post("/api/impor", json={"text": teks})
    assert r.status_code == 200 and r.json()["total"]["pesanan_dibuat"] == 2

    papan = client.get("/api/ringkasan").json()
    oid = papan["hari"][1]["jam"][0]["pesanan"][0]["id"]
    assert client.post(f"/api/orders/{oid}/payment-confirm").status_code == 409  # belum disetujui
    client.post(f"/api/orders/{oid}/approve")
    assert client.patch(f"/api/orders/{oid}", json={"status": "dikirim"}).status_code == 200
    res = client.post(f"/api/orders/{oid}/payment-confirm")  # COD: sudah dikirim, baru bayar
    assert res.status_code == 200 and res.json()["status"] == "dikirim"

    pesanan = client.get("/api/ringkasan").json()["hari"][1]["jam"][0]["pesanan"][0]
    assert (pesanan["status_papan"], pesanan["bayar"], pesanan["saran"]) == ("selesai", "lunas", [])
    assert db.get(Order, oid).status == "dikirim"


def test_endpoint_impor_harian_tanpa_menu_ditolak(client):
    res = client.post("/api/impor", json={"text": SAMPEL.decode()})
    assert res.status_code == 409 and res.json()["error"]["kode"] == "katalog_kosong"
