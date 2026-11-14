"""Buku pesanan harian: pratinjau chat, impor per hari, dan papan ringkasan. Pemilik: Satria.

Hitungan ada di `services/harian_service.py`. Endpoint lama per batch tetap jalan.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.impor import _PESAN_LLM, _galat, baca_badan
from app.api.kepemilikan import pemilik_aktif, produk_milik
from app.db import Product, get_db
from app.parser import FormatTidakDikenal
from app.services import EkstraksiGagalTotal, ImporBentrok, impor_harian, pratinjau, ringkasan

router = APIRouter(prefix="/api")


@router.post("/impor/pratinjau")
async def pratinjau_impor(request: Request, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)):
    data = await baca_badan(request)
    if isinstance(data, JSONResponse):
        return data
    try:
        return pratinjau(data, list(db.scalars(produk_milik(pemilik))))
    except FormatTidakDikenal as exc:
        return _galat(400, "format_file_tidak_dikenal", str(exc))


@router.post("/impor")
async def impor_per_hari(request: Request, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)):
    if db.scalar(produk_milik(pemilik).where(Product.aktif.is_(True)).limit(1)) is None:
        return _galat(409, "katalog_kosong", "Isi menu di Katalog dulu. Tanpa menu, pesanan tidak bisa dicocokkan dan harganya tidak bisa dihitung.")
    data = await baca_badan(request)
    if isinstance(data, JSONResponse):
        return data
    try:
        return await impor_harian(db, pemilik, data)
    except FormatTidakDikenal as exc:
        return _galat(400, "format_file_tidak_dikenal", str(exc))
    except EkstraksiGagalTotal as exc:
        pesan = _PESAN_LLM[exc.kode] + " Hari yang sudah selesai tetap tersimpan."
        return _galat(429 if exc.kode == "kuota_llm_habis" else 502, exc.kode, pesan)
    except ImporBentrok:
        return _galat(409, "impor_bentrok", "Impor lain sedang berjalan. Tunggu sebentar lalu coba lagi.")


@router.get("/ringkasan")
def papan_ringkasan(db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    return ringkasan(db, pemilik)
