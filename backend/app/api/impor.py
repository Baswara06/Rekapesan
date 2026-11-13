"""Endpoint penerima impor chat. Pemilik: Satria (orkestrasi di `services/import_service.py`).

Menerima `multipart/form-data` dengan `file` (.txt/.zip) atau `text`, atau JSON `{"text": "..."}`.
Share target PWA meneruskan berkas ke endpoint yang sama.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.parser import FormatTidakDikenal
from app.services import BatchTidakDitemukan, ImportResult, import_batch

router = APIRouter(prefix="/api")


def _galat(status: int, kode: str, pesan: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"kode": kode, "pesan": pesan}})


@router.post("/batches/{batch_id}/import", response_model=ImportResult)
async def impor_chat(batch_id: str, request: Request, db: Session = Depends(get_db)):
    data: bytes | str | None = None
    if "application/json" in request.headers.get("content-type", ""):
        try:
            badan = await request.json()
        except ValueError:
            badan = None
        if isinstance(badan, dict) and isinstance(badan.get("text"), str):
            data = badan["text"]
    else:
        form = await request.form()
        berkas = form.get("file")
        if berkas is not None and hasattr(berkas, "read"):
            data = await berkas.read()
        elif isinstance(form.get("text"), str):
            data = form["text"]

    if not data:
        return _galat(422, "validasi_gagal", "Kirim `file` (.txt/.zip) atau `text` berisi chat.")
    try:
        return await import_batch(db, batch_id, data)
    except BatchTidakDitemukan:
        return _galat(404, "tidak_ditemukan", "Batch tidak ditemukan.")
    except FormatTidakDikenal as exc:
        return _galat(400, "format_file_tidak_dikenal", str(exc))
