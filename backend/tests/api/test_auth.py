import time

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import Settings
from app.main import app


@pytest.fixture
def akun(monkeypatch):
    monkeypatch.setattr(
        security, "get_settings", lambda: Settings(demo_username="demo", demo_password="rahasia", app_secret_key="kunci-uji")
    )


def test_login_berhasil_lalu_token_dipakai(akun, tamu):
    res = tamu.post("/api/auth/login", json={"username": "demo", "password": "rahasia"})
    assert res.status_code == 200
    token = res.json()["token"]
    assert tamu.get("/api/products").status_code == 401
    assert tamu.get("/api/products", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_login_salah_ditolak_dengan_galat_seragam(akun, tamu):
    res = tamu.post("/api/auth/login", json={"username": "demo", "password": "salah"})
    assert res.status_code == 401
    assert res.json() == {"error": {"kode": "tidak_terautentikasi", "pesan": "Nama pengguna atau kata sandi salah."}}


def test_kata_sandi_kosong_di_env_menolak_semua_login(monkeypatch, tamu):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(demo_username="demo", demo_password=""))
    assert tamu.post("/api/auth/login", json={"username": "demo", "password": ""}).status_code == 401


def test_tanpa_token_atau_token_rusak_ditolak(akun, tamu):
    res = tamu.get("/api/batches")
    assert res.status_code == 401 and res.json()["error"]["kode"] == "tidak_terautentikasi"
    for header in ("Bearer", "Bearer abc", "Basic abc", "Bearer a.b"):
        assert tamu.get("/api/batches", headers={"Authorization": header}).status_code == 401


def test_token_dipalsukan_atau_kedaluwarsa_ditolak(akun):
    token = security.buat_token("demo")
    isi, _, _ = token.partition(".")
    assert security.periksa_token(token) == "demo"
    assert security.periksa_token(f"{isi}.tandatangan-palsu") is None
    lama = security.buat_token("demo", sekarang=time.time() - security.MASA_BERLAKU_DETIK - 10)
    assert security.periksa_token(lama) is None


def test_health_dan_login_tetap_terbuka(akun):
    c = TestClient(app)
    assert c.get("/api/health").status_code == 200
