"""Bukti bayar: model hanya menyarankan, penjual yang mengonfirmasi. Pemilik: Raihan (pembaca gambar: Pangeran).

Pencocokan nominal dilakukan kode (bandingkan dengan total pesanan). Status `dibayar` hanya
berubah lewat `payment-confirm`, tidak pernah dari keluaran model.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import extractor as modul_extractor
from app.api.kepemilikan import pastikan_order_milik, pemilik_aktif
from app.core.errors import ApiError, validasi
from app.db import STATUS_DIBAYAR, STATUS_DIKONFIRMASI, Order, Payment, get_db

router = APIRouter(prefix="/api")

MAKS_GAMBAR_BYTE = 5 * 1024 * 1024


def _order(db: Session, order_id: str, pemilik: str) -> Order:
    return pastikan_order_milik(db, db.get(Order, order_id), pemilik)


@router.post("/orders/{order_id}/payment-proof")
async def bukti_bayar(
    order_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    pemilik: str = Depends(pemilik_aktif),
) -> dict[str, Any]:
    order = _order(db, order_id, pemilik)
    if not (file.content_type or "").startswith("image/"):
        raise validasi("Unggah gambar tangkapan layar transfer (JPG atau PNG).")
    data = await file.read(MAKS_GAMBAR_BYTE + 1)
    if len(data) > MAKS_GAMBAR_BYTE:
        raise validasi("Gambar terlalu besar (maksimal 5 MB).")
    try:
        saran = await modul_extractor.read_payment_proof(data)
    except NotImplementedError:
        raise ApiError(502, "llm_gagal", "Pembaca bukti bayar belum tersedia.") from None
    except Exception:  # noqa: BLE001 - kegagalan model tidak boleh membuat server error
        raise ApiError(502, "llm_gagal", "Bukti bayar tidak bisa dibaca. Tandai lunas secara manual.") from None

    cocok = saran.nominal is not None and saran.nominal == order.total
    pembayaran = Payment(order_id=order.id, nama=saran.nama, nominal=saran.nominal, cocok=cocok)
    db.add(pembayaran)
    db.commit()
    return {"nama": saran.nama, "nominal": saran.nominal, "cocok": cocok}


@router.post("/orders/{order_id}/payment-confirm")
def konfirmasi_bayar(order_id: str, db: Session = Depends(get_db), pemilik: str = Depends(pemilik_aktif)) -> dict[str, Any]:
    """Penjual menyatakan pesanan sudah dibayar. Hanya untuk pesanan yang sudah disetujui."""
    order = _order(db, order_id, pemilik)

    if order.status == STATUS_DIBAYAR:
        return {"order_id": order.id, "status": order.status}
    if order.status != STATUS_DIKONFIRMASI:
        raise validasi("Hanya pesanan yang sudah disetujui yang bisa ditandai lunas.", status=409)
    order.status = STATUS_DIBAYAR
    terakhir = db.scalar(select(Payment).where(Payment.order_id == order.id).order_by(Payment.dibuat_pada.desc()))
    if terakhir is not None:
        terakhir.dikonfirmasi = True
    db.commit()
    return {"order_id": order.id, "status": order.status}
