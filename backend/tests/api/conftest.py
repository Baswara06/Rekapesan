"""Fixture uji API: klien sudah login, klien tamu, dan data pesanan contoh dari ekspor samaran."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import require_login
from app.db import get_db
from app.main import app
from app.services import import_batch
from tests.test_import_service import CONTOH, Tiruan


@pytest.fixture
def _basis(db):
    engine = db.get_bind()

    def _sesi():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    app.dependency_overrides[get_db] = _sesi
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def tamu(_basis):
    """Klien tanpa token."""
    return TestClient(app)


@pytest.fixture
def client(_basis):
    """Klien yang sudah login."""
    app.dependency_overrides[require_login] = lambda: "demo"
    return TestClient(app)


@pytest.fixture
def pesanan_contoh(db, katalog, batch):
    """Tiga pesanan hasil impor contoh (ekstraktor tiruan): Bu Rina, Pak Anton, Mas Budi. Semua `perlu_cek`."""
    asyncio.run(import_batch(db, "b-1", CONTOH, extractor=Tiruan()))
    db.expire_all()


def id_pesanan(client, nama, batch_id="b-1"):
    for o in client.get(f"/api/batches/{batch_id}/orders").json():
        if o["customer"]["nama_tampil"] == nama:
            return o["id"]
    raise AssertionError(f"pesanan {nama} tidak ada")
