"""CRUD katalog menu. Pemilik: Raihan."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.serializers import product_out
from app.core.errors import tidak_ditemukan
from app.db import Product, Recipe, get_db

router = APIRouter(prefix="/api")


class ResepIn(BaseModel):
    bahan: str = Field(min_length=1, max_length=120)
    jumlah: float = Field(gt=0)
    satuan: str = Field(min_length=1, max_length=30)


class ProductIn(BaseModel):
    nama: str = Field(min_length=1, max_length=120)
    alias: list[str] = []
    harga: int = Field(ge=0)
    stok_harian: int | None = Field(default=None, ge=0)
    aktif: bool = True
    resep: list[ResepIn] = []


class ProductPatch(BaseModel):
    nama: str | None = Field(default=None, min_length=1, max_length=120)
    alias: list[str] | None = None
    harga: int | None = Field(default=None, ge=0)
    stok_harian: int | None = Field(default=None, ge=0)  # null eksplisit = stok tidak dibatasi
    aktif: bool | None = None
    resep: list[ResepIn] | None = None


def _bersihkan_alias(alias: list[str]) -> list[str]:
    hasil: list[str] = []
    for a in alias:
        a = a.strip()
        if a and a.lower() not in {x.lower() for x in hasil}:
            hasil.append(a)
    return hasil


def _resep(items: list[ResepIn]) -> list[Recipe]:
    return [Recipe(bahan=r.bahan.strip(), jumlah=r.jumlah, satuan=r.satuan.strip()) for r in items]


def _ambil(db: Session, product_id: str) -> Product:
    p = db.scalar(select(Product).where(Product.id == product_id).options(selectinload(Product.resep)))
    if p is None:
        raise tidak_ditemukan("Menu")
    return p


@router.get("/products")
def daftar_produk(aktif: bool | None = Query(default=None), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    q = select(Product).options(selectinload(Product.resep)).order_by(Product.nama)
    if aktif is not None:
        q = q.where(Product.aktif == aktif)
    return [product_out(p) for p in db.scalars(q)]


@router.post("/products", status_code=201)
def buat_produk(body: ProductIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    p = Product(
        nama=body.nama.strip(),
        alias=_bersihkan_alias(body.alias),
        harga=body.harga,
        stok_harian=body.stok_harian,
        aktif=body.aktif,
    )
    p.resep = _resep(body.resep)
    db.add(p)
    db.commit()
    return product_out(p)


@router.patch("/products/{product_id}")
def ubah_produk(product_id: str, body: ProductPatch, db: Session = Depends(get_db)) -> dict[str, Any]:
    p = _ambil(db, product_id)
    diisi = body.model_fields_set
    if body.nama is not None:
        p.nama = body.nama.strip()
    if body.alias is not None:
        p.alias = _bersihkan_alias(body.alias)
    if body.harga is not None:
        p.harga = body.harga
    if "stok_harian" in diisi:
        p.stok_harian = body.stok_harian
    if body.aktif is not None:
        p.aktif = body.aktif
    if body.resep is not None:
        p.resep = _resep(body.resep)
    db.commit()
    return product_out(p)


@router.delete("/products/{product_id}")
def nonaktifkan_produk(product_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Menu tidak dihapus (pesanan lama masih merujuknya), hanya dinonaktifkan."""
    p = _ambil(db, product_id)
    p.aktif = False
    db.commit()
    return product_out(p)
