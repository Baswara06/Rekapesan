"""Tool read-only untuk agen tanya-jawab. Pemilik: Pangeran.

Semua tool hanya membaca lewat sesi DB read-only (database menolak tulis), dan hanya untuk batch milik
penjual yang ditetapkan kode, bukan oleh model: skema tool tidak punya argumen `batch_id`. Model hanya boleh
menyempitkan ke satu `tanggal` dari daftar hari yang sudah dipilih kode.
Yang dihitung tool adalah angka dari DB. Model hanya merangkai kalimat jawaban.
"""

from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    STATUS_DIKONFIRMASI,
    STATUS_DISETUJUI,
    STATUS_PERLU_CEK,
    Batch,
    Customer,
    Order,
    OrderItem,
    Product,
)
from app.rules import normalisasi_jam

# Arti tanda kuning untuk dibaca penjual. Kode mentah (mis. jam_kosong) tidak ikut dikirim ke model.
TANDA_ARTI = {
    "item_tidak_dikenal": "ada menu yang tidak dikenal di katalog",
    "jumlah_kosong": "jumlah porsi belum jelas",
    "jumlah_tidak_wajar": "jumlah porsi tidak wajar (terlalu banyak)",
    "alamat_kosong": "alamat belum ada",
    "jam_kosong": "jam kirim belum ada",
    "stok_kurang": "stok menu tidak cukup",
    "mungkin_dobel": "mungkin pesanan dobel",
    "gagal_diekstrak": "chat gagal dibaca, perlu dicek manual",
}
MAKS_PELANGGAN = 5
MAKS_TEKS = 200


def _potong(teks: str | None) -> str | None:
    if teks is None:
        return None
    return teks if len(teks) <= MAKS_TEKS else teks[:MAKS_TEKS] + "…"


def _ids(batch_id: str | Sequence[str]) -> list[str]:
    """Tool menerima satu batch (layar lama) atau beberapa batch (semua hari milik penjual)."""
    return [batch_id] if isinstance(batch_id, str) else list(batch_id)


def _tanggal(db: Session, ids: list[str]) -> dict[str, str]:
    return {b.id: b.tanggal_kirim.isoformat() for b in db.scalars(select(Batch).where(Batch.id.in_(ids)))}


def _pesanan(db: Session, batch_id: str | Sequence[str], status: tuple[str, ...]) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.batch_id.in_(_ids(batch_id)), Order.status.in_(status))
            .options(selectinload(Order.items), selectinload(Order.customer))
            .order_by(Order.dibuat_pada, Order.id)
        )
    )


def rekap_produksi(db: Session, batch_id: str | Sequence[str], jam: str | None = None) -> dict[str, Any]:
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
    # Pesanan yang menunggu dihitung dengan saringan jam yang sama, kalau tidak agen salah menyebut
    # jumlah seluruh batch sebagai jumlah untuk jam itu.
    antre = select(func.count()).select_from(Order).where(Order.batch_id.in_(_ids(batch_id)), Order.status == STATUS_PERLU_CEK)
    if jam_norm is not None:
        antre = antre.where(Order.jam_kirim == jam_norm)
    menunggu = db.scalar(antre)
    return {
        "jam": jam_norm,
        "produksi": produksi,
        "total_porsi": sum(r["porsi"] for r in produksi),
        "pesanan_dihitung": len(orders),
        "pesanan_menunggu_persetujuan_tidak_dihitung": menunggu,
    }


def daftar_belum_bayar(db: Session, batch_id: str | Sequence[str]) -> dict[str, Any]:
    """Pesanan yang sudah disetujui tetapi belum ditandai lunas."""
    orders = _pesanan(db, batch_id, (STATUS_DIKONFIRMASI,))
    tanggal = _tanggal(db, _ids(batch_id))
    return {
        "jumlah": len(orders),
        "total_tagihan": sum(o.total for o in orders),
        "pesanan": [
            {"nama": o.customer.nama_tampil, "tanggal": tanggal.get(o.batch_id), "total": o.total, "jam_kirim": o.jam_kirim}
            for o in orders
        ],
    }


def cek_pesanan_pelanggan(db: Session, batch_id: str | Sequence[str], nama: str) -> dict[str, Any]:
    """Isi pesanan seorang pembeli (cocokkan sebagian nama, tanpa membedakan huruf besar kecil)."""
    nama = (nama or "").strip()
    if not nama:
        return {"galat": "Nama pembeli kosong."}
    pelanggan = list(
        db.scalars(
            select(Customer)
            .where(Customer.batch_id.in_(_ids(batch_id)), func.lower(Customer.nama_tampil).contains(nama.lower(), autoescape=True))
            .order_by(Customer.nama_tampil)
            .limit(MAKS_PELANGGAN)
        )
    )
    tanggal = _tanggal(db, _ids(batch_id))
    hasil = []
    for c in pelanggan:
        for o in db.scalars(
            select(Order).where(Order.customer_id == c.id).options(selectinload(Order.items).selectinload(OrderItem.product))
        ):
            hasil.append(
                {
                    "nama": c.nama_tampil,
                    "tanggal": tanggal.get(o.batch_id),
                    "status": o.status,
                    "jam_kirim": o.jam_kirim,
                    "alamat": _potong(o.alamat),
                    "catatan": _potong(o.catatan),
                    "total": o.total,
                    "perlu_diperhatikan": [TANDA_ARTI.get(k, k) for k in (o.tanda or [])],
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
ARGUMEN: dict[str, tuple[str, ...]] = {
    "rekap_produksi": ("jam", "tanggal"),
    "daftar_belum_bayar": ("tanggal",),
    "cek_pesanan_pelanggan": ("nama", "tanggal"),
}
_TANGGAL = {"type": "string", "description": "Tanggal kirim YYYY-MM-DD dari daftar hari. Kosongkan untuk semua hari."}

SKEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "rekap_produksi",
            "description": (
                "Hitung jumlah porsi per menu dari pesanan yang sudah disetujui penjual. "
                "Isi 'jam' (mis. 12:00) untuk hanya menghitung pesanan dengan jam kirim itu; kosongkan untuk semua jam."
            ),
            "parameters": {
                "type": "object",
                "properties": {"jam": {"type": "string", "description": "Jam kirim, mis. 12:00. Opsional."}, "tanggal": _TANGGAL},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daftar_belum_bayar",
            "description": "Daftar pembeli yang pesanannya sudah disetujui tetapi belum lunas, beserta total tagihan.",
            "parameters": {"type": "object", "properties": {"tanggal": _TANGGAL}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cek_pesanan_pelanggan",
            "description": "Lihat isi, status, jam, alamat, dan total pesanan seorang pembeli berdasarkan namanya.",
            "parameters": {
                "type": "object",
                "properties": {"nama": {"type": "string", "description": "Nama pembeli, boleh sebagian."}, "tanggal": _TANGGAL},
                "required": ["nama"],
            },
        },
    },
]
