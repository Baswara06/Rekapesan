"""Pemisahan data per akun. Pemilik: Raihan.

Katalog dan batch punya `pemilik` (username di token). Pesanan, pembeli, pesan mentah, dan bukti bayar
ikut pemilik batch-nya. Data milik akun lain dijawab 404, seolah tidak ada.
"""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import tidak_ditemukan
from app.core.security import require_login
from app.db import Batch, Order, Product

# Dependency FastAPI: username penjual yang sedang login.
pemilik_aktif = require_login


def batch_milik(db: Session, batch_id: str, pemilik: str) -> Batch:
    b = db.get(Batch, batch_id)
    if b is None or b.pemilik != pemilik:
        raise tidak_ditemukan("Batch")
    return b


def pastikan_order_milik(db: Session, order: Order | None, pemilik: str) -> Order:
    if order is None or db.get(Batch, order.batch_id).pemilik != pemilik:
        raise tidak_ditemukan("Pesanan")
    return order


def produk_milik(pemilik: str) -> Select[tuple[Product]]:
    return select(Product).where(Product.pemilik == pemilik)
