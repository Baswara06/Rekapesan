"""Skema database Rekapesan. Pemilik: Satria.

Bentuk tabel mengikuti `docs/api-contract.md`. Uang dalam rupiah (integer).
Semua tabel milik sebuah batch terhapus ikut batch-nya (cascade), termasuk pesan mentah.
Katalog (`products`) dan batch punya `pemilik` (username penjual). Tabel lain ikut pemilik batch-nya.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

STATUS_PERLU_CEK = "perlu_cek"
STATUS_DIKONFIRMASI = "dikonfirmasi"
STATUS_DIBAYAR = "dibayar"
STATUS_DIKIRIM = "dikirim"
STATUS_BATAL = "batal"
SEMUA_STATUS = (STATUS_PERLU_CEK, STATUS_DIKONFIRMASI, STATUS_DIBAYAR, STATUS_DIKIRIM, STATUS_BATAL)
# Pesanan yang sudah disetujui penjual. Hanya ini yang masuk hitungan produksi dan omzet.
STATUS_DISETUJUI = (STATUS_DIKONFIRMASI, STATUS_DIBAYAR, STATUS_DIKIRIM)


def _uuid() -> str:
    return str(uuid.uuid4())


def _sekarang() -> datetime:
    return datetime.now()


class Base(DeclarativeBase):
    pass


class User(Base):
    """Akun penjual hasil register. Akun demo dari `.env` tidak disimpan di sini."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Username penjual pemilik menu. Data lama tanpa pemilik diberikan ke akun demo saat `init_db`.
    pemilik: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    nama: Mapped[str] = mapped_column(String(120))
    alias: Mapped[list[str]] = mapped_column(JSON, default=list)
    harga: Mapped[int] = mapped_column(Integer)
    # None berarti stok tidak dibatasi.
    stok_harian: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang)

    resep: Mapped[list["Recipe"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class Recipe(Base):
    """Bahan baku per satu porsi menu, dasar daftar belanja."""

    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    bahan: Mapped[str] = mapped_column(String(120))
    jumlah: Mapped[float] = mapped_column(Float)
    satuan: Mapped[str] = mapped_column(String(30))

    product: Mapped[Product] = relationship(back_populates="resep")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pemilik: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    nama: Mapped[str] = mapped_column(String(120))
    tanggal_kirim: Mapped[date] = mapped_column(Date)

    # Tanggal chat PO dibuka. Pesan sebelum tanggal ini dibuang saat impor. None = tanpa saringan.
    tanggal_mulai: Mapped[date | None] = mapped_column(Date, nullable=True)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang)

    messages: Mapped[list["MessageRow"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class Customer(Base):
    """Pembeli dalam satu batch, dikenali dari nama pengirim di chat."""

    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("batch_id", "nama_tampil"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    nama_tampil: Mapped[str] = mapped_column(String(120))

    batch: Mapped[Batch] = relationship(back_populates="customers")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PERLU_CEK, index=True)
    jam_kirim: Mapped[str | None] = mapped_column(String(5), nullable=True)
    alamat: Mapped[str | None] = mapped_column(Text, nullable=True)
    catatan: Mapped[str | None] = mapped_column(Text, nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    tanda: Mapped[list[str]] = mapped_column(JSON, default=list)
    perubahan_sebelum: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    perubahan_sesudah: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang)
    diubah_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang, onupdate=_sekarang)

    batch: Mapped[Batch] = relationship(back_populates="orders")
    customer: Mapped[Customer] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    pesan_sumber: Mapped[list["MessageRow"]] = relationship(
        back_populates="order", order_by="MessageRow.waktu"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    teks_asli: Mapped[str] = mapped_column(Text)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Disalin dari katalog oleh mesin aturan saat pesanan dibuat. Tidak pernah dari LLM.
    harga_satuan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    catatan_item: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship()


class MessageRow(Base):
    """Pesan mentah hasil parser. Sidik unik per batch, dasar impor ulang yang aman."""

    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("batch_id", "sidik"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    waktu: Mapped[datetime] = mapped_column(DateTime)
    pengirim: Mapped[str] = mapped_column(String(120))
    isi: Mapped[str] = mapped_column(Text)
    sidik: Mapped[str] = mapped_column(String(64))

    batch: Mapped[Batch] = relationship(back_populates="messages")
    order: Mapped[Order | None] = relationship(back_populates="pesan_sumber")


class Payment(Base):
    """Saran bukti bayar. Status pesanan baru berubah setelah penjual mengonfirmasi."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    nama: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nominal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cocok: Mapped[bool] = mapped_column(Boolean, default=False)
    dikonfirmasi: Mapped[bool] = mapped_column(Boolean, default=False)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime, default=_sekarang)

    order: Mapped[Order] = relationship(back_populates="payments")
