"""Endpoint penerima impor chat. Pemilik: Satria (orkestrasi di `services/import_service.py`).

Menerima `multipart/form-data` dengan `file` (.txt/.zip) atau `text`, atau JSON `{"text": "..."}`.
Share target PWA meneruskan berkas ke endpoint yang sama.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.kepemilikan import batch_milik, pemilik_aktif, produk_milik
from app.core.errors import ApiError
from app.db import Product, get_db
from app.parser import FormatTidakDikenal
from app.parser.whatsapp import MAKS_UKURAN_BYTE
from app.services import BatchTidakDitemukan, EkstraksiGagalTotal, ImporBentrok, ImportResult, import_batch

_PESAN_LLM = {
    "kuota_llm_habis": "Kuota model habis. Belum ada yang disimpan, coba impor lagi nanti.",
    "llm_gagal": "Model tidak bisa dihubungi. Belum ada yang disimpan, coba impor lagi.",
}

router = APIRouter(prefix="/api")


def _galat(status: int, kode: str, pesan: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"kode": kode, "pesan": pesan}})


async def baca_badan(request: Request) -> bytes | str | JSONResponse:
    """Isi chat dari multipart `file`/`text` atau JSON `{"text"}`. Galat dikembalikan sebagai JSONResponse."""
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
            # Baca paling banyak batas + 1 byte, supaya unggahan raksasa tidak dimuat ke memori.
            data = await berkas.read(MAKS_UKURAN_BYTE + 1)
        elif isinstance(form.get("text"), str):
            data = form["text"]
    if not data:
        return _galat(422, "validasi_gagal", "Kirim `file` (.txt/.zip) atau `text` berisi chat.")
    ukuran = len(data) if isinstance(data, bytes) else len(data.encode("utf-8"))
    if ukuran > MAKS_UKURAN_BYTE:
        return _galat(413, "validasi_gagal", "Berkas terlalu besar (maksimal 20 MB).")
    return data


@router.post("/batches/{batch_id}/import", response_model=ImportResult)
async def impor_chat(batch_id: str, request: Request, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)):
    try:
        batch_milik(db, batch_id, pemilik)
    except ApiError:
        return _galat(404, "tidak_ditemukan", "Batch tidak ditemukan.")
    # Akun baru belum punya menu: tanpa katalog semua pesanan jadi `item_tidak_dikenal` dan panggilan
    # LLM terbuang. Tolak sebelum berkas dibaca supaya penjual diarahkan mengisi menu dulu.
    if db.scalar(produk_milik(pemilik).where(Product.aktif.is_(True)).limit(1)) is None:
        return _galat(409, "katalog_kosong", "Isi menu di Katalog dulu. Tanpa menu, pesanan tidak bisa dicocokkan dan harganya tidak bisa dihitung.")
    data = await baca_badan(request)
    if isinstance(data, JSONResponse):
        return data
    try:
        return await import_batch(db, batch_id, data)
    except BatchTidakDitemukan:
        return _galat(404, "tidak_ditemukan", "Batch tidak ditemukan.")
    except FormatTidakDikenal as exc:
        return _galat(400, "format_file_tidak_dikenal", str(exc))
    except EkstraksiGagalTotal as exc:
        return _galat(429 if exc.kode == "kuota_llm_habis" else 502, exc.kode, _PESAN_LLM[exc.kode])
    except ImporBentrok:
        return _galat(409, "impor_bentrok", "Impor lain untuk batch ini sedang berjalan. Tunggu sebentar lalu coba lagi.")
