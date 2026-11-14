"""Endpoint rekap dan daftar belanja. Pemilik: Raihan (hitungan di `services/recap_service.py`, Satria)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.kepemilikan import batch_milik, pemilik_aktif
from app.db import get_db
from app.services import build_recap, build_shopping_list

router = APIRouter(prefix="/api")


@router.get("/batches/{batch_id}/recap")
def rekap(batch_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    batch_milik(db, batch_id, pemilik)
    return build_recap(db, batch_id)


@router.get("/batches/{batch_id}/shopping-list")
def daftar_belanja(
    batch_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)
) -> list[dict[str, Any]]:
    batch_milik(db, batch_id, pemilik)

    return build_shopping_list(db, batch_id)
