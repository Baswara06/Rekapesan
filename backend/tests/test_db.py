from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import Batch, MessageRow, Product, make_readonly_engine


def test_koneksi_read_only_bisa_baca_tapi_menolak_tulis(db, db_url, katalog):
    engine = make_readonly_engine(db_url)
    with Session(engine) as ro:
        assert ro.scalar(select(Product.harga).where(Product.id == "p-ayam")) == 18000
        ro.add(Batch(nama="x", tanggal_kirim=date(2026, 11, 13)))
        with pytest.raises(OperationalError):
            ro.commit()
    engine.dispose()
    assert db.scalars(select(Batch)).all() == []


def test_read_only_menolak_database_memori():
    with pytest.raises(ValueError):
        make_readonly_engine("sqlite:///:memory:")


def test_sidik_unik_per_batch(db, batch):
    from datetime import datetime

    from sqlalchemy.exc import IntegrityError

    for _ in range(2):
        db.add(MessageRow(batch_id="b-1", waktu=datetime(2026, 11, 12, 9), pengirim="A", isi="x", sidik="s" * 64))
    with pytest.raises(IntegrityError):
        db.commit()
