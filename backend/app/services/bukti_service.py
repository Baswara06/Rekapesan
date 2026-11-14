"""Bukti transfer dari foto di ekspor "dengan media" (.zip). Pemilik: Satria.

Hanya foto dari pembeli yang punya pesanan di batch itu yang dibaca (foto penjual seperti kode QRIS atau
foto antar dilewati), maksimal `MAKS_FOTO` per impor. Model vision (`read_payment_proof`) hanya MENYARANKAN
nama dan nominal; kode membandingkan nominal dengan total pesanan. Hasilnya disimpan sebagai `Payment`
yang BELUM dikonfirmasi: status pesanan tidak berubah sampai penjual menekan konfirmasi.
Kegagalan membaca satu foto tidak menggagalkan impor.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import STATUS_BATAL, Batch, Order, Payment
from app.parser.whatsapp import baca_berkas_zip, lampiran_foto
from app.schemas import ProofSuggestion

log = logging.getLogger(__name__)

MAKS_FOTO = 30
SEJALAN = 4

Pembaca = Callable[[bytes], Awaitable[ProofSuggestion]]


async def baca_bukti_dari_zip(db: Session, batch_id: str, data: Any, pembaca: Pembaca | None = None) -> int:
    """Baca foto bukti transfer pembeli untuk satu batch. Kembalikan jumlah saran bukti yang dibuat."""
    if not isinstance(data, (bytes, bytearray)):
        return 0
    lampiran = lampiran_foto(bytes(data))
    if not lampiran:
        return 0
    batch = db.get(Batch, batch_id)
    if batch is None:
        return 0
    if pembaca is None:
        from app.extractor import read_payment_proof as pembaca  # noqa: PLC0415

    orders = list(
        db.scalars(
            select(Order)
            .where(Order.batch_id == batch_id, Order.status != STATUS_BATAL)
            .options(selectinload(Order.customer), selectinload(Order.payments))
            .order_by(Order.dibuat_pada)
        )
    )
    # Pesanan aktif terakhir per pembeli (nama pengirim di chat = nama pembeli).
    per_pembeli: dict[str, Order] = {o.customer.nama_tampil: o for o in orders}
    sudah = {p.berkas for o in orders for p in o.payments if p.berkas}
    mulai = batch.tanggal_mulai or batch.tanggal_kirim
    calon = [
        (l, per_pembeli[l.pengirim])
        for l in lampiran
        if l.pengirim in per_pembeli and mulai <= l.waktu.date() <= batch.tanggal_kirim and l.berkas not in sudah
    ][:MAKS_FOTO]
    if not calon:
        return 0

    batas = asyncio.Semaphore(SEJALAN)

    async def baca(berkas: str) -> ProofSuggestion | None:
        isi = baca_berkas_zip(bytes(data), berkas)
        if not isi:
            return None
        async with batas:
            try:
                return await pembaca(isi)
            except Exception:  # noqa: BLE001 - satu foto gagal tidak boleh menggagalkan impor
                log.warning("Bukti %s tidak terbaca", berkas)
                return None

    hasil = await asyncio.gather(*(baca(l.berkas) for l, _ in calon))
    dibuat = 0
    for (l, order), saran in zip(calon, hasil, strict=True):
        if saran is None:
            continue  # gagal dibaca: dicoba lagi pada impor berikutnya
        if saran.nominal is None:
            # Bukan bukti transfer (foto antar, kode QRIS). Dicatat supaya impor ulang tidak membacanya lagi.
            order.payments.append(Payment(nama=None, nominal=None, cocok=False, dikonfirmasi=False, berkas=l.berkas))
            continue
        order.payments.append(
            Payment(
                nama=saran.nama,
                nominal=saran.nominal,
                cocok=saran.nominal == order.total,
                dikonfirmasi=False,
                berkas=l.berkas,
            )
        )
        dibuat += 1
    db.commit()
    return dibuat
