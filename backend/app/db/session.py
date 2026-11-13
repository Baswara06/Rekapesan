"""Koneksi database: sesi baca-tulis untuk API, sesi read-only untuk agen. Pemilik: Satria."""

import sqlite3
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base


def _is_sqlite(url: str) -> bool:
    return make_url(url).get_backend_name() == "sqlite"


def make_engine(url: str) -> Engine:
    """Engine baca-tulis. SQLite diberi foreign key aktif supaya cascade hapus batch jalan."""
    if not _is_sqlite(url):
        return create_engine(url, pool_pre_ping=True)

    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def make_readonly_engine(url: str) -> Engine:
    """Engine yang ditolak database saat menulis, untuk tool agen tanya-jawab.

    SQLite dibuka dengan `mode=ro`. PostgreSQL memakai `default_transaction_read_only`.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        path = parsed.database
        if not path or path == ":memory:":
            raise ValueError("Koneksi read-only butuh berkas SQLite, bukan database di memori.")

        def _connect() -> sqlite3.Connection:
            return sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)

        return create_engine("sqlite://", creator=_connect)

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"options": "-c default_transaction_read_only=on"},
    )


@lru_cache
def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


@lru_cache
def get_readonly_engine() -> Engine:
    return make_readonly_engine(get_settings().database_url)


def init_db(engine: Engine | None = None) -> None:
    """Buat semua tabel yang belum ada. Aman dipanggil berulang."""
    Base.metadata.create_all(engine or get_engine())


def get_db() -> Iterator[Session]:
    """Dependency FastAPI: satu sesi baca-tulis per permintaan."""
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


def get_readonly_session() -> Session:
    """Sesi read-only untuk agen (Pangeran). Pemanggil wajib menutupnya (`with`)."""
    return sessionmaker(get_readonly_engine(), autoflush=False)()
