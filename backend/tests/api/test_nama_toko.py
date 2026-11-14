"""Uji nama toko: diisi saat register, dibaca dan diubah lewat /auth/me, dipakai di balasan konfirmasi."""

import pytest
from fastapi.testclient import TestClient

from app.api.balasan import susun_balasan
from app.core import security
from app.core.config import Settings
from tests.api.conftest import id_pesanan

KUNCI_UJI = "kunci-uji-yang-cukup-panjang"


@pytest.fixture
def akun(monkeypatch):
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: Settings(
            demo_username="demo", demo_password="rahasia", demo_nama_toko="Katering Dewi", app_secret_key=KUNCI_UJI
        ),
    )


def _daftar(c: TestClient, **isi) -> dict[str, str]:
    res = c.post("/api/auth/register", json={"username": "bu_sari", "password": "sandi-rahasia", **isi})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


def test_nama_toko_disimpan_saat_register_dengan_spasi_dirapikan(akun, tamu):
    h = _daftar(tamu, nama_toko="  Dapur   Bu Sari ")
    assert tamu.get("/api/auth/me", headers=h).json() == {"username": "bu_sari", "nama_toko": "Dapur Bu Sari"}


def test_register_tanpa_nama_toko_tetap_bisa(akun, tamu):
    h = _daftar(tamu)
    assert tamu.get("/api/auth/me", headers=h).json()["nama_toko"] is None


@pytest.mark.parametrize("nama", ["A", "x" * 61])
def test_nama_toko_terlalu_pendek_atau_panjang_ditolak(akun, tamu, nama):
    res = tamu.post("/api/auth/register", json={"username": "bu_sari", "password": "sandi-rahasia", "nama_toko": nama})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"


def test_ubah_nama_toko(akun, tamu):
    h = _daftar(tamu)
    res = tamu.patch("/api/auth/me", json={"nama_toko": "Dapur Sari"}, headers=h)
    assert res.status_code == 200 and res.json()["nama_toko"] == "Dapur Sari"
    assert tamu.get("/api/auth/me", headers=h).json()["nama_toko"] == "Dapur Sari"
    assert tamu.patch("/api/auth/me", json={"nama_toko": "   "}, headers=h).status_code == 422


def test_akun_demo_memakai_nama_toko_dari_env_dan_tidak_bisa_diubah(akun, tamu):
    token = tamu.post("/api/auth/login", json={"username": "demo", "password": "rahasia"}).json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    assert tamu.get("/api/auth/me", headers=h).json() == {"username": "demo", "nama_toko": "Katering Dewi"}
    assert tamu.patch("/api/auth/me", json={"nama_toko": "Lain"}, headers=h).status_code == 409


def test_me_wajib_login(tamu):
    assert tamu.get("/api/auth/me").status_code == 401
    assert tamu.patch("/api/auth/me", json={"nama_toko": "Dapur"}).status_code == 401


def test_balasan_konfirmasi_menyebut_nama_toko(akun, client, pesanan_contoh):
    oid = id_pesanan(client, "Bu Rina")
    client.patch(f"/api/orders/{oid}", json={"jam_kirim": "12:00"})
    client.post(f"/api/orders/{oid}/approve")
    teks = client.get(f"/api/orders/{oid}/reply").json()["teks"]
    assert teks.splitlines()[0] == "Halo Bu Rina, pesanan kamu di Katering Dewi sudah kami catat ya:"


def test_susun_balasan_tanpa_nama_toko_tidak_berubah():
    item = [{"nama": "Es Teh", "qty": 1, "harga_satuan": 5000, "catatan_item": None, "dikenal": True}]
    assert susun_balasan("Pak Anton", item, 5000, None, None, None).startswith("Halo Pak Anton, pesanan kamu sudah")
    assert susun_balasan("Pak Anton", item, 5000, None, None, None, nama_toko="Katering Dewi").startswith(
        "Halo Pak Anton, pesanan kamu di Katering Dewi sudah"
    )
