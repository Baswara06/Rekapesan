"""Endpoint agen tanya-jawab. Pemilik: Raihan (agen: Pangeran). Jawaban selalu disertai trace."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import agent as modul_agent
from app.core.errors import ApiError, tidak_ditemukan
from app.db import Batch, get_db

router = APIRouter(prefix="/api")


class AskIn(BaseModel):
    batch_id: str
    pertanyaan: str = Field(min_length=1, max_length=1000)
    riwayat: list[dict[str, str]] = []


@router.post("/agent/ask")
async def tanya(body: AskIn, db: Session = Depends(get_db)) -> dict[str, Any]:
    if db.get(Batch, body.batch_id) is None:
        raise tidak_ditemukan("Batch")
    try:
        jawab = await modul_agent.ask_agent(body.pertanyaan, body.batch_id, body.riwayat)
    except NotImplementedError:
        raise ApiError(502, "llm_gagal", "Agen tanya-jawab belum tersedia.") from None
    except Exception:  # noqa: BLE001
        raise ApiError(502, "llm_gagal", "Agen tidak bisa menjawab sekarang. Coba lagi nanti.") from None
    return {"jawaban": jawab.answer, "trace": [t.model_dump() for t in jawab.trace]}
