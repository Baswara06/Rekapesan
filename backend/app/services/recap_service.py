"""Rekap batch: produksi, urutan kirim, omzet, belum bayar, daftar belanja. Pemilik: Satria.

Semua angka dihitung kode dari DB. Hanya pesanan yang sudah disetujui penjual
(dikonfirmasi, dibayar, dikirim) yang masuk hitungan. Pesanan `perlu_cek` hanya dihitung
jumlahnya di `menunggu_persetujuan`, supaya penjual tahu rekap belum lengkap.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import STATUS_DIKONFIRMASI, STATUS_DISETUJUI, STATUS_PERLU_CEK, Order, Product


def _pesanan(db: Session, batch_id: str, status: tuple[str, ...]) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.batch_id == batch_id, Order.status.in_(status))
            .options(selectinload(Order.items), selectinload(Order.customer))
            .order_by(Order.dibuat_pada, Order.id)
        )
    )


def _qty_per_produk(orders: list[Order]) -> dict[str, int]:
    qty: dict[str, int] = {}
    for o in orders:
        for it in o.items:
            if it.product_id and it.qty and it.qty > 0:
                qty[it.product_id] = qty.get(it.product_id, 0) + it.qty
    return qty


def build_recap(db: Session, batch_id: str) -> dict[str, Any]:
    """Bentuk `Recap` di `docs/api-contract.md`, ditambah `menunggu_persetujuan`."""
    orders = _pesanan(db, batch_id, STATUS_DISETUJUI)
    qty = _qty_per_produk(orders)
    produk = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(qty)))} if qty else {}

    produksi = [
        {
            "product_id": pid,
            "nama": produk[pid].nama,
            "qty": n,
            "stok_sisa": None if produk[pid].stok_harian is None else produk[pid].stok_harian - n,
        }
        for pid, n in qty.items()
        if pid in produk
    ]
    produksi.sort(key=lambda r: r["nama"].lower())

    per_jam: dict[str | None, list[str]] = {}
    for o in orders:
        per_jam.setdefault(o.jam_kirim, []).append(o.id)
    urutan_kirim = [
        {"jam": jam, "order_ids": ids}
        for jam, ids in sorted(per_jam.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))
    ]

    menunggu = len(_pesanan(db, batch_id, (STATUS_PERLU_CEK,)))
    return {
        "produksi": produksi,
        "urutan_kirim": urutan_kirim,
        "omzet": sum(o.total for o in orders),
        "belum_bayar": [
            {"order_id": o.id, "nama": o.customer.nama_tampil, "total": o.total}
            for o in orders
            if o.status == STATUS_DIKONFIRMASI
        ],
        "menunggu_persetujuan": menunggu,
    }


def build_shopping_list(db: Session, batch_id: str) -> list[dict[str, Any]]:
    """Daftar belanja: jumlah bahan per porsi (resep) x porsi yang disetujui, dijumlah per bahan dan satuan."""
    qty = _qty_per_produk(_pesanan(db, batch_id, STATUS_DISETUJUI))
    if not qty:
        return []
    products = db.scalars(select(Product).where(Product.id.in_(qty)).options(selectinload(Product.resep)))
    total: dict[tuple[str, str], float] = {}
    nama: dict[tuple[str, str], str] = {}
    for p in products:
        for r in p.resep:
            kunci = (r.bahan.strip().lower(), r.satuan.strip().lower())
            total[kunci] = total.get(kunci, 0.0) + r.jumlah * qty[p.id]
            nama.setdefault(kunci, r.bahan.strip())
    return [
        {"bahan": nama[k], "jumlah": round(v, 3), "satuan": k[1]}
        for k, v in sorted(total.items())
    ]
