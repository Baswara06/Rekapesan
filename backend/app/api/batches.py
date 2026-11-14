"""Batch PO: daftar, buat, hapus (beserta pesan mentah dan pesanan). Pemilik: Raihan."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.kepemilikan import batch_milik, pemilik_aktif
from app.api.serializers import batch_out
from app.core.errors import validasi
from app.db import Batch, get_db

router = APIRouter(prefix="/api")


class BatchIn(BaseModel):
    nama: str = Field(min_length=1, max_length=120)
    tanggal_kirim: date
    tanggal_mulai: date | None = None  # tanggal chat PO dibuka; pesan sebelumnya dibuang saat impor


@router.get("/batches")
def daftar_batch(db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> list[dict[str, Any]]:
    q = select(Batch).where(Batch.pemilik == pemilik).order_by(Batch.tanggal_kirim.desc(), Batch.dibuat_pada.desc())
    return [batch_out(b) for b in db.scalars(q)]


@router.post("/batches", status_code=201)
def buat_batch(body: BatchIn, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    if body.tanggal_mulai and body.tanggal_mulai > body.tanggal_kirim:
        raise validasi("Tanggal mulai tidak boleh setelah tanggal kirim.")
    b = Batch(pemilik=pemilik, nama=body.nama.strip(), tanggal_kirim=body.tanggal_kirim, tanggal_mulai=body.tanggal_mulai)
    db.add(b)
    db.commit()
    return batch_out(b)


@router.delete("/batches/{batch_id}", status_code=204)
def hapus_batch(batch_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> Response:
    """Hapus batch, pesan mentah, pembeli, pesanan, dan bukti bayar (cascade)."""
    b = batch_milik(db, batch_id, pemilik)
    db.delete(b)

    db.commit()
    return Response(status_code=204)
