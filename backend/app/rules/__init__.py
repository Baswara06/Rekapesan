"""Mesin aturan deterministik: harga, total, stok, tanda kuning, ubah/batal. Pemilik: Satria."""

from typing import Any

from app.schemas import Extraction, OrderChange


def apply_intent(order_context: dict[str, Any], extraction: Extraction) -> OrderChange:
    """Terapkan hasil ekstraksi ke pesanan aktif pelanggan. Semua angka dihitung kode, bukan LLM."""
    raise NotImplementedError
