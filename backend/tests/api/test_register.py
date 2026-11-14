"""Uji register akun penjual dan pemisahan data antar-akun."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import security
from app.core.config import Settings
from app.db import Batch, Product, User, init_db
from app.main import app

KUNCI_UJI = "kunci-uji-yang-cukup-panjang"


@pytest.fixture
def akun(monkeypatch):
    monkeypatch.setattr(
        security, "get_settings", lambda: Settings(demo_username="demo", demo_password="rahasia", app_secret_key=KUNCI_UJI)
    )


def _daftar(c: TestClient, username: str, password: str = "sandi-rahasia") -> dict[str, str]:
    res = c.post("/api/auth/register", json={"username": username, "password": password})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_register_lalu_login_dan_sandi_tidak_disimpan_mentah(akun, tamu, db):
    _daftar(tamu, "Bu_Sari")  # disimpan huruf kecil
    user = db.scalar(select(User).where(User.username == "bu_sari"))
    assert user is not None and "sandi-rahasia" not in user.password_hash
    res = tamu.post("/api/auth/login", json={"username": "bu_sari", "password": "sandi-rahasia"})
    assert res.status_code == 200 and security.periksa_token(res.json()["token"]) == "bu_sari"
    assert tamu.post("/api/auth/login", json={"username": "bu_sari", "password": "salah-sandi"}).status_code == 401


@pytest.mark.parametrize(
    ("username", "password", "status"),
    [("ab", "sandi-rahasia", 422), ("nama spasi", "sandi-rahasia", 422), ("bu_sari", "pendek", 422), ("demo", "sandi-rahasia", 409)],
)
def test_register_ditolak(akun, tamu, username, password, status):
    assert tamu.post("/api/auth/register", json={"username": username, "password": password}).status_code == status


def test_username_ganda_ditolak(akun, tamu):
    _daftar(tamu, "bu_sari")
    res = tamu.post("/api/auth/register", json={"username": "BU_SARI", "password": "lain-lagi-123"})
    assert res.status_code == 409 and res.json()["error"]["kode"] == "username_dipakai"


def test_register_mati_bila_kunci_lemah(monkeypatch, tamu):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(app_secret_key=""))
    assert tamu.post("/api/auth/register", json={"username": "bu_sari", "password": "sandi-rahasia"}).status_code == 401


def test_data_tiap_akun_terpisah(akun, tamu, katalog, batch, pesanan_contoh):
    """Akun baru tidak melihat atau mengubah katalog, batch, dan pesanan akun demo."""
    h = _daftar(tamu, "bu_sari")
    assert tamu.get("/api/products", headers=h).json() == []
    assert tamu.get("/api/batches", headers=h).json() == []
    for path in ("/api/batches/b-1/orders", "/api/batches/b-1/recap", "/api/batches/b-1/shopping-list"):
        assert tamu.get(path, headers=h).status_code == 404
    assert tamu.patch("/api/products/p-ayam", json={"harga": 1}, headers=h).status_code == 404
    assert tamu.delete("/api/batches/b-1", headers=h).status_code == 404
    assert tamu.post("/api/batches/b-1/import", json={"text": "x"}, headers=h).status_code == 404

    demo = {"Authorization": f"Bearer {security.buat_token('demo')}"}
    order_id = tamu.get("/api/batches/b-1/orders", headers=demo).json()[0]["id"]
    asing = [
        tamu.get(f"/api/orders/{order_id}", headers=h),
        tamu.get(f"/api/orders/{order_id}/reply", headers=h),
        tamu.patch(f"/api/orders/{order_id}", json={"alamat": "x"}, headers=h),
        tamu.post(f"/api/orders/{order_id}/approve", headers=h),
        tamu.post(f"/api/orders/{order_id}/reject", headers=h),
        tamu.post(f"/api/orders/{order_id}/payment-confirm", headers=h),
        tamu.post(f"/api/orders/{order_id}/payment-proof", files={"file": ("a.png", b"x", "image/png")}, headers=h),
        tamu.post("/api/batches/b-1/orders/approve-clean", headers=h),
        tamu.post("/api/agent/ask", json={"batch_id": "b-1", "pertanyaan": "siapa belum bayar"}, headers=h),
    ]
    assert [r.status_code for r in asing] == [404] * len(asing)
    assert tamu.get(f"/api/orders/{order_id}", headers=demo).json()["status"] == "perlu_cek"  # tidak tersentuh


    # Menu dan batch buatan akun baru hanya terlihat olehnya.
    tamu.post("/api/products", json={"nama": "Kue Lumpur", "harga": 3000}, headers=h)
    tamu.post("/api/batches", json={"nama": "PO Sabtu", "tanggal_kirim": "2026-11-14"}, headers=h)
    assert [p["nama"] for p in tamu.get("/api/products", headers=h).json()] == ["Kue Lumpur"]
    assert "Kue Lumpur" not in [p["nama"] for p in tamu.get("/api/products", headers=demo).json()]
    assert [b["nama"] for b in tamu.get("/api/batches", headers=demo).json()] == ["PO Jumat"]


def test_ubah_pesanan_tidak_bisa_memakai_menu_akun_lain(akun, tamu, db, katalog, batch, pesanan_contoh):
    db.add(Product(id="p-asing", pemilik="bu_sari", nama="Kue Lumpur", harga=1, stok_harian=None))
    db.commit()
    demo = {"Authorization": f"Bearer {security.buat_token('demo')}"}
    order_id = tamu.get("/api/batches/b-1/orders", headers=demo).json()[0]["id"]
    res = tamu.patch(
        f"/api/orders/{order_id}", json={"items": [{"product_id": "p-asing", "teks_asli": "kue 2", "qty": 2}]}, headers=demo
    )
    assert res.status_code == 200 and res.json()["items"][0]["product_id"] is None


def test_database_lama_diberi_kolom_pemilik_dan_data_diserahkan_ke_demo(tmp_path):
    from datetime import date

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine(f"sqlite:///{tmp_path / 'lama.db'}")
    with engine.begin() as conn:  # skema sebelum ada register
        conn.execute(text("CREATE TABLE batches (id VARCHAR(36) PRIMARY KEY, nama VARCHAR(120), tanggal_kirim DATE, tanggal_mulai DATE, dibuat_pada DATETIME)"))
        conn.execute(text("INSERT INTO batches (id, nama, tanggal_kirim) VALUES ('b-lama', 'PO lama', '2026-11-13')"))
    init_db(engine)
    init_db(engine)  # aman diulang
    with Session(engine) as s:
        assert s.get(Batch, "b-lama").pemilik == "demo"
        s.add(Batch(id="b-baru", pemilik="bu_sari", nama="PO", tanggal_kirim=date(2026, 11, 14)))
        s.commit()
        assert s.get(Batch, "b-baru").pemilik == "bu_sari"
