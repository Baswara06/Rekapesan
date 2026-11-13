import time

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import Settings
from app.main import app

KUNCI_UJI = "kunci-uji-yang-cukup-panjang"


@pytest.fixture
def akun(monkeypatch):
    monkeypatch.setattr(
        security, "get_settings", lambda: Settings(demo_username="demo", demo_password="rahasia", app_secret_key=KUNCI_UJI)
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


def _palsu(kunci: str, username: str = "penyusup") -> str:
    """Token buatan sendiri yang ditandatangani dengan `kunci` tebakan penyerang."""
    import base64
    import hashlib
    import hmac
    import json

    isi = base64.urlsafe_b64encode(json.dumps({"sub": username, "exp": int(time.time()) + 3600}).encode()).rstrip(b"=").decode()
    tanda = base64.urlsafe_b64encode(hmac.new(kunci.encode(), isi.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{isi}.{tanda}"


@pytest.mark.parametrize("kunci", ["", "ganti-dengan-string-acak-panjang", "pendek"])
def test_kunci_kosong_bawaan_atau_pendek_mematikan_login_dan_token_palsu_ditolak(monkeypatch, tamu, kunci):
    monkeypatch.setattr(
        security, "get_settings", lambda: Settings(demo_username="demo", demo_password="rahasia", app_secret_key=kunci)
    )
    res = tamu.post("/api/auth/login", json={"username": "demo", "password": "rahasia"})
    assert res.status_code == 401 and "APP_SECRET_KEY" in res.json()["error"]["pesan"]
    palsu = _palsu(kunci)
    assert security.periksa_token(palsu) is None
    assert tamu.get("/api/batches", headers={"Authorization": f"Bearer {palsu}"}).status_code == 401
    with pytest.raises(ValueError):
        security.buat_token("demo")


def test_kunci_yang_benar_tetap_menolak_token_dari_kunci_lain(akun, tamu):
    assert security.periksa_token(_palsu("tebakan-penyerang-yang-panjang")) is None
    assert security.periksa_token(_palsu(KUNCI_UJI)) == "penyusup"  # tanda tangan sah hanya bila kunci diketahui


def test_demo_password_kosong_memberi_pesan_yang_jelas(monkeypatch, tamu):
    monkeypatch.setattr(security, "get_settings", lambda: Settings(demo_password="", app_secret_key=KUNCI_UJI))
    res = tamu.post("/api/auth/login", json={"username": "demo", "password": ""})
    assert res.status_code == 401 and "DEMO_PASSWORD" in res.json()["error"]["pesan"]
