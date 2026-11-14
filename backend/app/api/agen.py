"""Endpoint agen tanya-jawab. Pemilik: Raihan (agen: Pangeran). Jawaban selalu disertai trace."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import agent as modul_agent
from app.agent.agen import Hari
from app.api.kepemilikan import batch_milik, pemilik_aktif
from app.core.errors import ApiError
from app.db import Batch, get_db
from app.services.harian_service import MAKS_HARI

router = APIRouter(prefix="/api")


class AskIn(BaseModel):
    # Kosong: agen membaca semua hari milik penjual (14 terbaru) dan menyaring sendiri per tanggal.
    batch_id: str | None = None
    pertanyaan: str = Field(min_length=1, max_length=1000)
    riwayat: list[dict[str, str]] = []


@router.post("/agent/ask")
async def tanya(body: AskIn, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    if body.batch_id:
        batch_milik(db, body.batch_id, pemilik)
        lingkup: str | list[Hari] = body.batch_id
    else:
        lingkup = [
            Hari(batch_id=b.id, tanggal=b.tanggal_kirim.isoformat(), nama=b.nama)
            for b in db.scalars(
                select(Batch).where(Batch.pemilik == pemilik).order_by(Batch.tanggal_kirim.desc()).limit(MAKS_HARI)
            )
        ]
    try:
        jawab = await modul_agent.ask_agent(body.pertanyaan, lingkup, body.riwayat)
    except NotImplementedError:
        raise ApiError(502, "llm_gagal", "Agen tanya-jawab belum tersedia.") from None
    except Exception:  # noqa: BLE001
        raise ApiError(502, "llm_gagal", "Agen tidak bisa menjawab sekarang. Coba lagi nanti.") from None
    return {"jawaban": jawab.answer, "trace": [t.model_dump() for t in jawab.trace]}
