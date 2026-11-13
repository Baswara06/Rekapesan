"""Ekstraksi pesanan satu pengirim dengan LLM. Pemilik: Pangeran.

Pembagian tanggung jawab dengan orkestrasi impor (`services/import_service.py`):
- galat penyedia (utama dan cadangan sama-sama gagal) DILEMPAR, supaya impor tahu ini masalah LLM,
- keluaran model yang tidak sah setelah satu kali ulang menjadi `Extraction(gagal=True)`, supaya hanya
  pengirim itu yang diberi tanda `gagal_diekstrak` dan penjual membaca chat aslinya.
"""

import json
import logging
import re
from typing import Any, get_args

from app.extractor import llm
from app.extractor.prompt import susun_pesan
from app.schemas import CatalogEntry, ExtractedItem, Extraction, Intent, Message

log = logging.getLogger(__name__)

_INTENT = set(get_args(Intent))
# Jumlah porsi di atas ini mustahil untuk pesanan rumahan. Nilai sebesar itu (mis. 99999999999999999999)
# membuat penyimpanan ke database gagal dan menjatuhkan seluruh impor, jadi dianggap tidak terbaca.
MAKS_QTY = 10_000
_PAGAR_KODE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class KeluaranTidakSah(ValueError):
    """Jawaban model bukan JSON sesuai skema."""


def _teks(nilai: Any) -> str | None:
    if isinstance(nilai, bool) or not isinstance(nilai, str | int | float):
        return None
    teks = str(nilai).strip()
    return teks or None


def _qty(nilai: Any) -> int | None:
    if isinstance(nilai, bool):
        return None
    if isinstance(nilai, int):
        n = nilai
    elif isinstance(nilai, float) and nilai.is_integer():
        n = int(nilai)
    elif isinstance(nilai, str) and re.fullmatch(r"-?\d{1,18}", nilai.strip()):
        n = int(nilai.strip())
    else:
        return None
    return n if abs(n) <= MAKS_QTY else None


def _ambil_objek(teks: str) -> dict[str, Any]:
    teks = _PAGAR_KODE.sub("", teks.strip())
    awal, akhir = teks.find("{"), teks.rfind("}")
    if awal < 0 or akhir <= awal:
        raise KeluaranTidakSah("Tidak ada objek JSON.")
    try:
        data = json.loads(teks[awal : akhir + 1])
    except json.JSONDecodeError as exc:
        raise KeluaranTidakSah(f"JSON rusak: {exc.msg}.") from exc
    if not isinstance(data, dict):
        raise KeluaranTidakSah("JSON bukan objek.")
    return data


def urai(teks: str, id_katalog: set[str]) -> Extraction:
    """Ubah jawaban model menjadi `Extraction`. Kolom di luar skema (mis. harga) dibuang begitu saja.

    `product_id` yang bukan id katalog menjadi None. `gagal` selalu False: itu hak kode, bukan model.
    """
    data = _ambil_objek(teks)
    intent = data.get("intent")
    if intent not in _INTENT:
        raise KeluaranTidakSah(f'"intent" harus salah satu dari {sorted(_INTENT)}.')
    mentah = data.get("items") or []
    if not isinstance(mentah, list):
        raise KeluaranTidakSah('"items" harus berupa daftar.')

    items: list[ExtractedItem] = []
    for it in mentah:
        if not isinstance(it, dict):
            raise KeluaranTidakSah("Setiap item harus berupa objek.")
        pid = it.get("product_id")
        teks_asli = _teks(it.get("teks_asli"))
        if teks_asli is None:
            raise KeluaranTidakSah('Setiap item butuh "teks_asli".')
        items.append(
            ExtractedItem(
                product_id=pid if isinstance(pid, str) and pid in id_katalog else None,
                teks_asli=teks_asli,
                qty=_qty(it.get("qty")),
                catatan_item=_teks(it.get("catatan_item")),
            )
        )
    return Extraction(
        intent=intent,
        items=items,
        tanggal=_teks(data.get("tanggal")),
        jam=_teks(data.get("jam")),
        alamat=_teks(data.get("alamat")),
        catatan=_teks(data.get("catatan")),
    )


async def extract_orders(
    sender_messages: list[Message],
    catalog: list[CatalogEntry],
    active_order: dict[str, Any] | None = None,
) -> Extraction:
    """Pahami pesan satu pengirim. Katalog tanpa harga. Isi chat adalah data, bukan instruksi.

    Melempar galat penyedia bila LLM utama dan cadangan gagal. Keluaran tidak sah diulang sekali dengan
    alasan penolakannya, lalu menjadi `Extraction(intent="bukan_pesanan", gagal=True)`.
    """
    percakapan = susun_pesan(sender_messages, catalog, active_order)
    id_katalog = {c.id for c in catalog}

    alasan = ""
    for percobaan in range(2):
        jawaban = await llm.chat(percakapan)
        try:
            return urai(jawaban, id_katalog)
        except KeluaranTidakSah as exc:
            alasan = str(exc)
            log.warning("Keluaran ekstraktor tidak sah (percobaan %d): %s", percobaan + 1, alasan)
            percakapan = [
                *percakapan,
                {"role": "assistant", "content": jawaban},
                {
                    "role": "user",
                    "content": f"Keluaranmu tidak sah: {alasan} Kirim ulang HANYA satu objek JSON sesuai format.",
                },
            ]
    return Extraction(intent="bukan_pesanan", gagal=True)
