"""Daftar, detail, ubah, setujui, tolak pesanan, dan balasan konfirmasi. Pemilik: Raihan.

Harga, total, dan tanda kuning selalu dihitung ulang oleh mesin aturan (`app.rules`),
termasuk saat penjual mengubah pesanan lewat PATCH. Tidak ada angka yang dipercaya dari klien.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.balasan import susun_balasan
from app.api.kepemilikan import batch_milik, nama_toko_akun, pastikan_order_milik, pemilik_aktif, produk_milik
from app.api.serializers import order_out
from app.core.config import get_settings
from app.core.errors import validasi
from app.db import (
    SEMUA_STATUS,
    STATUS_BATAL,
    STATUS_DIKONFIRMASI,
    STATUS_DISETUJUI,
    STATUS_PERLU_CEK,
    Order,
    OrderItem,
    Payment,
    get_db,
)
from app.rules import (
    beri_harga,
    hitung_total,
    normalisasi_jam,
    qty_per_produk,
    tanda_pesanan,
    validasi_product_id,
)
from app.schemas import ExtractedItem, Extraction
from app.services import segarkan_tanda_stok
from app.services.import_service import katalog_untuk_rules, order_ke_dict

router = APIRouter(prefix="/api")

# Perpindahan status yang boleh lewat PATCH. `dibayar` hanya lewat `payment-confirm` (penjual mengonfirmasi),
# pesanan batal hanya bisa dibuka lagi ke `perlu_cek`, dan `dikirim` tidak bisa dibatalkan atau dimundurkan.
PINDAH_STATUS: dict[str, set[str]] = {
    "perlu_cek": {"dikonfirmasi", "batal"},
    "dikonfirmasi": {"perlu_cek", "batal", "dikirim"},
    "dibayar": {"dikonfirmasi", "dikirim"},
    "dikirim": set(),
    "batal": {"perlu_cek"},
}


class ItemIn(BaseModel):
    product_id: str | None = None
    teks_asli: str = Field(min_length=1)
    qty: int | None = Field(default=None, ge=0)
    catatan_item: str | None = None


class OrderPatch(BaseModel):
    items: list[ItemIn] | None = None
    jam_kirim: str | None = None  # null atau "" menghapus jam
    alamat: str | None = None
    catatan: str | None = None
    status: Literal["perlu_cek", "dikonfirmasi", "dibayar", "dikirim", "batal"] | None = None


def _muat(db: Session, order_id: str, pemilik: str) -> Order:
    o = db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.customer), selectinload(Order.pesan_sumber))
    )
    return pastikan_order_milik(db, o, pemilik)


def _konteks_hitung(db: Session, order: Order, pemilik: str) -> tuple[dict[str, Any], dict[str, int]]:
    """Katalog untuk mesin aturan dan qty terpakai oleh pesanan LAIN di batch yang sama."""
    katalog = katalog_untuk_rules(list(db.scalars(produk_milik(pemilik))))
    lain = db.scalars(
        select(Order)
        .where(Order.batch_id == order.batch_id, Order.id != order.id, Order.status != STATUS_BATAL)
        .options(selectinload(Order.items))
    )
    terpakai: dict[str, int] = {}
    for o in lain:
        for pid, qty in qty_per_produk(order_ke_dict(o)["items"]).items():
            terpakai[pid] = terpakai.get(pid, 0) + qty
    return katalog, terpakai


def _hitung_ulang(db: Session, order: Order, pemilik: str) -> None:
    katalog, terpakai = _konteks_hitung(db, order, pemilik)
    items = order_ke_dict(order)["items"]
    order.total = hitung_total(items)
    if order.status == STATUS_BATAL:
        order.tanda = []
        return
    order.tanda = list(
        tanda_pesanan(
            items, order.jam_kirim, order.alamat, katalog, terpakai, get_settings().jumlah_tidak_wajar_default
        )
    )


def _bersih(teks: str | None) -> str | None:
    teks = (teks or "").strip()
    return teks or None


@router.get("/batches/{batch_id}/orders")
def daftar_pesanan(
    batch_id: str,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    pemilik: str = Depends(pemilik_aktif),
) -> list[dict[str, Any]]:
    batch_milik(db, batch_id, pemilik)
    if status is not None and status not in SEMUA_STATUS:
        raise validasi(f"Status tidak dikenal: {status}.")
    q = (
        select(Order)
        .where(Order.batch_id == batch_id)
        .options(selectinload(Order.items), selectinload(Order.customer), selectinload(Order.pesan_sumber))
        .order_by(Order.dibuat_pada, Order.id)
    )
    if status:
        q = q.where(Order.status == status)
    return [order_out(o) for o in db.scalars(q)]


@router.get("/orders/{order_id}")
def detail_pesanan(order_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    return order_out(_muat(db, order_id, pemilik))


@router.patch("/orders/{order_id}")
def ubah_pesanan(
    order_id: str, body: OrderPatch, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)
) -> dict[str, Any]:
    order = _muat(db, order_id, pemilik)
    diisi = body.model_fields_set

    if body.items is not None:
        # Hanya menu milik penjual ini: id menu akun lain dijadikan None oleh validasi_product_id.
        katalog = katalog_untuk_rules(list(db.scalars(produk_milik(pemilik))))
        diminta = Extraction(
            intent="ubah",
            items=[
                ExtractedItem(product_id=i.product_id, teks_asli=i.teks_asli.strip(), qty=i.qty, catatan_item=i.catatan_item)
                for i in body.items
            ],
        )
        # Menu yang tidak ada atau sudah nonaktif dijadikan None, sama seperti jalur impor.
        baru = beri_harga(validasi_product_id(diminta, katalog).items, katalog)
        order.items.clear()
        db.flush()
        for it in baru:
            order.items.append(OrderItem(**it))

    if "jam_kirim" in diisi:
        if _bersih(body.jam_kirim) is None:
            order.jam_kirim = None
        else:
            jam = normalisasi_jam(body.jam_kirim)
            if jam is None:
                raise validasi("Jam kirim tidak dikenali. Contoh: 12:00 atau 11.30.")
            order.jam_kirim = jam
    if "alamat" in diisi:
        order.alamat = _bersih(body.alamat)
    if "catatan" in diisi:
        order.catatan = _bersih(body.catatan)
    if body.status is not None and body.status != order.status:
        if body.status == "dibayar":
            raise validasi("Tandai lunas lewat payment-confirm, bukan lewat PATCH status.", status=409)
        if body.status not in PINDAH_STATUS[order.status]:
            raise validasi(f"Status {order.status} tidak bisa langsung menjadi {body.status}.", status=409)
        if order.status == "dibayar":
            for p in db.scalars(select(Payment).where(Payment.order_id == order.id)):
                p.dikonfirmasi = False  # pelunasan dibatalkan penjual
        order.status = body.status

    _hitung_ulang(db, order, pemilik)
    segarkan_tanda_stok(db, order.batch_id)  # stok menurut urutan masuk, untuk semua pesanan di batch
    db.commit()
    return order_out(order)


@router.post("/orders/{order_id}/approve")
def setujui(order_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    order = _muat(db, order_id, pemilik)
    if order.status == STATUS_BATAL:
        raise validasi("Pesanan yang sudah dibatalkan tidak bisa disetujui.", status=409)
    if order.status == STATUS_PERLU_CEK:
        order.status = STATUS_DIKONFIRMASI
        db.commit()
    return order_out(order)


@router.post("/orders/{order_id}/reject")
def tolak(order_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    order = _muat(db, order_id, pemilik)
    if order.status in ("dibayar", "dikirim"):
        raise validasi("Pesanan yang sudah dibayar atau dikirim tidak bisa ditolak.", status=409)
    if order.status != STATUS_BATAL:
        order.status = STATUS_BATAL
        order.tanda = []
        segarkan_tanda_stok(db, order.batch_id)  # stok yang dilepas bisa menghapus tanda pesanan lain
        db.commit()
    return order_out(order)


@router.post("/batches/{batch_id}/orders/approve-clean")
def setujui_yang_bersih(
    batch_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)
) -> dict[str, int]:
    """Setujui semua pesanan `perlu_cek` yang tidak bertanda kuning. Yang bertanda tetap menunggu penjual."""
    batch_milik(db, batch_id, pemilik)
    menunggu = list(db.scalars(select(Order).where(Order.batch_id == batch_id, Order.status == STATUS_PERLU_CEK)))
    disetujui = 0
    for o in menunggu:
        if not o.tanda:
            o.status = STATUS_DIKONFIRMASI
            disetujui += 1
    db.commit()
    return {"disetujui": disetujui, "masih_bertanda": len(menunggu) - disetujui}


@router.get("/orders/{order_id}/reply")
def balasan(order_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, str]:
    order = _muat(db, order_id, pemilik)
    if order.status not in STATUS_DISETUJUI:
        raise validasi("Setujui pesanan dulu sebelum membuat balasan konfirmasi.", status=409)
    nama_menu = {p.id: p.nama for p in db.scalars(produk_milik(pemilik))}

    items = [
        {
            "nama": nama_menu.get(it.product_id, it.teks_asli) if it.product_id else it.teks_asli,
            "qty": it.qty,
            "harga_satuan": it.harga_satuan,
            "catatan_item": it.catatan_item,
            "dikenal": it.product_id is not None,
        }
        for it in order.items
    ]
    teks = susun_balasan(
        order.customer.nama_tampil, items, order.total, order.jam_kirim, order.alamat, order.catatan,
        nama_toko=nama_toko_akun(db, pemilik),
    )
    return {"teks": teks}
