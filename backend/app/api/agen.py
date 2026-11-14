"""Endpoint agen tanya-jawab dan riwayat percakapannya. Pemilik: Raihan (agen: Pangeran). Jawaban selalu disertai trace.

Riwayat disimpan per akun dan dihapus otomatis setelah 30 hari tanpa pesan baru. Penghapusan dijalankan
setiap kali riwayat dibuka atau pertanyaan dikirim, jadi tidak butuh penjadwal.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import agent as modul_agent
from app.agent.agen import MAKS_RIWAYAT, Hari
from app.agent.alat import KEDALUWARSA_HARI
from app.api.kepemilikan import batch_milik, pemilik_aktif
from app.core.errors import ApiError, tidak_ditemukan
from app.db import Batch, Percakapan, PesanTanya, get_db
from app.services.harian_service import MAKS_HARI

router = APIRouter(prefix="/api")


class AskIn(BaseModel):
    # Kosong: agen membaca semua hari milik penjual (14 terbaru) dan menyaring sendiri per tanggal.
    batch_id: str | None = None
    pertanyaan: str = Field(min_length=1, max_length=1000)
    riwayat: list[dict[str, str]] = []
    # Kosong: percakapan baru. Diisi: lanjutkan percakapan itu (riwayat dibaca dari server).
    percakapan_id: str | None = None


def hapus_kedaluwarsa(db: Session, pemilik: str) -> None:
    batas = datetime.now() - timedelta(days=KEDALUWARSA_HARI)
    lama = list(db.scalars(select(Percakapan.id).where(Percakapan.pemilik == pemilik, Percakapan.diubah_pada < batas)))
    if lama:
        db.execute(delete(PesanTanya).where(PesanTanya.percakapan_id.in_(lama)))
        db.execute(delete(Percakapan).where(Percakapan.id.in_(lama)))
        db.commit()


def _percakapan_milik(db: Session, percakapan_id: str, pemilik: str) -> Percakapan:
    p = db.get(Percakapan, percakapan_id)
    if p is None or p.pemilik != pemilik:
        raise tidak_ditemukan("Percakapan")
    return p


def _berakhir(p: Percakapan) -> str:
    return (p.diubah_pada + timedelta(days=KEDALUWARSA_HARI)).date().isoformat()


@router.post("/agent/ask")
async def tanya(body: AskIn, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    hapus_kedaluwarsa(db, pemilik)
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

    percakapan = _percakapan_milik(db, body.percakapan_id, pemilik) if body.percakapan_id else None
    if percakapan is not None:
        riwayat = [{"peran": m.peran, "isi": m.isi} for m in percakapan.pesan[-MAKS_RIWAYAT:]]
    else:
        riwayat = body.riwayat

    try:
        jawab = await modul_agent.ask_agent(
            body.pertanyaan, lingkup, riwayat, pemilik=pemilik, percakapan_id=percakapan.id if percakapan else None
        )
    except NotImplementedError:
        raise ApiError(502, "llm_gagal", "Agen tanya-jawab belum tersedia.") from None
    except Exception:  # noqa: BLE001
        raise ApiError(502, "llm_gagal", "Agen tidak bisa menjawab sekarang. Coba lagi nanti.") from None

    # Disimpan hanya bila agen berhasil menjawab, supaya riwayat tidak berisi pertanyaan tanpa jawaban.
    trace = [t.model_dump() for t in jawab.trace]
    if percakapan is None:
        judul = " ".join(body.pertanyaan.split())
        percakapan = Percakapan(pemilik=pemilik, judul=judul if len(judul) <= 80 else judul[:79] + "…")
        db.add(percakapan)
        db.flush()
    urutan = db.scalar(select(func.count()).select_from(PesanTanya).where(PesanTanya.percakapan_id == percakapan.id)) or 0
    db.add(PesanTanya(percakapan_id=percakapan.id, urutan=urutan, peran="pengguna", isi=body.pertanyaan))
    db.add(PesanTanya(percakapan_id=percakapan.id, urutan=urutan + 1, peran="agen", isi=jawab.answer, trace=trace))
    percakapan.diubah_pada = datetime.now()
    db.commit()
    return {"jawaban": jawab.answer, "trace": trace, "percakapan_id": percakapan.id}


@router.get("/agent/percakapan")
def daftar_percakapan(db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> list[dict[str, Any]]:
    hapus_kedaluwarsa(db, pemilik)
    jumlah = dict(
        db.execute(
            select(PesanTanya.percakapan_id, func.count())
            .join(Percakapan, PesanTanya.percakapan_id == Percakapan.id)
            .where(Percakapan.pemilik == pemilik)
            .group_by(PesanTanya.percakapan_id)
        ).all()
    )
    return [
        {
            "id": p.id,
            "judul": p.judul,
            "diubah_pada": p.diubah_pada.isoformat(timespec="seconds"),
            "berakhir_pada": _berakhir(p),
            "jumlah_pesan": jumlah.get(p.id, 0),
        }
        for p in db.scalars(select(Percakapan).where(Percakapan.pemilik == pemilik).order_by(Percakapan.diubah_pada.desc()))
    ]


@router.get("/agent/percakapan/{percakapan_id}")
def detail_percakapan(percakapan_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    hapus_kedaluwarsa(db, pemilik)
    p = _percakapan_milik(db, percakapan_id, pemilik)
    return {
        "id": p.id,
        "judul": p.judul,
        "berakhir_pada": _berakhir(p),
        "pesan": [{"peran": m.peran, "isi": m.isi, "trace": m.trace or []} for m in p.pesan],
    }


@router.delete("/agent/percakapan/{percakapan_id}", status_code=204)
def hapus_percakapan(percakapan_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> Response:
    db.delete(_percakapan_milik(db, percakapan_id, pemilik))
    db.commit()
    return Response(status_code=204)
