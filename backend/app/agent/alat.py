"""Tool read-only untuk agen tanya-jawab. Pemilik: Pangeran.

Semua tool hanya membaca lewat sesi DB read-only (database menolak tulis), dan hanya untuk satu batch
yang ditetapkan kode, bukan oleh model: skema tool tidak punya argumen `batch_id`.
Yang dihitung tool adalah angka dari DB. Model hanya merangkai kalimat jawaban.
"""

from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    STATUS_DIKONFIRMASI,
    STATUS_DISETUJUI,
    STATUS_PERLU_CEK,
    Customer,
    Order,
    OrderItem,
    Product,
)
from app.rules import normalisasi_jam

MAKS_PELANGGAN = 5
MAKS_TEKS = 200


def _potong(teks: str | None) -> str | None:
    if teks is None:
        return None
    return teks if len(teks) <= MAKS_TEKS else teks[:MAKS_TEKS] + "…"


def _pesanan(db: Session, batch_id: str, status: tuple[str, ...]) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.batch_id == batch_id, Order.status.in_(status))
            .options(selectinload(Order.items), selectinload(Order.customer))
            .order_by(Order.dibuat_pada, Order.id)
        )
    )


def rekap_produksi(db: Session, batch_id: str, jam: str | None = None) -> dict[str, Any]:
    """Jumlah porsi per menu dari pesanan yang SUDAH DISETUJUI penjual, opsional untuk satu jam kirim."""
    jam_norm = normalisasi_jam(jam) if jam else None
    if jam and jam_norm is None:
        return {"galat": f"Jam '{jam}' tidak dikenali. Pakai format seperti 12:00."}
    orders = [o for o in _pesanan(db, batch_id, STATUS_DISETUJUI) if jam_norm is None or o.jam_kirim == jam_norm]

    qty: dict[str, int] = {}
    for o in orders:
        for it in o.items:
            if it.product_id and it.qty and it.qty > 0:
                qty[it.product_id] = qty.get(it.product_id, 0) + it.qty
    nama = {p.id: p.nama for p in db.scalars(select(Product).where(Product.id.in_(qty)))} if qty else {}
    produksi = sorted(({"menu": nama[pid], "porsi": n} for pid, n in qty.items() if pid in nama), key=lambda r: r["menu"])
    menunggu = db.scalar(
        select(func.count()).select_from(Order).where(Order.batch_id == batch_id, Order.status == STATUS_PERLU_CEK)
    )
    return {
        "jam": jam_norm,
        "produksi": produksi,
        "total_porsi": sum(r["porsi"] for r in produksi),
        "pesanan_dihitung": len(orders),
        "pesanan_menunggu_persetujuan_tidak_dihitung": menunggu,
    }


def daftar_belum_bayar(db: Session, batch_id: str) -> dict[str, Any]:
    """Pesanan yang sudah disetujui tetapi belum ditandai lunas."""
    orders = _pesanan(db, batch_id, (STATUS_DIKONFIRMASI,))
    return {
        "jumlah": len(orders),
        "total_tagihan": sum(o.total for o in orders),
        "pesanan": [{"nama": o.customer.nama_tampil, "total": o.total, "jam_kirim": o.jam_kirim} for o in orders],
    }


def cek_pesanan_pelanggan(db: Session, batch_id: str, nama: str) -> dict[str, Any]:
    """Isi pesanan seorang pembeli (cocokkan sebagian nama, tanpa membedakan huruf besar kecil)."""
    nama = (nama or "").strip()
    if not nama:
        return {"galat": "Nama pembeli kosong."}
    pelanggan = list(
        db.scalars(
            select(Customer)
            .where(Customer.batch_id == batch_id, func.lower(Customer.nama_tampil).contains(nama.lower(), autoescape=True))
            .order_by(Customer.nama_tampil)
            .limit(MAKS_PELANGGAN)
        )
    )
    hasil = []
    for c in pelanggan:
        for o in db.scalars(
            select(Order).where(Order.customer_id == c.id).options(selectinload(Order.items).selectinload(OrderItem.product))
        ):
            hasil.append(
                {
                    "nama": c.nama_tampil,
                    "status": o.status,
                    "jam_kirim": o.jam_kirim,
                    "alamat": _potong(o.alamat),
                    "catatan": _potong(o.catatan),
                    "total": o.total,
                    "tanda": list(o.tanda or []),
                    "item": [
                        {"menu": it.product.nama if it.product else _potong(it.teks_asli), "porsi": it.qty}
                        for it in o.items
                    ],
                }
            )
    return {"cocok": len(hasil), "pesanan": hasil} if hasil else {"cocok": 0, "pesan": f"Tidak ada pembeli bernama '{nama}'."}


# Nama tool -> fungsi. Argumen model disaring ke `ARGUMEN` supaya tidak ada yang menyelundupkan parameter lain.
ALAT: dict[str, Callable[..., dict[str, Any]]] = {
    "rekap_produksi": rekap_produksi,
    "daftar_belum_bayar": daftar_belum_bayar,
    "cek_pesanan_pelanggan": cek_pesanan_pelanggan,
}
ARGUMEN: dict[str, tuple[str, ...]] = {"rekap_produksi": ("jam",), "daftar_belum_bayar": (), "cek_pesanan_pelanggan": ("nama",)}

SKEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "rekap_produksi",
            "description": (
                "Hitung jumlah porsi per menu dari pesanan yang sudah disetujui penjual. "
                "Isi 'jam' (mis. 12:00) untuk hanya menghitung pesanan dengan jam kirim itu; kosongkan untuk seluruh batch."
            ),
            "parameters": {
                "type": "object",
                "properties": {"jam": {"type": "string", "description": "Jam kirim, mis. 12:00. Opsional."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daftar_belum_bayar",
            "description": "Daftar pembeli yang pesanannya sudah disetujui tetapi belum lunas, beserta total tagihan.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cek_pesanan_pelanggan",
            "description": "Lihat isi, status, jam, alamat, dan total pesanan seorang pembeli berdasarkan namanya.",
            "parameters": {
                "type": "object",
                "properties": {"nama": {"type": "string", "description": "Nama pembeli, boleh sebagian."}},
                "required": ["nama"],
            },
        },
    },
]
