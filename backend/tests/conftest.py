"""Fixture bersama: database SQLite sementara per uji dan katalog contoh."""

import pytest
from sqlalchemy.orm import Session

from app.db import Batch, Product, Recipe, init_db, make_engine


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'uji.db'}"


@pytest.fixture
def db(db_url):
    engine = make_engine(db_url)
    init_db(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def katalog(db):
    """Tiga menu contoh. Id tetap supaya mudah dirujuk di uji."""
    ayam = Product(id="p-ayam", nama="Ayam Bakar", alias=["aybak", "ayam bkr"], harga=18000, stok_harian=30)
    ayam.resep = [
        Recipe(bahan="Ayam", jumlah=0.25, satuan="kg"),
        Recipe(bahan="Beras", jumlah=0.1, satuan="kg"),
    ]
    lodeh = Product(id="p-lodeh", nama="Nasi Lodeh", alias=["lodeh"], harga=15000, stok_harian=10)
    lodeh.resep = [Recipe(bahan="beras", jumlah=0.1, satuan="kg")]
    teh = Product(id="p-teh", nama="Es Teh", alias=["esteh"], harga=5000, stok_harian=None)
    db.add_all([ayam, lodeh, teh])
    db.commit()
    return {"ayam": ayam, "lodeh": lodeh, "teh": teh}


@pytest.fixture
def batch(db):
    from datetime import date

    b = Batch(id="b-1", nama="PO Jumat", tanggal_kirim=date(2026, 11, 13), tanggal_mulai=date(2026, 11, 12))
    db.add(b)
    db.commit()
    return b
