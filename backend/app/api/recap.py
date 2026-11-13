"""Endpoint rekap dan daftar belanja. Pemilik: Raihan (hitungan di `services/recap_service.py`, Satria)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import tidak_ditemukan
from app.db import Batch, get_db
from app.services import build_recap, build_shopping_list

router = APIRouter(prefix="/api")


def _cek_batch(db: Session, batch_id: str) -> None:
    if db.get(Batch, batch_id) is None:
        raise tidak_ditemukan("Batch")


@router.get("/batches/{batch_id}/recap")
def rekap(batch_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    _cek_batch(db, batch_id)
    return build_recap(db, batch_id)


@router.get("/batches/{batch_id}/shopping-list")
def daftar_belanja(batch_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    _cek_batch(db, batch_id)
    return build_shopping_list(db, batch_id)
