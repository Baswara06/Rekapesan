"""Bentuk keluaran JSON sesuai `docs/api-contract.md`. Pemilik: Raihan."""

from typing import Any

from app.db.models import Batch, Order, Product


def product_out(p: Product) -> dict[str, Any]:
    return {
        "id": p.id,
        "nama": p.nama,
        "alias": list(p.alias or []),
        "harga": p.harga,
        "stok_harian": p.stok_harian,
        "aktif": p.aktif,
        "resep": [{"bahan": r.bahan, "jumlah": r.jumlah, "satuan": r.satuan} for r in p.resep],
    }


def batch_out(b: Batch) -> dict[str, Any]:
    return {
        "id": b.id,
        "nama": b.nama,
        "tanggal_kirim": b.tanggal_kirim.isoformat(),
        "tanggal_mulai": b.tanggal_mulai.isoformat() if b.tanggal_mulai else None,
        "dibuat_pada": b.dibuat_pada.isoformat(),
    }


def order_out(o: Order) -> dict[str, Any]:
    return {
        "id": o.id,
        "batch_id": o.batch_id,
        "customer": {"id": o.customer.id, "nama_tampil": o.customer.nama_tampil},
        "status": o.status,
        "jam_kirim": o.jam_kirim,
        "alamat": o.alamat,
        "catatan": o.catatan,
        "items": [
            {
                "id": it.id,
                "product_id": it.product_id,
                "teks_asli": it.teks_asli,
                "qty": it.qty,
                "harga_satuan": it.harga_satuan,
                "catatan_item": it.catatan_item,
            }
            for it in o.items
        ],
        "total": o.total,
        "tanda": list(o.tanda or []),
        "perubahan": {"sebelum": o.perubahan_sebelum, "sesudah": o.perubahan_sesudah},
        "pesan_sumber": [
            {"id": m.id, "waktu": m.waktu.isoformat(), "pengirim": m.pengirim, "isi": m.isi}
            for m in o.pesan_sumber
        ],
    }
