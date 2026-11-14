"""Menu yang dipesan pembeli tetapi belum ada di katalog. Pemilik: Satria.

Item pesanan yang tidak cocok dengan katalog tersimpan dengan `product_id` kosong (tanda `item_tidak_dikenal`).
Di sini item itu dikelompokkan dengan KODE (huruf kecil, tanpa angka dan kata pengisi), supaya penjual bisa
menambahkannya ke katalog dengan harga yang ia tentukan sendiri. Setelah ditambah, item lama yang teksnya
sama dicocokkan ulang oleh kode: harga dan total dihitung, tanda kuning disegarkan. LLM tidak dipanggil.
"""

import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.kepemilikan import pemilik_aktif
from app.api.orders import _hitung_ulang
from app.api.serializers import product_out
from app.core.errors import validasi
from app.db import STATUS_BATAL, Batch, Order, OrderItem, Product, get_db
from app.services import segarkan_tanda_stok

router = APIRouter(prefix="/api")

_PENGISI = {
    "x", "porsi", "pcs", "bungkus", "bks", "biji", "buah", "ya", "yaa", "kak", "ka", "mbak", "mba", "mas", "bu", "pak",
    "sama", "dan", "aja", "deh", "dong", "ada", "ga", "gak", "nggak", "kah", "tolong", "mau", "pesan", "pesen", "order",
}


def kunci_menu(teks: str) -> str:
    """'Nasi Ayam Geprek 2 ya kak' -> 'nasi ayam geprek'."""
    kata = re.findall(r"[a-z]+", teks.lower())
    return " ".join(k for k in kata if k not in _PENGISI)[:60]


def _item_belum_dikenal(db: Session, pemilik: str) -> list[tuple[OrderItem, Order]]:
    return list(
        db.execute(
            select(OrderItem, Order)
            .join(Order, OrderItem.order_id == Order.id)
            .join(Batch, Order.batch_id == Batch.id)
            .where(Batch.pemilik == pemilik, OrderItem.product_id.is_(None), Order.status != STATUS_BATAL)
        ).all()
    )


@router.get("/menu-belum-dikenal")
def menu_belum_dikenal(db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> list[dict[str, Any]]:
    kelompok: dict[str, dict[str, Any]] = {}
    for it, o in _item_belum_dikenal(db, pemilik):
        kunci = kunci_menu(it.teks_asli)
        if len(kunci) < 2:
            continue
        g = kelompok.setdefault(kunci, {"kunci": kunci, "nama": kunci.title(), "pesanan": set(), "porsi": 0, "contoh": it.teks_asli})
        g["pesanan"].add(o.id)
        g["porsi"] += it.qty or 0
    hasil = [
        {"kunci": g["kunci"], "nama": g["nama"], "jumlah_pesanan": len(g["pesanan"]), "total_porsi": g["porsi"], "contoh": g["contoh"]}
        for g in kelompok.values()
    ]
    return sorted(hasil, key=lambda g: (-g["jumlah_pesanan"], g["nama"]))


class TambahIn(BaseModel):
    kunci: str = Field(min_length=2, max_length=60)
    nama: str = Field(min_length=1, max_length=120)
    harga: int = Field(gt=0)
    stok_harian: int | None = Field(default=None, ge=0)


@router.post("/menu-belum-dikenal/tambahkan", status_code=201)
def tambahkan(body: TambahIn, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    nama = " ".join(body.nama.split())
    kunci = body.kunci.strip().lower()
    ada = db.scalar(select(Product).where(Product.pemilik == pemilik, Product.nama.ilike(nama)))
    if ada is not None and ada.aktif:
        raise validasi(f"Menu '{ada.nama}' sudah ada di katalog.", status=409)
    if ada is None:
        # Teks asli pembeli jadi nama panggilan, supaya impor berikutnya langsung dikenali.
        produk = Product(pemilik=pemilik, nama=nama, alias=[kunci] if kunci != nama.lower() else [], harga=body.harga, stok_harian=body.stok_harian)
        db.add(produk)
    else:
        produk = ada
        produk.aktif, produk.harga = True, body.harga
    db.flush()

    diubah: dict[str, Order] = {}
    for it, o in _item_belum_dikenal(db, pemilik):
        if kunci_menu(it.teks_asli) == kunci:
            it.product_id, it.harga_satuan = produk.id, produk.harga
            diubah[o.id] = o
    db.flush()
    batch_ids = set()
    for o in diubah.values():
        db.refresh(o, attribute_names=["items"])
        _hitung_ulang(db, o, pemilik)
        batch_ids.add(o.batch_id)
    for b in batch_ids:
        segarkan_tanda_stok(db, b)
    db.commit()
    db.refresh(produk, attribute_names=["resep"])
    return {"menu": product_out(produk), "pesanan_dicocokkan": len(diubah)}
