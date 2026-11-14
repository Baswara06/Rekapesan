"""Tanda `stok_kurang` untuk satu batch, dihitung di satu tempat. Pemilik: Satria.

Aturannya: stok dibagi menurut **urutan pesanan masuk**. Sebuah pesanan diberi `stok_kurang`
hanya bila pesanan yang masuk lebih dulu (dan belum batal) ditambah pesanan itu sendiri melebihi
stok harian. Pesanan yang masuk belakangan tidak pernah membuat pesanan sebelumnya ikut bertanda.

Fungsi ini dipanggil setiap kali isi batch berubah (impor, ubah, tolak, buka lagi), supaya tidak
ada tanda basi: membatalkan satu pesanan besar langsung melepas tanda pesanan sesudahnya.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import STATUS_BATAL, Batch, Order, Product

from app.rules import atur_tanda, qty_per_produk, stok_kurang


def segarkan_tanda_stok(db: Session, batch_id: str) -> None:
    """Hitung ulang `stok_kurang` semua pesanan yang belum batal di sebuah batch. Tanda lain tidak disentuh.

    Tidak melakukan commit: pemanggil yang menutup transaksinya.
    """
    db.flush()
    pemilik = select(Batch.pemilik).where(Batch.id == batch_id).scalar_subquery()
    katalog = {p.id: {"stok_harian": p.stok_harian} for p in db.scalars(select(Product).where(Product.pemilik == pemilik))}
    orders = db.scalars(
        select(Order)
        .where(Order.batch_id == batch_id, Order.status != STATUS_BATAL)
        .options(selectinload(Order.items))
        .order_by(Order.dibuat_pada, Order.id)
    )
    terpakai: dict[str, int] = {}
    for order in orders:
        items = [{"product_id": it.product_id, "qty": it.qty} for it in order.items]
        baru = atur_tanda(list(order.tanda or []), "stok_kurang", stok_kurang(items, katalog, terpakai))
        if baru != list(order.tanda or []):
            order.tanda = baru
        for pid, qty in qty_per_produk(items).items():
            terpakai[pid] = terpakai.get(pid, 0) + qty
