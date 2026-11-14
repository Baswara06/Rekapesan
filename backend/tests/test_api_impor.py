"""Uji endpoint impor: multipart, JSON, dan bentuk galat seragam."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import extractor as modul_extractor
from app.db import Batch, get_db, init_db, make_engine
from app.core.security import require_login
from app.main import app
from app.schemas import Extraction

TEKS = "12/11/26 09.15 - Bu Rina: ayam bakar 2 ya\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = make_engine(f"sqlite:///{tmp_path / 'api.db'}")
    init_db(engine)
    with Session(engine) as s:
        s.add(Batch(id="b-1", pemilik="demo", nama="PO",
 tanggal_kirim=date(2026, 11, 13)))
        s.commit()

    def _db():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    async def tiruan(sender_messages, catalog, active_order=None):
        return Extraction(intent="bukan_pesanan")

    monkeypatch.setattr(modul_extractor, "extract_orders", tiruan)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_login] = lambda: "demo"  # uji ini fokus ke impor, bukan login
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def test_impor_json_lalu_berkas_yang_sama_dilewati(client):
    res = client.post("/api/batches/b-1/import", json={"text": TEKS})
    assert res.status_code == 200 and res.json()["pesan_baru"] == 1
    res = client.post("/api/batches/b-1/import", files={"file": ("chat.txt", TEKS.encode(), "text/plain")})
    assert res.json() == {"pesan_baru": 0, "pesan_dilewati": 1, "pesanan_dibuat": 0, "pesanan_diubah": 0, "perlu_cek": 0}


def test_impor_form_text(client):
    assert client.post("/api/batches/b-1/import", data={"text": TEKS}).json()["pesan_baru"] == 1


def test_galat_seragam(client):
    res = client.post("/api/batches/tidak-ada/import", json={"text": TEKS})
    assert res.status_code == 404 and res.json()["error"]["kode"] == "tidak_ditemukan"
    res = client.post("/api/batches/b-1/import", json={"text": "bukan chat"})
    assert res.status_code == 400 and res.json()["error"]["kode"] == "format_file_tidak_dikenal"
    res = client.post("/api/batches/b-1/import", json={})
    assert res.status_code == 422 and res.json()["error"]["kode"] == "validasi_gagal"


def test_llm_mati_total_menjadi_llm_gagal_dan_tidak_menyimpan(client, monkeypatch):
    async def rusak(sender_messages, catalog, active_order=None):
        raise RuntimeError("penyedia mati")

    monkeypatch.setattr(modul_extractor, "extract_orders", rusak)
    res = client.post("/api/batches/b-1/import", json={"text": TEKS})
    assert res.status_code == 502 and res.json()["error"]["kode"] == "llm_gagal"

    class Kuota(Exception):
        status_code = 429

    async def habis(sender_messages, catalog, active_order=None):
        raise Kuota

    monkeypatch.setattr(modul_extractor, "extract_orders", habis)
    res = client.post("/api/batches/b-1/import", json={"text": TEKS})
    assert res.status_code == 429 and res.json()["error"]["kode"] == "kuota_llm_habis"

    async def pulih(sender_messages, catalog, active_order=None):
        return Extraction(intent="bukan_pesanan")

    monkeypatch.setattr(modul_extractor, "extract_orders", pulih)
    assert client.post("/api/batches/b-1/import", json={"text": TEKS}).json()["pesan_baru"] == 1


def test_berkas_terlalu_besar_ditolak(client, monkeypatch):
    monkeypatch.setattr("app.api.impor.MAKS_UKURAN_BYTE", 10)
    res = client.post("/api/batches/b-1/import", files={"file": ("chat.txt", TEKS.encode(), "text/plain")})
    assert res.status_code == 413 and res.json()["error"]["kode"] == "validasi_gagal"
